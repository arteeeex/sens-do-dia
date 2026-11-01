@echo off
rem Le de novo todas as demos de partida do CS2 e refaz os pesos de cada situacao,
rem o caminho dos alvos e a postura do boneco.
rem Rode depois de baixar demos novas (CS2 > Assistir > Tuas partidas > baixar).
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
set "DEMOS=D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays"
echo Lendo os duelos das demos...
"%PY%" -I "%~dp0analise\extrair_duelos.py" "%DEMOS%" "%~dp0analise\duelos.json" || goto erro
echo Medindo a cabeca pelos tiros...
"%PY%" -I "%~dp0analise\medir_cabeca.py" "%DEMOS%" "%~dp0analise\cabeca.json" || goto erro
echo Medindo a altura de cada parte do corpo nos acertos...
"%PY%" -I "%~dp0analise\medir_regioes.py" "%DEMOS%" "%~dp0analise\regioes.json" || goto erro
echo Montando o boneco na postura medida...
"%PY%" -I "%~dp0analise\boneco.py" "%~dp0analise\hitboxes_cs2.json" "%~dp0analise\regioes.json" "%~dp0app\boneco.js" "%~dp0analise" || goto erro
echo Calculando os pesos e os caminhos dos alvos...
"%PY%" -I "%~dp0analise\perfil.py" "%~dp0analise\duelos.json" "%~dp0analise\cabeca.json" "%~dp0app\perfil.js" "%~dp0analise\pesos.txt" || goto erro
echo.
echo Pronto. Pesos novos em app\perfil.js (resumo em analise\pesos.txt), boneco em app\boneco.js.
pause
exit /b 0
:erro
echo.
echo Deu erro. Copia a mensagem acima e manda pro Claude.
pause
exit /b 1
