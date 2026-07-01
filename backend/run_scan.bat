@echo off
chcp 65001 >nul
REM 切換到本 bat 檔所在資料夾（backend），確保能找到 app 套件與 .env
cd /d "%~dp0"

REM 若日後有建立虛擬環境，會自動啟用（沒有就略過，用系統 Python）
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

py run_scan.py

REM 將 Python 的結束碼回傳給工作排程器（0=成功，非 0=失敗）
exit /b %errorlevel%
