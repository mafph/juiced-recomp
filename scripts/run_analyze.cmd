@echo off
set "JAVA_HOME=C:\Program Files\Java\jdk-24"
call "C:\Users\Marcos\Downloads\juicedDecomp\tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat" "C:\Users\Marcos\Downloads\juicedDecomp\ghidra_proj" JuicedDecomp -import "C:\Users\Marcos\Downloads\juicedDecomp\Juiced.exe" -analysisTimeoutPerFile 3600 > "C:\Users\Marcos\Downloads\juicedDecomp\ghidra_analyze.log" 2>&1
echo DONE_EXIT_%ERRORLEVEL%>> "C:\Users\Marcos\Downloads\juicedDecomp\ghidra_analyze.log"
