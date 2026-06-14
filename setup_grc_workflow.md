# GitHub Actions Workflow & Compiler Templates

Dieses Dokument zeigt die Templates für die automatisierte Dokumenten-Befüllung, Konvertierung und Ingestion im GitHub Repository des Endbenutzers.

---

## 1. GitHub Action Workflow: `.github/workflows/setup-grc.yml`

Dieser Workflow wird automatisch gestartet, sobald der Cloudflare Worker die `config.json` in das Repository des Kunden hochlädt. Er checkt das Kunden-Repository aus und zieht sich anschließend die verschlüsselten DORA/M365-Templates aus unserem privaten **IP-Extensions-Repository** über einen hinterlegten **SSH Deploy Key**.

```yaml
name: Compile Documents & Ingest GRC Data

on:
  push:
    branches:
      - main
    paths:
      - 'config.json'
  workflow_dispatch:

jobs:
  build-and-upload:
    runs-on: ubuntu-latest

    steps:
    # 1. Check out the customer's private GRC repository (Install/Import Repo)
    - name: Checkout Install Repository
      uses: actions/checkout@v4
      with:
        path: '.'

    # 2. Check out our private IP templates repository using an SSH Deploy Key
    - name: Checkout IP Templates Repository
      uses: actions/checkout@v4
      with:
        repository: 'mneshva/grc-ip-extensions' # Unser geschütztes IP Repository
        token: ${{ secrets.IP_REPO_ACCESS_TOKEN }} # Oder SSH Deploy Key: ssh-key: ${{ secrets.IP_DEPLOY_KEY }}
        path: 'ip-templates' # Auslagerung in separaten Unterordner während des Builds

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install System Dependencies (LibreOffice for PDF Conversion)
      run: |
        sudo apt-get update
        sudo apt-get install -y libreoffice pandoc python3-pip

    - name: Install Python Dependencies
      run: |
        pip install python-docx requests

    - name: Copy IP Templates and Populate Placeholders
      run: |
        # Verschiebe Templates aus dem IP-Ordner in die Build-Pipeline
        mkdir -p templates
        cp ip-templates/DORA_M365_Exit_Strategie.docx templates/
        cp ip-templates/IT-Notfallplan-M365-Exchange.docx templates/
        cp ip-templates/IT-Notfallplan-M365-SharePoint.docx templates/
        python scripts/process_templates.py

    - name: Run GRC Ingestion Script
      env:
        CISO_API_URL: ${{ secrets.CISO_API_URL }}
        CISO_API_TOKEN: ${{ secrets.CISO_API_TOKEN }}
      run: |
        python scripts/upload_to_ciso.py

    - name: Clean up temporary IP Templates (Security First)
      run: |
        rm -rf ip-templates
        rm -rf templates

    - name: Commit & Push Compiled PDFs (Data Ownership)
      run: |
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add evidences/*.pdf
        git commit -m "Auto-compiled M365 and DORA evidence PDFs [skip ci]" || echo "No changes to commit"
        git push origin main
```

---

## 2. Python Script für Template-Befüllung: `scripts/process_templates.py`

Dieses Skript liest die `config.json` aus und ersetzt alle Platzhalter in den `.docx` Dokumenten, um anschließend PDFs daraus zu erstellen.

```python
import os
import json
import subprocess
from docx import Document

def replace_text_in_paragraph(paragraph, old_text, new_text):
    if old_text in paragraph.text:
        # Ersetze den Text unter Beibehaltung der Formatierung
        for run in paragraph.runs:
            if old_text in run.text:
                run.text = run.text.replace(old_text, new_text)

def populate_docx(file_path, replacements):
    doc = Document(file_path)
    
    # 1. Haupttext durchsuchen
    for p in doc.paragraphs:
        for old_text, new_text in replacements.items():
            replace_text_in_paragraph(p, old_text, new_text)
            
    # 2. Tabellen durchsuchen
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for old_text, new_text in replacements.items():
                        replace_text_in_paragraph(p, old_text, new_text)
                        
    # 3. Kopf- und Fußzeilen durchsuchen
    for section in doc.sections:
        for header in [section.header, section.first_page_header, section.even_page_header]:
            if header:
                for p in header.paragraphs:
                    for old_text, new_text in replacements.items():
                        replace_text_in_paragraph(p, old_text, new_text)
        for footer in [section.footer, section.first_page_footer, section.even_page_footer]:
            if footer:
                for p in footer.paragraphs:
                    for old_text, new_text in replacements.items():
                        replace_text_in_paragraph(p, old_text, new_text)
                        
    doc.save(file_path)
    print(f"[+] Populated placeholdes in: {file_path}")

def convert_to_pdf(file_path, output_dir):
    # Ruft LibreOffice Headless auf, um das docx in ein PDF zu konvertieren
    cmd = [
        "libreoffice", "--headless", 
        "--convert-to", "pdf", 
        "--outdir", output_dir, 
        file_path
    ]
    subprocess.run(cmd, check=True)
    print(f"[+] Converted to PDF: {file_path} -> {output_dir}")

def main():
    # 1. Config laden
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    replacements = {
        "<Ziel-Tenant-Domain>": config.get("tenant_domain", ""),
        "<Unternehmensname>": config.get("org_name", ""),
        "<RTO-Wert>": f"{config.get('rto_target', '8')} Stunden",
        "<Notfallkoordinator>": config.get("recovery_lead", "IT-Sicherheitsbeauftragter (ISB)")
    }
    
    # Ordner für Ergebnisse erstellen
    os.makedirs("evidences", exist_ok=True)
    
    # Templates bearbeiten
    templates = [
        "templates/DORA_M365_Exit_Strategie.docx",
        "templates/IT-Notfallplan-M365-Exchange.docx",
        "templates/IT-Notfallplan-M365-SharePoint.docx"
    ]
    
    for template in templates:
        if os.path.exists(template):
            # Kopiere Template in evidences Ordner vor Bearbeitung
            dest_docx = os.path.join("evidences", os.path.basename(template))
            import shutil
            shutil.copy(template, dest_docx)
            
            # Befüllen
            populate_docx(dest_docx, replacements)
            # Konvertieren
            convert_to_pdf(dest_docx, "evidences")
        else:
            print(f"[WARNING] Template {template} not found.")

if __name__ == "__main__":
    main()
```

---

## 3. Python Script für GRC Upload: `scripts/upload_to_ciso.py`

Dieses Skript läuft als letzter Schritt in der Pipeline, authentifiziert sich an der API des Kunden und lädt die Dokumente als offizielle Nachweise hoch.

```python
import os
import requests

def upload_evidence(file_path, api_url, token):
    filename = os.path.basename(file_path)
    headers = {
        "Authorization": f"Token {token}"
    }
    
    # 1. Evidence Objekt abfragen oder anlegen
    search_url = f"{api_url}/api/v1/evidences/?search={filename}"
    res = requests.get(search_url, headers=headers)
    
    evidence_id = None
    if res.status_code == 200 and res.json().get("results"):
        evidence_id = res.json()["results"][0]["id"]
        print(f"[+] Found existing Evidence ID: {evidence_id}")
    else:
        # Neu anlegen
        create_url = f"{api_url}/api/v1/evidences/"
        data = {
            "name": f"Automated Evidence - {filename}",
            "description": f"Compiled and customized GRC evidence file {filename}."
        }
        create_res = requests.post(create_url, json=data, headers=headers)
        if create_res.status_code in [200, 201, 211]:
            evidence_id = create_res.json()["id"]
            print(f"[+] Created new Evidence in GRC platform: {evidence_id}")
            
    if not evidence_id:
        print(f"[ERROR] Failed to resolve evidence for {filename}")
        return
        
    # 2. File hochladen (Revision anlegen)
    revision_url = f"{api_url}/api/v1/evidences/{evidence_id}/revisions/"
    with open(file_path, "rb") as f:
        files = {
            "attachment": (filename, f, "application/pdf")
        }
        rev_res = requests.post(revision_url, files=files, headers=headers)
        if rev_res.status_code in [200, 201, 211]:
            print(f"[+] Ingested file attachment revision for {filename}")
        else:
            print(f"[ERROR] Failed to upload revision: {rev_res.text}")

def main():
    api_url = os.environ.get("CISO_API_URL")
    token = os.environ.get("CISO_API_TOKEN")
    
    if not api_url or not token:
        print("[ERROR] Missing environment variables CISO_API_URL or CISO_API_TOKEN")
        return
        
    # Alle generierten PDFs im evidences Ordner hochladen
    evidences_dir = "evidences"
    for file in os.listdir(evidences_dir):
        if file.endswith(".pdf"):
            upload_evidence(os.path.join(evidences_dir, file), api_url, token)

if __name__ == "__main__":
    main()
```
