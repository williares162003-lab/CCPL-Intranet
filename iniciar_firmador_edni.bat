@echo off
cd /d "%~dp0"
set "OPENSC_CONF=%~dp0opensc-dnie-peru.conf"
set "EDNI_PKCS11_DLL=C:\Program Files\IDEMIA\IDPlugClassic\DLLs\idplug-pkcs11.dll"
python firmador_edni_local.py
pause