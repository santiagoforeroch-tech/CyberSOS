param(
  [string]$Email = "admin@cybersos.example"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $root ".env"

if (-not (Test-Path -LiteralPath $envPath)) {
  Copy-Item -LiteralPath (Join-Path $root ".env.example") -Destination $envPath
}

$securePassword = Read-Host "Contraseña privada del administrador local (no se mostrará)" -AsSecureString
$plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
  [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
)
$mfaCode = Read-Host "Código MFA local de 6 dígitos (solo para pruebas)"
if ($mfaCode -notmatch '^[0-9]{6}$') { throw "El código MFA debe tener exactamente 6 dígitos." }

$content = Get-Content -LiteralPath $envPath -Raw
$content = [regex]::Replace($content, '(?m)^LOCAL_ADMIN_EMAIL=.*$', "LOCAL_ADMIN_EMAIL=$Email")
$content = [regex]::Replace($content, '(?m)^LOCAL_ADMIN_PASSWORD=.*$', "LOCAL_ADMIN_PASSWORD=$plainPassword")
$content = [regex]::Replace($content, '(?m)^LOCAL_MFA_CODE=.*$', "LOCAL_MFA_CODE=$mfaCode")
Set-Content -LiteralPath $envPath -Value $content -NoNewline
Write-Host "Administrador local configurado para $Email. La contraseña se guardó únicamente en .env." -ForegroundColor Green
