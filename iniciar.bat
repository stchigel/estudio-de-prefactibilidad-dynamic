@echo off
rem Inicia backend y frontend, cada uno en su ventana, y abre el navegador.
rem   iniciar.bat              modo uso normal (compila el frontend y lo sirve optimizado)
rem   iniciar.bat desarrollo   recarga automática al editar código (lo usa iniciar-desarrollo.bat)
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "MODO=%~1"
if /i not "%MODO%"=="desarrollo" set "MODO=produccion"

call :puerto_ocupado 3000 && goto :ya_corriendo
call :puerto_ocupado 8000 && goto :ya_corriendo

call :instalar_si_falta || goto :error

if not exist "backend\.env" (
    echo Aviso: no existe backend\.env; la lectura de facturas con IA no va a funcionar.
    echo        Ver README, sección "Lectura automática de facturas".
    echo.
)

if "%MODO%"=="produccion" (
    echo Compilando el frontend, puede tardar un minuto...
    pushd frontend
    call npm run build
    if errorlevel 1 ( popd & goto :error )
    popd
    set "CMD_BACKEND=.venv\Scripts\python -m uvicorn api.main:app --port 8000"
    set "CMD_FRONTEND=npm start"
) else (
    set "CMD_BACKEND=.venv\Scripts\python -m uvicorn api.main:app --reload --port 8000"
    set "CMD_FRONTEND=npm run dev"
)

rem cmd /k deja la ventana abierta si el servidor se cae, para poder leer el error.
start "Prefactibilidad - backend" /d "%~dp0backend" cmd /k "%CMD_BACKEND%"
start "Prefactibilidad - frontend" /d "%~dp0frontend" cmd /k "%CMD_FRONTEND%"

echo Esperando a que los servidores respondan...
call :esperar http://127.0.0.1:8000/api/salud backend || goto :error
call :esperar http://localhost:3000/ frontend || goto :error

echo.
echo Sistema iniciado (%MODO%).
echo   En esta PC:      http://localhost:3000
for /f %%i in ('tailscale ip -4 2^>nul') do echo   Desde otras PCs: http://%%i:3000
echo.
echo Para apagarlo: cerrar las dos ventanas o ejecutar detener.bat
start "" http://localhost:3000
timeout /t 10 >nul 2>nul
exit /b 0


:ya_corriendo
echo El sistema ya parece estar corriendo (puerto 3000 u 8000 en uso).
echo Abrir http://localhost:3000, o ejecutar detener.bat y volver a iniciar.
goto :fin_con_pausa

:error
echo.
echo No se pudo iniciar el sistema. Revisar los mensajes de arriba
echo y los de las ventanas "Prefactibilidad - backend/frontend" si se abrieron.
:fin_con_pausa
pause
exit /b 1


rem ---------------------------------------------------------------------------
:puerto_ocupado
netstat -ano | findstr /r /c:":%1 .*LISTENING" /c:":%1 .*ESCUCHANDO" >nul
exit /b %errorlevel%

:instalar_si_falta
if not exist "backend\.venv\Scripts\python.exe" (
    echo Primera vez: instalando el backend...
    where python >nul 2>nul || ( echo Falta Python 3.12 o superior: https://www.python.org/downloads/ & exit /b 1 )
    python -m venv backend\.venv || exit /b 1
    pushd backend
    .venv\Scripts\python -m pip install -e ".[dev]"
    if errorlevel 1 ( popd & exit /b 1 )
    popd
)
if not exist "frontend\node_modules" (
    echo Primera vez: instalando el frontend...
    where npm >nul 2>nul || ( echo Falta Node.js 20 o superior: https://nodejs.org/ & exit /b 1 )
    pushd frontend
    call npm install
    if errorlevel 1 ( popd & exit /b 1 )
    popd
)
exit /b 0

rem Espera hasta 3 minutos a que la URL responda (el primer arranque en desarrollo es lento).
:esperar
for /l %%n in (1,1,90) do (
    curl -s -o nul "%~1" && exit /b 0
    ping -n 3 127.0.0.1 >nul
)
echo El %~2 no respondió en %~1.
exit /b 1
