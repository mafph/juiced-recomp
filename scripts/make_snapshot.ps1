# make_snapshot.ps1 - kompaktes, portables Backup des Projektstands.
#
# Legt neben dem Projektordner einen Ordner juicedDecomp_snapshot_<Datum> an mit:
#   juicedDecomp-history.bundle   komplette Git-Historie (kein Remote vorhanden!)
#   source.zip                    alle getrackten Dateien (git archive HEAD)
#   data/                         nicht-regenerierbare/grosse Daten (Juiced.exe, Ghidra-Export, ...)
#   MANIFEST.txt                  Hashes, Groessen, Tool-/Paketversionen
#   RESTORE.md                    Kopie von HANDOVER.md
#
# Aufruf:
#   powershell -ExecutionPolicy Bypass -File scripts\make_snapshot.ps1
#   ... -OutDir D:\backup\juiced
#
[CmdletBinding()]
param(
    [string]$OutDir
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
Set-Location $repo

if (-not $OutDir) {
    $parent = Split-Path $repo -Parent
    $OutDir = Join-Path $parent ("juicedDecomp_snapshot_" + (Get-Date -Format 'yyyyMMdd'))
}
$OutDir = [System.IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutDir 'data') | Out-Null

function Info($m) { Write-Host "[snapshot] $m" }

$dirty = (git status --porcelain)
if ($dirty) {
    Write-Warning "Arbeitskopie ist nicht sauber - das Backup enthaelt den letzten COMMIT, nicht unstaged Aenderungen:"
    $dirty | ForEach-Object { Write-Warning "  $_" }
}

# --- 1. Git-Historie (Bundle) ---
$bundle = Join-Path $OutDir 'juicedDecomp-history.bundle'
Info "Git-Bundle -> $bundle"
git bundle create $bundle --all | Out-Null
if ($LASTEXITCODE -ne 0) { throw "git bundle fehlgeschlagen" }

# --- 2. Getrackte Quellen ---
$srcZip = Join-Path $OutDir 'source.zip'
Info "Quellen (HEAD) -> $srcZip"
git archive --format=zip -o $srcZip HEAD
if ($LASTEXITCODE -ne 0) { throw "git archive fehlgeschlagen" }

# --- 3. Daten kopieren (nur was nicht sinnvoll regenerierbar ist) ---
$dataDir = Join-Path $OutDir 'data'
$files = @('Juiced.exe', 'juiced_pe.json', 'juiced_functions.json', 'opencode.json',
           '.gitattributes', '.gitignore', 'AUFTRAG.md', 'HANDOVER.md')
foreach ($f in $files) {
    $p = Join-Path $repo $f
    if (Test-Path -LiteralPath $p) {
        Copy-Item -LiteralPath $p -Destination (Join-Path $dataDir $f) -Force
    } else {
        Write-Warning "fehlt: $f"
    }
}

function Copy-Dir($name) {
    $src = Join-Path $repo $name
    if (-not (Test-Path -LiteralPath $src)) { Write-Warning "fehlt: $name"; return }
    $dst = Join-Path $dataDir $name
    Info "kopiere $name/ ..."
    robocopy $src $dst /E /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy $name fehlgeschlagen ($LASTEXITCODE)" }
}

Copy-Dir 'decompiled'
Copy-Dir 'pcrecomp'
Copy-Dir 'logs'

# --- 4. MANIFEST ---
$manifest = Join-Path $OutDir 'MANIFEST.txt'
$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("Juiced.exe Rekompilierung - Snapshot")
$lines.Add("Erstellt: " + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
$lines.Add("Commit:   " + (git rev-parse HEAD))
$lines.Add("Branch:   " + (git rev-parse --abbrev-ref HEAD))
$lines.Add("")
$lines.Add("== Wiederherstellung ==")
$lines.Add("1) git clone juicedDecomp-history.bundle juicedDecomp")
$lines.Add("2) data/* an die gleichen Pfade im Repo kopieren")
$lines.Add("3) Toolchain/Python siehe RESTORE.md (HANDOVER.md)")
$lines.Add("4) scripts\reproduce.cmd  bzw.  scripts\build_full.cmd")
$lines.Add("")
$lines.Add("== Toolchain / Pakete ==")
try { $lines.Add("gcc:   " + ((& 'C:\msys64\mingw32\bin\gcc.exe' --version 2>$null) | Select-Object -First 1)) } catch { $lines.Add("gcc:   <nicht gefunden>") }
try { $lines.Add("ninja: " + (& 'C:\msys64\mingw32\bin\ninja.exe' --version 2>$null)) } catch { $lines.Add("ninja: <nicht gefunden>") }
try { $lines.Add("cmake: " + ((& 'C:\msys64\mingw32\bin\cmake.exe' --version 2>$null) | Select-Object -First 1)) } catch { $lines.Add("cmake: <nicht gefunden>") }
if (Test-Path '.venv\Scripts\python.exe') {
    $lines.Add("python: " + (& '.venv\Scripts\python.exe' -c "import sys;print(sys.version.split()[0])"))
    $lines.Add("pip freeze:")
    (& '.venv\Scripts\python.exe' -m pip freeze) | ForEach-Object { $lines.Add("  $_") }
}
try { $lines.Add("pcrecomp commit: " + (git -C pcrecomp rev-parse HEAD)) } catch { }
$lines.Add("")
$lines.Add("== Daten (SHA256 + Groesse) ==")
function Add-Hash($path, $label) {
    if (Test-Path -LiteralPath $path) {
        $h = Get-FileHash -Algorithm SHA256 -LiteralPath $path
        $sz = (Get-Item -LiteralPath $path).Length
        $lines.Add(("{0}  {1,12:N0}  {2}" -f $h.Hash, $sz, $label))
    }
}
Add-Hash (Join-Path $repo 'Juiced.exe') 'Juiced.exe'
Add-Hash (Join-Path $repo 'juiced_functions.json') 'juiced_functions.json'
Add-Hash (Join-Path $repo 'juiced_pe.json') 'juiced_pe.json'
Add-Hash (Join-Path $repo 'decompiled\all_functions.c') 'decompiled/all_functions.c'
Add-Hash (Join-Path $repo 'decompiled\functions.csv') 'decompiled/functions.csv'
Add-Hash $bundle 'juicedDecomp-history.bundle'
Add-Hash $srcZip 'source.zip'
$lines.Add("")
$lines.Add("== Verzeichnisse (Groesse) ==")
foreach ($d in 'data\decompiled', 'data\pcrecomp', 'data\logs') {
    $p = Join-Path $OutDir $d
    if (Test-Path -LiteralPath $p) {
        $sum = (Get-ChildItem -LiteralPath $p -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
        $lines.Add(("{0,12:N0}  {1}" -f $sum, $d))
    }
}
$lines | Set-Content -Path $manifest -Encoding UTF8

# --- 5. RESTORE.md ---
$hand = Join-Path $repo 'HANDOVER.md'
if (Test-Path -LiteralPath $hand) {
    Copy-Item -LiteralPath $hand -Destination (Join-Path $OutDir 'RESTORE.md') -Force
}

# --- 6. Zusammenfassung ---
$total = (Get-ChildItem -LiteralPath $OutDir -Recurse -File | Measure-Object Length -Sum).Sum
Info ("fertig: {0}" -f $OutDir)
Info ("Gesamtgroesse: {0:N1} MB" -f ($total / 1MB))
Get-ChildItem -LiteralPath $OutDir | ForEach-Object {
    if ($_.PSIsContainer) {
        $s = (Get-ChildItem -LiteralPath $_.FullName -Recurse -File | Measure-Object Length -Sum).Sum
        Info ("  {0,-32} {1,8:N1} MB" -f ($_.Name + '/'), ($s / 1MB))
    } else {
        Info ("  {0,-32} {1,8:N2} MB" -f $_.Name, ($_.Length / 1MB))
    }
}
Info "Zip daraus erstellen oder den Ordner auf externen Datentraeger kopieren."
