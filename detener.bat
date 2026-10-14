@echo off
rem Detiene backend y frontend: las ventanas abiertas por iniciar.bat y cualquier
rem proceso que siga escuchando en los puertos 3000 u 8000.
chcp 65001 >nul
setlocal

taskkill /fi "WINDOWTITLE eq Prefactibilidad - backend*" /t /f >nul 2>nul
taskkill /fi "WINDOWTITLE eq Prefactibilidad - frontend*" /t /f >nul 2>nul

for %%p in (3000 8000) do (
    for /f "tokens=5" %%i in ('netstat -ano ^| findstr /r /c:":%%p .*LISTENING" /c:":%%p .*ESCUCHANDO"') do (
        taskkill /pid %%i /t /f >nul 2>nul
    )
)

echo Sistema detenido.
timeout /t 3 >nul 2>nul
