@echo off
rem Inicia backend y frontend, cada uno en su ventana, y abre el navegador.
rem La primera vez instala todo; si faltan Python o Node.js, ofrece instalarlos con winget.
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
if exist "backend\.venv\Scripts\python.exe" goto :frontend_si_falta
call :buscar_python || exit /b 1
echo Primera vez: instalando el backend...
"%PY%" -m venv backend\.venv || exit /b 1
pushd backend
.venv\Scripts\python -m pip install -e ".[dev]"
if errorlevel 1 ( popd & exit /b 1 )
popd

:frontend_si_falta
if exist "frontend\node_modules" exit /b 0
call :buscar_node || exit /b 1
echo Primera vez: instalando el frontend...
pushd frontend
call npm install
if errorlevel 1 ( popd & exit /b 1 )
popd
exit /b 0


rem Deja en PY un Python 3.12 o superior; si no hay, ofrece instalarlo con winget.
rem (El "python" de Microsoft Store que aparece sin Python instalado falla en la prueba y no cuenta.)
:buscar_python
set "PY=python"
call :python_sirve && exit /b 0
for %%v in (312 313 314) do if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
call :python_sirve && exit /b 0
echo.
echo Falta Python 3.12 o superior.
call :ofrecer_instalar Python || goto :python_manual
winget install -e --id Python.Python.3.13 --accept-package-agreements --accept-source-agreements --override "/quiet InstallAllUsers=0 InstallLauncherAllUsers=0 PrependPath=1"
set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
call :python_sirve && exit /b 0
echo No se pudo instalar Python automaticamente.
:python_manual
echo Instalarlo desde https://www.python.org/downloads/ tildando "Add python.exe to PATH",
echo y volver a ejecutar este archivo.
exit /b 1

:python_sirve
"%PY%" -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>nul
exit /b %errorlevel%


rem Deja Node.js 20 o superior en el PATH; si no hay, ofrece instalarlo con winget.
:buscar_node
call :node_sirve && exit /b 0
set "PATH=%ProgramFiles%\nodejs;%PATH%"
call :node_sirve && exit /b 0
echo.
echo Falta Node.js 20 o superior.
call :ofrecer_instalar Node.js || goto :node_manual
echo Windows va a pedir permiso de administrador para instalarlo.
winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
call :node_sirve && exit /b 0
echo No se pudo instalar Node.js automaticamente.
:node_manual
echo Instalarlo desde https://nodejs.org/ (version LTS) y volver a ejecutar este archivo.
exit /b 1

:node_sirve
node -e "process.exit(Number(process.versions.node.split('.')[0]) < 20 ? 1 : 0)" >nul 2>nul || exit /b 1
where npm >nul 2>nul
exit /b %errorlevel%


rem Pregunta antes de instalar (winget viene con Windows 10/11 actualizados).
:ofrecer_instalar
where winget >nul 2>nul || exit /b 1
choice /c SN /m "Instalar %~1 ahora automaticamente"
if errorlevel 2 exit /b 1
exit /b 0

rem Espera hasta 3 minutos a que la URL responda (el primer arranque en desarrollo es lento).
:esperar
for /l %%n in (1,1,90) do (
    curl -s -o nul "%~1" && exit /b 0
    ping -n 3 127.0.0.1 >nul
)
echo El %~2 no respondió en %~1.
exit /b 1
