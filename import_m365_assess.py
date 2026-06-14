# import_m365_assess.py
# Python script to load M365-Assess registry_bilingual.json into CISO Assistant Django DB

import os
import sys
import json

# Add /code to path to import django models
sys.path.append("/code")

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from core.models import Framework, RequirementNode, Perimeter, ComplianceAssessment
from iam.models import Folder

def run():
    print("[*] Starting M365-Assess Framework Ingestion...")
    
    # 1. Get root folder
    root_folder = Folder.get_root_folder()
    
    # 2. Get active perimeter
    perimeter = Perimeter.objects.filter(name="M365 Security & Compliance Audit").first()
    if not perimeter:
        print("[ERROR] Perimeter 'M365 Security & Compliance Audit' not found. Cannot proceed.")
        return

    # 3. Load bilingual registry JSON
    registry_path = "/code/db/registry_bilingual.json"
    if not os.path.exists(registry_path):
        print(f"[ERROR] Bilingual registry file not found at {registry_path}")
        return
        
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
        
    checks = registry.get("checks", [])
    print(f"[+] Loaded {len(checks)} checks from {registry_path}")
    
    # 4. Create Framework object
    fw_urn = "urn:ciso-assistant:framework:m365-assess"
    framework, fw_created = Framework.objects.get_or_create(
        ref_id="M365-ASSESS",
        defaults={
            "folder": root_folder,
            "name": "M365 Security Assessment Benchmark (M365-Assess)",
            "description": "Automated Microsoft 365 security and compliance assessment containing 292 checks.",
            "urn": fw_urn,
            "locale": "en",
            "default_locale": True,
            "is_published": True,
            "translations": {
                "de": {
                    "name": "M365 Sicherheitsbewertungs-Benchmark (M365-Assess)",
                    "description": "Automatisierte Microsoft 365 Sicherheits- und Compliance-Bewertung mit 292 Prüfpunkten."
                }
            }
        }
    )
    if fw_created:
        print(f"[+] Created Framework: {framework.name}")
    else:
        # Update framework fields if already exists
        framework.name = "M365 Security Assessment Benchmark (M365-Assess)"
        framework.urn = fw_urn
        framework.is_published = True
        framework.translations = {
            "de": {
                "name": "M365 Sicherheitsbewertungs-Benchmark (M365-Assess)",
                "description": "Automatisierte Microsoft 365 Sicherheits- und Compliance-Bewertung mit 292 Prüfpunkten."
            }
        }
        framework.save()
        print(f"[+] Framework already exists. Updated name/translations.")

    # 5. Create Parent Category Nodes
    # To keep things clean, let's create a parent node for each category first
    category_nodes = {}
    categories = set(c.get("category", "COMMON").strip().upper() for c in checks)
    
    category_names_en = {
        "SECUREMON": "Security Monitoring",
        "IDENTITY": "Identity and Access Management",
        "EXCHANGE": "Exchange Online E-Mail Security",
        "SHAREPOINT": "SharePoint Online and OneDrive Security",
        "TEAMS": "Microsoft Teams Collaboration Security",
        "DEVICE": "Device Management and Intune",
        "DATA": "Data Protection and Compliance (Purview)",
        "COMMON": "Common Security Configurations",
        "NETWORKING": "Networking and Infrastructure Security",
        "AUDIT": "Audit Logging and Monitoring",
        "ACCESS": "Access Control",
        "GOVERNANCE": "Governance and Policies",
        "COMPLIANCE": "Compliance Standards",
    }
    
    category_names_de = {
        "SECUREMON": "Sicherheitsüberwachung (Security Monitoring)",
        "IDENTITY": "Identitäts- & Zugriffsverwaltung (IAM)",
        "EXCHANGE": "E-Mail-Sicherheit (Exchange Online)",
        "SHAREPOINT": "Speicher & Kollaboration (SharePoint & OneDrive)",
        "TEAMS": "Zusammenarbeit (Microsoft Teams)",
        "DEVICE": "Geräteverwaltung (Intune)",
        "DATA": "Datenschutz & Compliance (Purview)",
        "COMMON": "Allgemeine Sicherheitskonfiguration",
        "NETWORKING": "Netzwerksicherheit",
        "AUDIT": "Protokollierung & Überwachung (Audit)",
        "ACCESS": "Zugriffssteuerung",
        "GOVERNANCE": "Richtlinien & Compliance (Governance)",
        "COMPLIANCE": "Compliance-Standards",
    }
    
    for cat in categories:
        cat_urn = f"urn:ciso-assistant:requirement:m365-assess:cat:{cat.lower().replace(' ', '-')}"
        name_en = category_names_en.get(cat, cat.replace("-", " ").replace("_", " ").title())
        name_de = category_names_de.get(cat, cat.replace("-", " ").replace("_", " ").title())
        
        # Limit to 195 characters to be safe for CharField max_length=200
        if len(name_en) > 195:
            name_en = name_en[:192] + "..."
        if len(name_de) > 195:
            name_de = name_de[:192] + "..."
            
        cat_node, cat_created = RequirementNode.objects.get_or_create(
            ref_id=f"CAT-{cat}",
            framework=framework,
            defaults={
                "folder": root_folder,
                "urn": cat_urn,
                "name": name_en,
                "description": f"M365-Assess Category: {name_en}",
                "locale": "en",
                "default_locale": True,
                "assessable": False,
                "is_published": True,
                "translations": {
                    "de": {
                        "name": name_de,
                        "description": f"M365-Assess Kategorie: {name_de}"
                    }
                }
            }
        )
        category_nodes[cat] = cat_node
        if cat_created:
            print(f"  [+] Created Category Node: {cat}")
            
    # 6. Ingest all 292 Check Nodes
    print("[*] Ingesting check nodes...")
    created_count = 0
    updated_count = 0
    
    # Create the references directory
    references_dir = "/code/db/references"
    os.makedirs(references_dir, exist_ok=True)
    
    for check in checks:
        check_id = check.get("checkId")
        name_en = check.get("name")
        cat = check.get("category", "COMMON").strip().upper()
        desc_en = check.get("description", "")
        
        translations = check.get("translations", {})
        
        parent = category_nodes.get(cat)
        parent_urn = parent.urn if parent else None
        
        # Save check details to a reference JSON file in bilingual format
        ref_file_path = os.path.join(references_dir, f"{check_id}.json")
        with open(ref_file_path, "w", encoding="utf-8") as rf:
            json.dump(check, rf, indent=4, ensure_ascii=False)
            
        # In case name is too long for Django field (max 200)
        if len(name_en) > 195:
            name_en = name_en[:192] + "..."
            
        trans_de = translations.get("de", {})
        name_de = trans_de.get("name", name_en)
        if len(name_de) > 195:
            name_de = name_de[:192] + "..."
            
        desc_de = trans_de.get("description", desc_en)
        
        # Set reference annotation
        annotation_en = f"Full reference data saved in: `/code/db/references/{check_id}.json`"
        annotation_de = f"Vollständige Referenzdaten gespeichert unter: `/code/db/references/{check_id}.json`"
        
        # Build requirement node URN
        node_urn = f"urn:ciso-assistant:requirement:m365-assess:{check_id.lower()}"
        
        req_node, r_created = RequirementNode.objects.get_or_create(
            ref_id=check_id,
            framework=framework,
            defaults={
                "folder": root_folder,
                "urn": node_urn,
                "name": name_en,
                "description": desc_en,
                "annotation": annotation_en,
                "locale": "en",
                "default_locale": True,
                "assessable": True,
                "is_published": True,
                "parent_urn": parent_urn,
                "translations": {
                    "de": {
                        "name": name_de,
                        "description": desc_de,
                        "annotation": annotation_de
                    }
                }
            }
        )
        
        if r_created:
            created_count += 1
        else:
            # Update existing node to ensure correct description/parent/translations
            req_node.name = name_en
            req_node.urn = node_urn
            req_node.description = desc_en
            req_node.annotation = annotation_en
            req_node.parent_urn = parent_urn
            req_node.is_published = True
            req_node.translations = {
                "de": {
                    "name": name_de,
                    "description": desc_de,
                    "annotation": annotation_de
                }
            }
            req_node.save()
            updated_count += 1
            
    print(f"[+] Ingestion completed. Created: {created_count}, Updated: {updated_count} requirement nodes.")
    
    # 7. Link Framework to Project (Compliance Assessment)
    assessment_name = f"{perimeter.name} - {framework.name}"
    assessment, a_created = ComplianceAssessment.objects.get_or_create(
        name=assessment_name[:250],
        perimeter=perimeter,
        framework=framework,
        defaults={
            "folder": root_folder,
            "description": f"Automated Compliance Assessment for {framework.name}"
        }
    )
    if a_created:
        print(f"[+] Linked framework '{framework.name}' to project '{perimeter.name}'")
    else:
        print(f"[+] Framework '{framework.name}' is already linked to project.")
    
    # Initialize requirement assessments for all nodes
    assessment.create_requirement_assessments()
        
if __name__ == "__main__":
    run()
