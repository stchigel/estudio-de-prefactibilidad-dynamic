# Genera las miniaturas del selector de páginas (public/diapositivas/NN.jpg) a partir de la
# presentación plantilla, usando PowerPoint instalado en la PC (Windows).
#
# Uso, desde la carpeta frontend:
#   powershell -ExecutionPolicy Bypass -File scripts/exportar-miniaturas.ps1
#
# Se usa la plantilla original (con "XX" de ejemplo) y no la del backend, que tiene los
# marcadores {{...}} a la vista. Las dos tienen las mismas 16 diapositivas en el mismo orden.
param(
  [string]$Plantilla = (Join-Path $PSScriptRoot "..\..\ejemplos-prefactibilidad\Presentaci*n prefactibilidad SOLAR.pptx"),
  [int]$Ancho = 480,
  [int]$Alto = 270
)

$ErrorActionPreference = "Stop"
$destino = Join-Path $PSScriptRoot "..\public\diapositivas"
New-Item -ItemType Directory -Force $destino | Out-Null
# Comodín en "Presentaci*n": PowerShell 5.1 lee este archivo sin BOM con la codificación local.
$plantilla = (Resolve-Path $Plantilla | Select-Object -First 1).Path
$destino = (Resolve-Path $destino).Path

$app = New-Object -ComObject PowerPoint.Application
try {
  # Abrir: solo lectura, sin título, sin ventana.
  $p = $app.Presentations.Open($plantilla, -1, 0, 0)
  foreach ($d in $p.Slides) {
    $d.Export((Join-Path $destino ("{0:D2}.jpg" -f $d.SlideIndex)), "JPG", $Ancho, $Alto)
  }
  Write-Output "$($p.Slides.Count) miniaturas en $destino"
  $p.Close()
}
finally {
  $app.Quit()
}
