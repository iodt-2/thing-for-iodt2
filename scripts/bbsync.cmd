@echo off
rem bbsync.cmd - bbsync.sh icin cmd.exe / PowerShell sarmalayicisi.
rem PowerShell execution policy'sinden etkilenmez (bbsync.ps1 aksine).
rem
rem   scripts\bbsync.cmd setup
rem   scripts\bbsync.cmd init
rem   scripts\bbsync.cmd status
rem   scripts\bbsync.cmd push

setlocal

set "BASH=%ProgramFiles%\Git\bin\bash.exe"
if not exist "%BASH%" set "BASH=%ProgramFiles%\Git\usr\bin\bash.exe"
if not exist "%BASH%" set "BASH=%ProgramFiles(x86)%\Git\bin\bash.exe"
if not exist "%BASH%" (
  echo hata: bash.exe bulunamadi. Git for Windows kurulu mu? 1>&2
  exit /b 1
)

"%BASH%" "%~dp0bbsync.sh" %*
exit /b %ERRORLEVEL%
