param(
    [switch]$StartApi,
    [switch]$UseDocker,
    [switch]$StopApi
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$gatewayScript = Join-Path $PSScriptRoot "logos-webposto-gateway\run_gateway_windows.ps1"

if (-not (Test-Path $gatewayScript)) {
    Write-Error "Script do gateway não encontrado em: $gatewayScript"
    exit 1
}

& $gatewayScript @PSBoundParameters
