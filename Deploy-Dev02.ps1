# Deploy-Local.ps1
# Script to install and launch CISO Assistant locally using Docker Desktop on Windows 11.

$ErrorActionPreference = "Stop"

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " Starting CISO Assistant Local Deployment (Windows 11 Client)" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check and Auto-Install Git
Write-Host "[*] Checking if Git is installed..." -ForegroundColor Cyan
$gitCheck = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCheck) {
    Write-Host "[!] Git is not installed. Trying to install via Windows Package Manager (winget)..." -ForegroundColor Yellow
    $wingetCheck = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetCheck) {
        Write-Host "[ERROR] winget is not installed. Please install Git manually: https://git-scm.com/" -ForegroundColor Red
        Exit 1
    }
    
    Write-Host "    Installing Git silently..." -ForegroundColor DarkGray
    & winget install --id Git.Git --exact --silent --accept-source-agreements --accept-package-agreements
    
    # Reload environment PATH for the process
    $env:PATH += ";C:\Program Files\Git\cmd"
    $gitCheck = Get-Command git -ErrorAction SilentlyContinue
    if (-not $gitCheck) {
        Write-Host "[ERROR] Git installation finished, but 'git' is still not found in PATH." -ForegroundColor Red
        Write-Host "Bitte starte deine Shell neu und führe das Skript erneut aus." -ForegroundColor Yellow
        Exit 1
    }
    Write-Host "[+] Git was successfully installed." -ForegroundColor Green
} else {
    Write-Host "[+] Git is available." -ForegroundColor Green
}

# 1b. Check and Auto-Install/Update Windows Subsystem for Linux (WSL)
Write-Host "[*] Checking Windows Subsystem for Linux (WSL) status..." -ForegroundColor Cyan
$wslCheck = Get-Command wsl.exe -ErrorAction SilentlyContinue
if (-not $wslCheck) {
    Write-Host "[!] WSL is not installed. WSL is required for Docker Desktop." -ForegroundColor Yellow
    Write-Host "    Installing WSL (this requires administrator rights)..." -ForegroundColor DarkGray
    try {
        & wsl.exe --install --no-distribution
        Write-Host "[+] WSL was successfully enabled." -ForegroundColor Green
        Write-Host "[IMPORTANT] A system reboot is required to complete the WSL installation." -ForegroundColor Red
        Write-Host "Bitte starte deinen PC neu und führe dieses Skript danach erneut aus!" -ForegroundColor Yellow
        Exit 1
    } catch {
        Write-Host "[ERROR] Failed to automatically install WSL. Please run 'wsl --install' manually." -ForegroundColor Red
        Exit 1
    }
} else {
    Write-Host "[+] WSL is installed." -ForegroundColor Green
    Write-Host "[*] Updating WSL kernel to the latest version..." -ForegroundColor Cyan
    try {
        # wsl --update updates the WSL 2 kernel silently
        & wsl.exe --update
        Write-Host "[+] WSL has been updated successfully." -ForegroundColor Green
    } catch {
        Write-Host "[WARNING] Failed to run 'wsl --update': $_" -ForegroundColor Yellow
    }
}

# 2. Check and Auto-Install/Start Docker Desktop
Write-Host "[*] Checking if Docker Desktop is installed..." -ForegroundColor Cyan
$dockerCheck = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerCheck) {
    Write-Host "[!] Docker Desktop is not installed. Trying to install via winget..." -ForegroundColor Yellow
    $wingetCheck = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $wingetCheck) {
        Write-Host "[ERROR] winget is not installed. Please install Docker Desktop manually: https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
        Exit 1
    }
    
    Write-Host "    Installing Docker Desktop silently (this may take a few minutes)..." -ForegroundColor DarkGray
    & winget install --id Docker.DockerDesktop --exact --silent --accept-source-agreements --accept-package-agreements
    
    # Reload environment PATH for the process
    $env:PATH += ";C:\Program Files\Docker\Docker\resources\bin"
    $dockerCheck = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCheck) {
        Write-Host "[WARNING] Docker Desktop was installed, but the CLI tools are not yet in PATH." -ForegroundColor Yellow
        Write-Host "Bitte starte deinen PC neu, um die Installation abzuschließen, und führe das Skript erneut aus." -ForegroundColor Yellow
        Exit 1
    }
    Write-Host "[+] Docker Desktop was successfully installed." -ForegroundColor Green
} else {
    Write-Host "[+] Docker Desktop is installed." -ForegroundColor Green
}

# Check if Docker daemon is active
Write-Host "[*] Checking if Docker daemon is active..." -ForegroundColor Cyan
$daemonRunning = $false
try {
    $oldEAP = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    $info = & docker info 2>&1
    $ErrorActionPreference = $oldEAP
    if ($LASTEXITCODE -eq 0 -and $info -notmatch "error during connect") {
        $daemonRunning = $true
    }
}
catch {
    $daemonRunning = $false
}

if (-not $daemonRunning) {
    Write-Host "[!] Docker daemon is not active. Attempting to start Docker Desktop..." -ForegroundColor Yellow
    $dockerDesktopPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktopPath) {
        Start-Process $dockerDesktopPath
        Write-Host "    Docker Desktop started. Waiting for daemon to become active (up to 60 seconds)..." -ForegroundColor DarkGray
        
        for ($i = 1; $i -le 12; $i++) {
            Start-Sleep -Seconds 5
            try {
                $oldEAP = $ErrorActionPreference
                $ErrorActionPreference = "SilentlyContinue"
                $info = & docker info 2>&1
                $ErrorActionPreference = $oldEAP
                if ($LASTEXITCODE -eq 0 -and $info -notmatch "error during connect") {
                    $daemonRunning = $true
                    break
                }
            }
            catch {}
            Write-Host "    Waiting for Docker daemon ($($i * 5)s/60s)..." -ForegroundColor Yellow
        }
    }
}

if (-not $daemonRunning) {
    Write-Host "[ERROR] Docker Desktop daemon is not running." -ForegroundColor Red
    Write-Host "Bitte starte Docker Desktop manuell und vergewissere dich, dass der Service aktiv ist." -ForegroundColor Yellow
    Exit 1
}
Write-Host "[+] Docker daemon is running." -ForegroundColor Green

# 3. Instance Configuration & Folder Selection
Write-Host ""
Write-Host "====================================================================" -ForegroundColor Yellow
Write-Host " Instanz-Konfiguration" -ForegroundColor Yellow
Write-Host "====================================================================" -ForegroundColor Yellow

$instanceName = "dev02"
$port = 8445
$qdrantPort = 6335
$selectedDrive = "D:"
$DockerRoot = "D:\_Docker"
$LocalDir = "D:\_Docker\ciso-assistant-dev02"

Write-Host "[+] Ausgewählter Installationspfad: $LocalDir" -ForegroundColor Green
Write-Host "[+] Konfigurierter HTTPS-Port: $port" -ForegroundColor Green
Write-Host "[+] Konfigurierter Qdrant-Port: $qdrantPort" -ForegroundColor Green

if (-not (Test-Path $DockerRoot)) {
    Write-Host "[*] Erstelle Root-Ordner '$DockerRoot'..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $DockerRoot | Out-Null
}

# 4. Clone Repository if not exists
if (-not (Test-Path $LocalDir)) {
    Write-Host "[*] Cloning ciso-assistant-community repository into: $LocalDir..." -ForegroundColor Cyan
    & git clone https://github.com/intuitem/ciso-assistant-community.git $LocalDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to clone the repository." -ForegroundColor Red
        Exit 1
    }
    Write-Host "[+] Repository cloned successfully." -ForegroundColor Green
} else {
    Write-Host "[+] Directory 'ciso-assistant-$instanceName' already exists. Skipping clone." -ForegroundColor Green
}

# 5. Patch docker-compose.yml for Local Stability & Multi-Instance Ports
$composePath = Join-Path $LocalDir "docker-compose.yml"
if (Test-Path $composePath) {
    # Revert any previous local modifications to start from a clean state (self-healing)
    Push-Location $LocalDir
    try {
        & git checkout -- docker-compose.yml 2>&1 | Out-Null
    } catch {}
    finally {
        Pop-Location
    }

    Write-Host "[*] Optimizing docker-compose.yml for instance '$instanceName' (Port: $port)..." -ForegroundColor Cyan
    $content = Get-Content -Raw -Path $composePath
    
    # 5a. Comment out container_name definitions to allow multiple instances without container name collision
    $content = $content -replace 'container_name:\s*\w+', '# $0'
    
    # 5b. Inject WEB_CONCURRENCY and GUNICORN_TIMEOUT if not present
    if ($content -notlike "*WEB_CONCURRENCY*") {
        $content = $content -replace 'environment:(\r?\n)', "environment:`$1      - WEB_CONCURRENCY=1`$1      - GUNICORN_TIMEOUT=300`$1"
    }
    
    # 5c. Update exposed URLs with the custom port
    $content = $content -replace 'https://localhost:8443', "https://localhost:$($port)"
    
    # 5d. Update Caddy HTTPS port mapping and ensure it is quoted to prevent YAML parser errors (maps host port to Caddy's internal port)
    $content = $content -replace '- ["'']?8443:8443["'']?', "- `"$($port):$($port)`""
    
    # 5e. Update Qdrant port mapping to prevent collision and ensure it is quoted
    $content = $content -replace '- ["'']?6333:6333["'']?', "- `"$($qdrantPort):6333`""
    
    # Write the modified docker-compose.yml as UTF-8 without BOM to ensure cross-platform compatibility
    [System.IO.File]::WriteAllText($composePath, $content, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "[+] docker-compose.yml successfully optimized and port mappings updated." -ForegroundColor Green
} else {
    Write-Host "[ERROR] docker-compose.yml not found in ciso-assistant-$instanceName directory." -ForegroundColor Red
    Exit 1
}

# 6. Start Docker Compose
Write-Host "[*] Pulling and starting Docker containers..." -ForegroundColor Cyan
Push-Location $LocalDir
try {
    Write-Host "    Pulling latest images..." -ForegroundColor DarkGray
    & docker compose pull
    Write-Host "    Starting services..." -ForegroundColor DarkGray
    & docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to start docker-compose services." -ForegroundColor Red
        Pop-Location
        Exit 1
    }
}
finally {
    Pop-Location
}
Write-Host "[+] Docker containers started successfully." -ForegroundColor Green

# 7. Wait for Healthy API
Write-Host "[*] Waiting for CISO Assistant API to become healthy..." -ForegroundColor Cyan
Write-Host "    (This can take 2-3 minutes on the first startup for database migrations to execute)" -ForegroundColor DarkGray

$apiUrl = "https://localhost:$port/api/health/"
$maxRetries = 40
$delay = 10
$healthy = $false

# Temporary disable SSL certificate checks for local self-signed dev certs
[System.Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }

# Get system curl.exe path (bypasses PowerShell cert validation callback issues)
$curlPath = Get-Command curl.exe -ErrorAction SilentlyContinue

for ($i = 1; $i -le $maxRetries; $i++) {
    if ($curlPath) {
        # Run standard curl.exe to check HTTP status or response
        $statusCode = & curl.exe -k -s -o NUL -w "%{http_code}" $apiUrl
        if ($statusCode -eq "200" -or $statusCode -eq "302") {
            $healthy = $true
            break
        }
        # Fallback body check
        $resBody = & curl.exe -k -s $apiUrl
        if ($resBody -match "status" -and $resBody -match "ok") {
            $healthy = $true
            break
        }
    } else {
        try {
            $response = Invoke-WebRequest -Uri $apiUrl -Method Get -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                break
            }
        } catch {
            # Silent ignore connection errors during boot
        }
    }
    Write-Host "    Attempt $i/${maxRetries}: Waiting for API to respond... Retrying in $delay seconds." -ForegroundColor Yellow
    Start-Sleep -Seconds $delay
}

if (-not $healthy) {
    Write-Host "[ERROR] CISO Assistant API did not become healthy in time." -ForegroundColor Red
    Write-Host "Please check the logs using: docker compose -f $LocalDir/docker-compose.yml logs backend" -ForegroundColor Yellow
    Exit 1
}
Write-Host "[+] CISO Assistant API is healthy!" -ForegroundColor Green

# 8. Interactive Profile Selection & Automated GRC Configuration
Write-Host ""
Write-Host "====================================================================" -ForegroundColor Yellow
Write-Host " GRC Onboarding Profile Selection" -ForegroundColor Yellow
Write-Host "====================================================================" -ForegroundColor Yellow
Write-Host "Verfügbare Onboarding-Profile für die GRC-Plattform:" -ForegroundColor Yellow
Write-Host " [1] Finance (DORA, ISO 27001, BSI C5, GDPR, SOC 2, M365-Assess)" -ForegroundColor White
Write-Host " [2] Healthcare (ISO 27001, NIS 2, GDPR, BSI IT-Grundschutz, M365-Assess)" -ForegroundColor White
Write-Host " [3] Automotive (TISAX, ISO 27001, GDPR, AI Act, M365-Assess)" -ForegroundColor White
Write-Host " [4] SME / KMU (NIST CSF 2.0, GDPR, M365-Assess) [Empfohlen]" -ForegroundColor White
Write-Host " [5] Freelancer (GDPR, M365-Assess)" -ForegroundColor White
Write-Host ""

$profileChoice = 1
$profileKey = "finance"
switch ($profileChoice) {
    1 { $profileKey = "finance" }
    2 { $profileKey = "healthcare" }
    3 { $profileKey = "automotive" }
    4 { $profileKey = "sme" }
    5 { $profileKey = "freelancer" }
}
Write-Host "[+] Ausgewähltes Profil: $($profileKey.ToUpper())" -ForegroundColor Green
Write-Host ""

Write-Host "[*] Kopiere GRC-Setup-Skripte, Framework-Daten und Nachweise..." -ForegroundColor Cyan
$GRCScripts = @(
    "grc_setup.py",
    "import_m365_assess.py",
    "grc_setup_m365_deconstruction.py",
    "grc_setup_metrology.py",
    "grc_link_all_frameworks.py",
    "import_m365_findings.py",
    "grc_profile_setup.py",
    "populate_privacy_custom.py",
    "registry_bilingual.json",
    "m365_assessment_parsed.json"
)

foreach ($script in $GRCScripts) {
    $src = Join-Path $PSScriptRoot $script
    $dst = Join-Path $LocalDir "db\$script"
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination $dst -Force
        Write-Host "    [+] Kopiert: $script" -ForegroundColor DarkGray
    } else {
        Write-Host "    [WARNING] Skript nicht gefunden: $script" -ForegroundColor Yellow
    }
}

# Copy evidences folder
$srcEvidences = Join-Path $PSScriptRoot "evidences"
$dstEvidences = Join-Path $LocalDir "db\evidences"
if (Test-Path $srcEvidences) {
    Copy-Item -Path $srcEvidences -Destination $dstEvidences -Recurse -Force
    Write-Host "    [+] Kopiert: evidences Ordner" -ForegroundColor DarkGray
} else {
    Write-Host "    [WARNING] evidences Ordner nicht gefunden bei $srcEvidences" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[*] Starte automatisierte GRC-Konfiguration in Docker (Dauer: ca. 1-2 Minuten)..." -ForegroundColor Cyan

Push-Location $LocalDir
try {
    # 8.1. Run Core Setup (loads ALL libraries incl. MCSB, NIST 800-53, DORA full, CRA, SCF)
    Write-Host "[1/8] Initialisiere Core-Plattform, lade Libraries & Knox API-Token..." -ForegroundColor Yellow
    if (Test-Path "db\grc_setup.py") {
        & docker compose exec -T backend python db/grc_setup.py
    } else {
        throw "db\grc_setup.py fehlt"
    }

    # 8.2. Run M365-Assess Ingestion
    Write-Host "[2/8] Ingestiere M365-Assess Framework (292 Checks)..." -ForegroundColor Yellow
    if (Test-Path "db\import_m365_assess.py") {
        & docker compose exec -T backend python db/import_m365_assess.py
    } else {
        throw "db\import_m365_assess.py fehlt"
    }

    # 8.3. Run M365 Deconstruction (Solutions, Assets, Contracts)
    Write-Host "[3/8] Erstelle M365 Service Solutions & verknüpfe Assets..." -ForegroundColor Yellow
    if (Test-Path "db\grc_setup_m365_deconstruction.py") {
        & docker compose exec -T backend python db/grc_setup_m365_deconstruction.py
    } else {
        throw "db\grc_setup_m365_deconstruction.py fehlt"
    }

    # 8.4. Run Metrology Dashboard Setup (31 Metrics & 7 Dashboards)
    Write-Host "[4/8] Generiere Compliance-Dashboards & Widgets..." -ForegroundColor Yellow
    if (Test-Path "db\grc_setup_metrology.py") {
        & docker compose exec -T backend python db/grc_setup_metrology.py
    } else {
        throw "db\grc_setup_metrology.py fehlt"
    }

    # 8.5. Run TPRM Framework-wide Linkage
    Write-Host "[5/8] Verknüpfe Microsoft & MSP Entities über alle Frameworks..." -ForegroundColor Yellow
    if (Test-Path "db\grc_link_all_frameworks.py") {
        & docker compose exec -T backend python db/grc_link_all_frameworks.py
    } else {
        throw "db\grc_link_all_frameworks.py fehlt"
    }

    # 8.6. Run Tenant Findings Importer & Cross-Framework Mapping
    Write-Host "[6/8] Importiere Tenant-Audit-Ergebnisse & mappe Kontrollen..." -ForegroundColor Yellow
    if (Test-Path "db\import_m365_findings.py") {
        & docker compose exec -T backend python db/import_m365_findings.py
    } else {
        throw "db\import_m365_findings.py fehlt"
    }

    # 8.7. Run Onboarding Profile Setup
    Write-Host "[7/8] Wende ausgewähltes Onboarding-Profil '$($profileKey.ToUpper())' an..." -ForegroundColor Yellow
    if (Test-Path "db\grc_profile_setup.py") {
        & docker compose exec -T backend python db/grc_profile_setup.py --profile $profileKey
    } else {
        throw "db\grc_profile_setup.py fehlt"
    }

    # 8.8. Run GDPR / Privacy Custom Data Seeder
    Write-Host "[8/8] Importiere GDPR / DSGVO Datenschutz-Inventar & RoPA..." -ForegroundColor Yellow
    if (Test-Path "db\populate_privacy_custom.py") {
        & docker compose exec -T backend python db/populate_privacy_custom.py
    } else {
        throw "db\populate_privacy_custom.py fehlt"
    }
}
catch {
    Write-Host "[ERROR] GRC Konfiguration fehlgeschlagen: $_" -ForegroundColor Red
    Pop-Location
    Exit 1
}
finally {
    Pop-Location
}

# 9. Parse and Display Credentials
$jsonPath = Join-Path $LocalDir "db\grc_setup_output.json"
$apiToken = "Nicht generiert"
$perimeterId = "Nicht generiert"
$assessmentName = "Nicht generiert"

if (Test-Path $jsonPath) {
    $setupData = Get-Content -Raw -Path $jsonPath | ConvertFrom-Json
    $apiToken = $setupData.api_token
    $perimeterId = $setupData.perimeter_id
    $assessmentName = $setupData.assessment_name
}

Write-Host ""
Write-Host "====================================================================" -ForegroundColor Green
Write-Host " CISO Assistant Local Deployment & Auto-Config Completed!" -ForegroundColor Green
Write-Host "====================================================================" -ForegroundColor Green
Write-Host "Your local GRC instance is ready at: https://localhost:$port" -ForegroundColor White
Write-Host "Credentials:" -ForegroundColor White
Write-Host " - Email/Username:  admin@local.test" -ForegroundColor White
Write-Host " - Password:        admin12345" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "Auto-Configured API Token & Project Details (for collectors):" -ForegroundColor Yellow
Write-Host " - API Token:       $apiToken" -ForegroundColor White
Write-Host " - Perimeter ID:    $perimeterId" -ForegroundColor White
Write-Host " - Active Assessment: $assessmentName" -ForegroundColor White
Write-Host "====================================================================" -ForegroundColor Green

