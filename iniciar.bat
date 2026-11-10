@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute instalar.bat antes de iniciar o programa.
  pause
  exit /b 1
)
echo Abra http://localhost:5000 no navegador quando o servidor estiver pronto.
echo Mantenha esta janela aberta durante a demonstracao.
".venv\Scripts\python.exe" run.py
if errorlevel 1 (
  echo Consulte o erro acima e o README.md.
  pause
)
