<#
  Accesos del puente de WhatsApp: UN icono en el escritorio y el arranque con Windows.

    WhatsApp IA          un clic: prende el puente (si estaba apagado) y abre el panel en el
                         navegador. Si ya estaba prendido, solo abre el panel. En el panel se
                         apaga y se prende: interruptor Apagado / Solo yo / Abierto y Detener.
    (Inicio de Windows)  prende el puente minimizado y sin abrir el navegador.

  Uso (lo corre Claude, o doble clic en 3_CREAR_ICONO_Y_ARRANQUE.bat):
    powershell -ExecutionPolicy Bypass -File crear_accesos.ps1               icono + arranque con Windows
    powershell -ExecutionPolicy Bypass -File crear_accesos.ps1 -SinArranque  solo el icono
    powershell -ExecutionPolicy Bypass -File crear_accesos.ps1 -Quitar       borra icono y arranque
#>
param([switch]$SinArranque, [switch]$Quitar)
$ErrorActionPreference = "Stop"

$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
$escritorio = [Environment]::GetFolderPath("Desktop")
$inicio = [Environment]::GetFolderPath("Startup")

# Ventana 7 = minimizada: la ventana negra queda en la barra de tareas y lo que se ve es el panel.
$accesos = @(
  @{ Ruta = Join-Path $escritorio "WhatsApp IA.lnk"; Args = ""; Desc = "Abre el panel del puente de WhatsApp (y lo prende si estaba apagado)" },
  @{ Ruta = Join-Path $inicio "WhatsApp IA - Puente.lnk"; Args = "--sin-navegador"; Desc = "Prende el puente de WhatsApp al encender el computador"; Arranque = $true }
)
# Los de la primera version (tres iconos): se borran siempre.
$viejos = "WhatsApp IA - Prender.lnk", "WhatsApp IA - Panel.lnk", "WhatsApp IA - Apagar.lnk" | ForEach-Object { Join-Path $escritorio $_ }
foreach ($v in $viejos) { if (Test-Path $v) { Remove-Item $v -Force } }

if ($Quitar) {
  foreach ($a in $accesos) {
    if (Test-Path $a.Ruta) { Remove-Item $a.Ruta -Force; Write-Host "Borrado: $($a.Ruta)" }
  }
  Write-Host "Listo: sin icono y sin arranque con Windows. El puente sigue en su carpeta."
  exit 0
}

$shell = New-Object -ComObject WScript.Shell
foreach ($a in $accesos) {
  if ($a.Arranque -and $SinArranque) { continue }
  $lnk = $shell.CreateShortcut($a.Ruta)
  $lnk.TargetPath = Join-Path $aqui "1_INICIAR_PUENTE.bat"
  $lnk.Arguments = $a.Args
  $lnk.WorkingDirectory = $aqui
  $lnk.IconLocation = (Join-Path $aqui "iconos\whatsapp_ia.ico") + ",0"
  $lnk.WindowStyle = 7
  $lnk.Description = $a.Desc
  $lnk.Save()
  Write-Host "Creado: $($a.Ruta)"
}
if ($SinArranque) { Write-Host "Sin arranque con Windows (se pidio -SinArranque)." }
Write-Host "Listo."
