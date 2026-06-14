# CISO Automation & Managed Service - Cloud-Bereitstellung & Betrieb

Dieses private Repository enthält die Bereitstellungs-, Automatisierungs- und Agenten-Komponenten für deinen **M365 Security & Compliance Managed Service**. Es ermöglicht das Aufsetzen des **CISO Assistant** Backends in der Cloud und die Durchführung vollautomatisierter Sicherheitsprüfungen über eine REST-Schnittstelle.

---

## 📂 Repository-Inhalt und Struktur

* **`mcp_ciso_assistant.py`**: Der Python-basierte MCP-Server. Er erlaubt es LLM-Agenten (in Copilot, Open WebUI etc.), per API Projekte im CISO Assistant anzulegen und Compliance-Frameworks zuzuweisen.
* **`collectors/free/Get-M365ComplianceData.ps1`**: Der datenschutzfreundliche, REST-basierte PowerShell-Kollektor. Er fragt Entra ID-Daten per HTTPS REST ab (ohne Graph SDK) und sendet sie an den CISO Assistant.
* **`collectors/subscription/`**: Ordner für Premium-Scans (z. B. fortgeschrittene OAuth-Risikoanalyse).
* **`.env.template`**: Vorlage für die lokale Secret-Konfiguration.

---

## 🤖 1. LLM-Agent Integration via MCP (`mcp_ciso_assistant.py`)

Der MCP-Server ermöglicht es deinem KI-Assistenten, direkt per Chat-Eingabe GRC-Ressourcen anzulegen.

### Unterstützung von Befehlen wie:
* *„Erstelle mir eine GRC Plattform für meinen M365 Tenant“*
* *„Erstelle für den Kunden XYZ eine GRC Plattform und weise das DORA-Framework zu“*

### Funktionsweise:
Wenn der VPS-Server offline oder in der Entwicklung ist, schaltet der MCP-Server automatisch in einen **Simulations- und Offline-Modus** um. Er speichert die neu erstellten Projekte in einer lokalen Datei (`grc_projects_database.json`) ab, generiert Simulations-Tokens und simuliert das erfolgreiche API-Verhalten. So ist die LLM-Interaktion jederzeit test- und demonstrierbar!

---

## 💻 2. Ausführen des REST-basierten PowerShell-Collectors (`Get-M365ComplianceData.ps1`)

Dieser Kollektor läuft lokal auf dem Administrator-PC. Er benötigt **keine** schweren Graph-Zusatzmodule, sondern arbeitet rein über Standard-HTTPS-Anfragen an die Microsoft Graph-API.

### Voraussetzungen in Azure/Entra ID:
1. Erstelle eine **App-Registrierung** in deinem Entra ID.
2. Weise der App folgende API-Berechtigungen (Anwendungsberechtigungen / Application Permissions) für Microsoft Graph zu:
   * `Organization.Read.All` (v1.0 - zum Auslesen des Organisationsnamens)
   * `Policy.Read.All` (beta - zum Auslesen des Security-Defaults-Status)
3. Generiere ein **Client Secret** (Clientschlüssel) für die App.

### Ausführungs-Beispiel (Sicher & Verifiziert):
Kopiere dieses Skript in deine PowerShell (PowerShell 7+ empfohlen). Es fordert die Passwörter und Tokens über eine sichere Eingabemaske an, sodass keine Secrets im Klartext im Terminal oder im Verlauf landen:

```powershell
# 1. Parameter sicher abfragen (verschlüsselt im Speicher)
$SecureSecret = Read-Host -AsSecureString "Bitte das Azure App Client Secret eingeben"
$SecureCisoToken = Read-Host -AsSecureString "Bitte das CISO Assistant API-Token eingeben"

# 2. Collector-Skript laden
. .\collectors\free\Get-M365ComplianceData.ps1

# 3. Audit ausführen und Befund an den CISO Assistant senden
Invoke-M365ComplianceAudit `
    -TenantId "11111111-2222-3333-4444-555555555555" `
    -ClientId "00000000-0000-0000-0000-000000000000" `
    -ClientSecret $SecureSecret `
    -CisoApiUrl "https://ciso.deinedomain.de" `
    -CisoApiToken $SecureCisoToken `
    -Verbose
```

*Das Skript ermittelt den Tenant-Namen und den Status von 'Security Defaults', generiert einen standardisierten Befund (M365-SEC-001) und sendet ihn direkt per POST an die API deines CISO Assistants.*

---

## 🚀 3. CISO Assistant bereitstellen und aufsetzen

Für die Bereitstellung deines GRC-Backends bieten wir einen **interaktiven Deployment Orchestrator** an. Führe dazu einfach folgendes PowerShell-Skript im Hauptverzeichnis des Projekts aus:

```powershell
.\Deploy.ps1
```

Das Skript führt dich durch ein interaktives Auswahlmenü für das Deployment-Ziel:

### Option 1: Remote in der Oracle Cloud (OCI Free Tier - Empfohlen)
* Erstellt eine vollautomatische, sichere und private VM-Infrastruktur über den OCI Resource Manager (Infrastruktur als Code) inklusive OCI Bastion-Zugang. Es gibt keine offenen Inbound-Ports aus dem Internet.
* Eine detaillierte Klick-für-Klick-Anleitung für Endbenutzer zur OCI-Einrichtung findest du im [DEPLOYMENT_GUIDE.md](file:///c:/Users/Micha/.gemini/antigravity/scratch/ciso-automation-managed-service/DEPLOYMENT_GUIDE.md).

### Option 2: Lokal auf diesem Windows 11 Client (Docker Desktop / WSL)
* Klont das offizielle Repository `ciso-assistant-community` automatisch in ein lokales Unterverzeichnis `./ciso-assistant-local`.
* Konfiguriert und optimiert die lokale `docker-compose.yml` (z.B. Erhöhung der Gunicorn-Timeouts auf 300s für einen stabilen Start bei geringen Ressourcen).
* Startet die Docker-Container im Hintergrund und leitet dich durch die interaktive Einrichtung des Administrator-Accounts (Superuser).
* **Lokaler Zugriff:** Nach erfolgreichem Start ist die Plattform lokal in deinem Browser unter **`https://localhost:8443`** erreichbar.
