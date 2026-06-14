<#
.SYNOPSIS
    Automated WSL2 and Docker Desktop installation script for CISO Assistant.
.DESCRIPTION
    This script runs administrative checks, installs WSL2, downloads and installs
    Docker Desktop silently, and verifies the Docker service state.
#>

# 1. Require Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning "Dieses Skript muss als Administrator ausgeführt werden! Bitte starte PowerShell als Administrator neu."
    Exit 1
}

Write-Host "[*] Starte CISO Assistant - Lokale WSL2 & Docker-Installation..." -ForegroundColor Cyan

# 2. Check and Install WSL2
Write-Host "[*] Überprüfe WSL-Status..." -ForegroundColor Cyan
$wslCheck = Get-Command wsl -ErrorAction SilentlyContinue
if (-not $wslCheck) {
    Write-Host "[+] WSL nicht gefunden. Installiere WSL2..." -ForegroundColor Yellow
    # Trigger silent WSL installation
    wsl --install --default-shell wsl
    Write-Host "[!] WSL2 wurde installiert. Ein Neustart des Systems ist erforderlich." -ForegroundColor Red
    Write-Host "[!] Bitte starte deinen PC neu und führe dieses Skript erneut aus." -ForegroundColor Red
    Exit 0
} else {
    Write-Host "  [+] WSL2 ist bereits installiert." -ForegroundColor Green
}

# 3. Check and Install Docker Desktop
Write-Host "[*] Überprüfe Docker Desktop..." -ForegroundColor Cyan
$dockerCheck = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCheck) {
    Write-Host "[+] Docker nicht gefunden. Downloade Docker Desktop Installer (ca. 600MB)..." -ForegroundColor Yellow
    $installerPath = Join-Path $env:TEMP "DockerDesktopInstaller.exe"
    
    # Download Docker Desktop
    $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    Start-BitsTransfer -Source $dockerUrl -Destination $installerPath
    
    Write-Host "[+] Installiere Docker Desktop (Silent Mode, WSL2 Backend)..." -ForegroundColor Yellow
    # Silent Installation with WSL2 backend configured
    $installProcess = Start-Process -FilePath $installerPath -ArgumentList "install --quiet --accept-license --backend=wsl-2" -Wait -PassThru
    
    if ($installProcess.ExitCode -eq 0) {
        Write-Host "  [+] Docker Desktop wurde erfolgreich installiert." -ForegroundColor Green
    } else {
        Write-Error "[-] Docker Desktop Installation fehlgeschlagen. Exit Code: $($installProcess.ExitCode)"
        Exit 1
    }
    
    # Cleanup installer
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "  [+] Docker ist bereits installiert." -ForegroundColor Green
}

# 4. Verify Docker is running
Write-Host "[*] Überprüfe den Docker-Dienst..." -ForegroundColor Cyan
$attempts = 0
$dockerRunning = $false
while (-not $dockerRunning -and $attempts -lt 12) {
    & docker ps > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerRunning = $true
    } else {
        Write-Host "  [.] Warte auf Start des Docker Daemons (10s)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        $attempts++
    }
}

if ($dockerRunning) {
    Write-Host "  [+] Docker Daemon läuft erfolgreich!" -ForegroundColor Green
    Write-Host "[+] WSL2 & Docker-Setup abgeschlossen! Du kannst nun das Repository klonen und 'docker compose up -d' ausführen." -ForegroundColor Green
} else {
    Write-Warning "[-] Docker Daemon konnte nicht gestartet werden. Bitte starte Docker Desktop manuell."
}
