@echo off
REM Unified launcher wrapper - delegates to ultimate_cert_fix.cmd
setlocal
pushd "%~dp0" >nul
call "%~dp0ultimate_cert_fix.cmd"
popd >nul
endlocal
