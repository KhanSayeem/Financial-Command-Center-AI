@echo off
REM Legacy wrapper - delegates to the consolidated ultimate_cert_fix.cmd
setlocal
pushd "%~dp0" >nul
call "%~dp0ultimate_cert_fix.cmd"
popd >nul
endlocal
