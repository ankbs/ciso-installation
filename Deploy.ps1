# Deploy.ps1
# Main entrypoint and orchestrator for CISO Assistant deployment.

# Ensure correct terminal output encoding for German umlauts
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " CISO Assistant Deployment Orchestrator" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Wo möchtest du das Backend installieren?" -ForegroundColor Yellow
Write-Host " [1] Remote in der Oracle cloud (OCI Free Tier)" -ForegroundColor White
Write-Host " [2] Lokal auf dem windows 11 Pro / Enterprise client (Docker Desktop)" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Bitte wähle eine Option [1-2]"

if ($choice -eq "1") {
    Write-Host "`n[+] Starte Remote OCI Deployment..." -ForegroundColor Green
    # Verify Python is available
    $pythonCheck = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCheck) {
        Write-Host "[ERROR] Python ist nicht installiert oder nicht im PATH vorhanden." -ForegroundColor Red
        Write-Host "Das OCI-Deployment benötigt Python 3 mit der OCI SDK-Bibliothek." -ForegroundColor Yellow
        Exit 1
    }
    
    # Run the OCI deployment script
    python "$PSScriptRoot\iac\deploy_to_oci.py"
}
elseif ($choice -eq "2") {
    Write-Host "`n[+] Starte lokale Windows 11 Installation..." -ForegroundColor Green
    & "$PSScriptRoot\Deploy-Local.ps1"
}
else {
    Write-Host "`n[ERROR] Ungültige Auswahl. Bitte wähle entweder 1 oder 2." -ForegroundColor Red
    Exit 1
}
