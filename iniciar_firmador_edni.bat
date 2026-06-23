@echo off
cd /d "%~dp0"
set "OPENSC_CONF=%~dp0opensc-dnie-peru.conf"
set "EDNI_PKCS11_DLL=C:\Program Files\IDEMIA\IDPlugClassic\DLLs\idplug-pkcs11.dll"
set "EDNI_FIRMADOR_PORT=8765"
set "EDNI_CORS_ORIGINS=http://127.0.0.1:5000,http://localhost:5000,https://trabajodaweb.pythonanywhere.com"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" firmador_edni_local.py
) else (
    python firmador_edni_local.py
)
pause
