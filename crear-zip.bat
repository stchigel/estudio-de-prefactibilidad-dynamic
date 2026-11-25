@echo off
rem Arma un .zip del proyecto para llevarlo a otra PC: los archivos del repositorio (con los cambios
rem sin commitear) mas backend\.env, con la API key. No incluye lo que instala iniciar.bat
rem (.venv, node_modules, .next, out, caches). Queda al lado de la carpeta del repositorio.
rem
rem El .zip lleva la API key: compartirlo solo por un medio privado.
chcp 65001 >nul
setlocal
cd /d "%~dp0"

where git >nul 2>nul || (
    echo Hace falta Git para armar el .zip: https://git-scm.com/download/win
    goto :fin
)

for %%I in ("%~dp0.") do set "NOMBRE=%%~nxI"
for %%I in ("%~dp0..") do set "ZIP=%%~fI\%NOMBRE%.zip"

rem Un arbol con los cambios sin commitear de los archivos versionados (vacio si no hay cambios).
set "ARBOL="
for /f %%i in ('git stash create') do set "ARBOL=%%i"
if not defined ARBOL set "ARBOL=HEAD"

set "ENV="
if exist "backend\.env" (
    set "ENV="--prefix=%NOMBRE%/backend/" --add-file=backend/.env"
) else (
    echo Aviso: no existe backend\.env; el .zip va sin API key ^(se carga despues con setup-key.bat^).
)

if exist "%ZIP%" del "%ZIP%"
git archive --format=zip -o "%ZIP%" %ENV% "--prefix=%NOMBRE%/" %ARBOL% || (
    echo No se pudo armar el .zip.
    goto :fin
)

git status --porcelain | findstr /b "??" >nul && (
    echo Aviso: hay archivos nuevos sin agregar a git; no van en el .zip ^(ver "git status"^).
)

echo.
echo Listo: %ZIP%
if defined ENV echo Incluye backend\.env con la API key: compartirlo solo por un medio privado.

:fin
echo.
pause
