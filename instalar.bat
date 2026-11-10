@echo off
setlocal
cd /d "%~dp0"
echo Instalando Guardiao em ambiente Python isolado...
py -3.14 --version >nul 2>&1
if errorlevel 1 (
  echo Instale o Python 3.14 de 64 bits com o Python Launcher e tente novamente.
  echo Consulte o README.md para instalacao manual.
  pause
  exit /b 1
)
py -3.14 -m venv .venv
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erro
".venv\Scripts\python.exe" baixar_modelos.py
if errorlevel 1 goto erro
".venv\Scripts\python.exe" verificar.py
if errorlevel 1 goto erro
echo.
echo Instalacao concluida. Agora abra iniciar.bat.
pause
exit /b 0
:erro
echo.
echo A instalacao nao foi concluida. Confira a mensagem acima e o README.md.
pause
exit /b 1
