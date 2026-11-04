@echo off
rem Crea backend\.env y configura el proveedor de IA (Gemini o Claude) y su API key.
rem El código PowerShell (menú con flechas) está al final de este mismo archivo.
chcp 65001 >nul
set "RAIZ=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ((Get-Content -LiteralPath '%~f0' -Raw -Encoding UTF8) -split ('#'+'PS_START'))[1]"
if errorlevel 1 echo. & echo Hubo un error; la configuracion no se completo.
echo.
pause
exit /b
#PS_START
$raiz = $env:RAIZ
$env_ = Join-Path $raiz 'backend\.env'
$ejemplo = Join-Path $raiz 'backend\.env.example'
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Elegir-Opcion([string]$titulo, [string[]]$opciones) {
    $sel = 0
    Write-Host $titulo
    Write-Host '(flechas arriba/abajo para moverse, Enter para elegir)' -ForegroundColor DarkGray
    Write-Host ''
    $fila = [Console]::CursorTop
    [Console]::CursorVisible = $false
    try {
        while ($true) {
            [Console]::SetCursorPosition(0, $fila)
            for ($i = 0; $i -lt $opciones.Count; $i++) {
                if ($i -eq $sel) { Write-Host ("  > " + $opciones[$i]).PadRight(60) -ForegroundColor Black -BackgroundColor Cyan }
                else { Write-Host ("    " + $opciones[$i]).PadRight(60) }
            }
            $tecla = [Console]::ReadKey($true)
            switch ($tecla.Key) {
                'UpArrow'   { $sel = ($sel - 1 + $opciones.Count) % $opciones.Count }
                'DownArrow' { $sel = ($sel + 1) % $opciones.Count }
                'Enter'     { return $sel }
            }
        }
    } finally { [Console]::CursorVisible = $true }
}

function Poner-Valor([string]$texto, [string]$clave, [string]$valor) {
    $linea = "$clave=$valor"
    $patron = "(?m)^$([regex]::Escape($clave))=.*$"
    if ($texto -match $patron) {
        return [regex]::Replace($texto, $patron, { param($m) $linea }, 'None')
    }
    return $texto.TrimEnd("`r", "`n") + "`r`n$linea`r`n"
}

Write-Host ''
Write-Host '=== Configuracion de la API key para leer facturas ===' -ForegroundColor Cyan
Write-Host ''

# 1) Copiar el .env (si ya existe se conserva y solo se actualizan las dos lineas)
if (Test-Path $env_) {
    Write-Host 'Ya existe backend\.env: se conserva y solo se actualizan el proveedor y la key.' -ForegroundColor Yellow
} else {
    if (-not (Test-Path $ejemplo)) { throw "No se encontro $ejemplo" }
    Copy-Item $ejemplo $env_
    Write-Host 'Se creo backend\.env a partir de backend\.env.example.'
}
Write-Host ''

# 2) Elegir proveedor
$indice = Elegir-Opcion 'Que proveedor de IA queres usar?' @(
    'Gemini  (Google)',
    'Claude  (Anthropic)'
)
if ($indice -eq 0) {
    $proveedor = 'gemini'; $claveKey = 'GEMINI_API_KEY'; $donde = 'https://aistudio.google.com/apikey'
} else {
    $proveedor = 'claude'; $claveKey = 'ANTHROPIC_API_KEY'; $donde = 'https://console.anthropic.com'
}
Write-Host ''
Write-Host "Elegiste $proveedor. La key se obtiene en $donde" -ForegroundColor Green
Write-Host ''

# 3) Pedir el token (oculto al escribir/pegar)
$token = ''
while (-not $token) {
    $seguro = Read-Host 'Pega la API key y presiona Enter (no se muestra en pantalla)' -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
    try { $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr).Trim() }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if (-not $token) { Write-Host 'La key esta vacia, probar de nuevo.' -ForegroundColor Red }
}

# 4) Completar el .env
$texto = [IO.File]::ReadAllText($env_, [Text.Encoding]::UTF8)
$texto = Poner-Valor $texto 'EXTRACCION_PROVEEDOR' $proveedor
$texto = Poner-Valor $texto $claveKey $token
[IO.File]::WriteAllText($env_, $texto, $utf8)

Write-Host ''
Write-Host "Listo: backend\.env quedo con EXTRACCION_PROVEEDOR=$proveedor y $claveKey completada ($($token.Length) caracteres)." -ForegroundColor Green
Write-Host 'Si el sistema estaba corriendo, reiniciarlo (detener.bat e iniciar.bat) para que tome la key.'
