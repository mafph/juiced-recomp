@echo off
set "JAVA_HOME=C:\Program Files\Java\jdk-24"
call "C:\Users\Marcos\Downloads\juicedDecomp\tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat" "C:\Users\Marcos\Downloads\juicedDecomp\ghidra_proj" JuicedDecomp -process "Juiced.exe" -noanalysis -scriptPath "C:\Users\Marcos\Downloads\juicedDecomp\scripts" -postScript ExportDecompiledC.java "C:\Users\Marcos\Downloads\juicedDecomp\decompiled" > "C:\Users\Marcos\Downloads\juicedDecomp\logs\export.log" 2>&1
echo DONE_EXIT_%ERRORLEVEL%>> "C:\Users\Marcos\Downloads\juicedDecomp\logs\export.log"
