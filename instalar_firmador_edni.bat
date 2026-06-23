@echo off
cd /d "%~dp0"
echo ==========================================
echo Instalador del Firmador eDNI CCPL
echo ==========================================
echo.
echo Este instalador crea un entorno local y descarga las librerias necesarias.
echo Debe ejecutarse solo una vez en la computadora del administrador.
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m venv .venv
) else (
    python -m venv .venv
)

if not exist ".venv\Scripts\python.exe" (
    echo No se pudo crear el entorno local.
    echo Instale Python para Windows y marque la opcion "Add Python to PATH".
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements_firmador.txt

echo.
echo Instalacion completada.
echo Ahora ejecute iniciar_firmador_edni.bat y deje esa ventana abierta.
pause
