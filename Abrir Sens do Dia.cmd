@echo off
rem Abre o Sens do Dia no Brave (raw input do mouse funciona em navegador Chromium).
rem O caminho e relativo a esta pasta: funciona onde quer que ela esteja.
set "BRAVE=C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
set "APP=%~dp0app\index.html"
if exist "%BRAVE%" (
  start "" "%BRAVE%" "%APP%"
) else (
  start "" "%APP%"
)
