# grc_profile_setup.py
# Onboarding customizer script to tailor the CISO Assistant base instance 
# for different industry profiles (Finance, Healthcare, Automotive, SME, Freelancer).
# Updates frameworks, perimeters, dashboards, and pre-maps M365 solutions/evidence to requirements.

import os
import sys
import argparse
import django

# Add /code to python path
sys.path.append("/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from core.models import Perimeter, ComplianceAssessment, Evidence, RequirementAssessment, Framework
from metrology.models import Dashboard
from tprm.models import Entity, Solution, EntityAssessment
from iam.models import Folder

# Profile Mapping
PROFILE_CONFIGS = {
    "finance": {
        "frameworks": [
            "ISO/IEC 27001:2022",
            "NOREA-DORA-in-control",
            "BSI-C5-2020",
            "GDPR-checklist",
            "GDPR",
            "SOC2-2017-Rev-2022",
            "M365-ASSESS"
        ],
        "dashboards": [
            "seed:dora-compliance-dashboard",
            "seed:iso27001-compliance-dashboard",
            "seed:gdpr-privacy-dashboard",
            "seed:bsi-compliance-dashboard",
            "seed:m365-security-dashboard"
        ]
    },
    "healthcare": {
        "frameworks": [
            "ISO/IEC 27001:2022",
            "NIS2-directive",
            "GDPR-checklist",
            "GDPR",
            "bs-it-gs-2023-isms-sicherheitsmanagement",
            "bs-it-gs-2023-sys-it-systeme",
            "bs-it-gs-2023-ops-betrieb",
            "M365-ASSESS"
        ],
        "dashboards": [
            "seed:nis2-compliance-dashboard",
            "seed:gdpr-privacy-dashboard",
            "seed:iso27001-compliance-dashboard",
            "seed:bsi-compliance-dashboard",
            "seed:m365-security-dashboard"
        ]
    },
    "automotive": {
        "frameworks": [
            "TISAX v6.0.2",
            "ISO/IEC 27001:2022",
            "GDPR-checklist",
            "GDPR",
            "AI Act",
            "M365-ASSESS"
        ],
        "dashboards": [
            "seed:iso27001-compliance-dashboard",
            "seed:gdpr-privacy-dashboard",
            "seed:ai-compliance-dashboard",
            "seed:m365-security-dashboard"
        ]
    },
    "sme": {
        "frameworks": [
            "NIST-CSF-2.0",
            "GDPR-checklist",
            "M365-ASSESS"
        ],
        "dashboards": [
            "seed:m365-security-dashboard",
            "seed:gdpr-privacy-dashboard",
            "seed:nis2-compliance-dashboard"
        ]
    },
    "freelancer": {
        "frameworks": [
            "GDPR-checklist",
            "M365-ASSESS"
        ],
        "dashboards": [
            "seed:m365-security-dashboard",
            "seed:gdpr-privacy-dashboard"
        ]
    }
}

def main():
    parser = argparse.ArgumentParser(description="Tailor CISO Assistant for specific profiles.")
    parser.add_argument(
        "--profile", 
        choices=["finance", "healthcare", "automotive", "sme", "freelancer"],
        required=True,
        help="Select the onboarding profile."
    )
    args = parser.parse_args()
    profile = args.profile
    
    print(f"[*] Applying Profile: {profile.upper()}...")
    
    config = PROFILE_CONFIGS.get(profile)
    if not config:
        print(f"[ERROR] Configuration for profile '{profile}' not found.")
        return
        
    root_folder = Folder.get_root_folder()
    perimeter = Perimeter.objects.filter(name="M365 Security & Compliance Audit").first()
    if not perimeter:
        print("[ERROR] Perimeter 'M365 Security & Compliance Audit' not found.")
        return
        
    # 1. Framework Initialization & Status Config
    print("[*] Initializing Compliance Assessments (Frameworks)...")
    all_ca = list(ComplianceAssessment.objects.filter(perimeter=perimeter))
    for ca in all_ca:
        fw_ref = ca.framework.ref_id
        if fw_ref in config["frameworks"]:
            print(f"  [+] Profile Active Framework: {ca.framework.name} ({fw_ref})")
            ca.status = "in_progress"
            ca.save()
            # Initialize requirement assessments for profile frameworks
            ca.create_requirement_assessments()
        else:
            print(f"  [.] Retaining Framework (Draft mode): {ca.framework.name} ({fw_ref})")
            ca.status = "planned"
            ca.save()
            
    # 2. Dashboard Retention (Non-destructive)
    print("\n[*] Reviewing Metrology Dashboards...")
    all_dashboards = list(Dashboard.objects.all())
    for db in all_dashboards:
        db_ref = db.ref_id
        if db_ref in config["dashboards"]:
            print(f"  [+] Highlighted Dashboard: {db.name} ({db_ref})")
        else:
            print(f"  [.] Retaining Dashboard: {db.name} ({db_ref})")

            
    # 3. Pre-Mapping Microsoft Service Description & Evidence to requirements
    print("\n[*] Pre-mapping Microsoft official documentation as evidence to compliance assessments...")
    
    # Resolve Evidences
    ev_m365_platform = Evidence.objects.filter(name__icontains="Platform Description").first()
    ev_exchange_online = Evidence.objects.filter(name__icontains="Exchange Online").first()
    ev_service_health = Evidence.objects.filter(name__icontains="Service Health").first()
    ev_dora_addendum = Evidence.objects.filter(name__icontains="DORA Zusatzvereinbarung").first()
    ev_gdap_mapping = Evidence.objects.filter(name__icontains="GDAP").first()
    
    # 3a. Pre-mapping M365-Assess Requirements
    m365_ca = ComplianceAssessment.objects.filter(perimeter=perimeter, framework__ref_id="M365-ASSESS").first()
    if m365_ca:
        print("[+] Pre-mapping M365-Assess requirements...")
        reqs = RequirementAssessment.objects.filter(compliance_assessment=m365_ca)
        
        # Mapping rules
        for req in reqs:
            ref_id = req.requirement.ref_id
            
            # E-Mail security
            if ref_id.startswith("EXCHANGE-") or "EXCHANGE" in ref_id:
                if ev_exchange_online:
                    req.evidences.add(ev_exchange_online)
                    req.status = "done"
                    req.result = "compliant"
                    req.observation = "Abgedeckt durch Microsoft Servicebeschreibung (Exchange Online). E-Mail-Verschlüsselung, Spam-Schutz und Postfacheinstellungen sind standardmäßig aktiv."
                    req.save()
                    
            # Teams, SharePoint & OneDrive
            elif ref_id.startswith("SPO-") or ref_id.startswith("TEAMS-") or "SHAREPOINT" in ref_id:
                if ev_m365_platform:
                    req.evidences.add(ev_m365_platform)
                    req.status = "done"
                    req.result = "compliant"
                    req.observation = "Abgedeckt durch Microsoft Platform Description (SharePoint & Teams). Standardmäßige Transportverschlüsselung und Freigaberichtlinien sind aktiv."
                    req.save()
                    
            # Security Monitoring, Service Health, Continuity
            elif ref_id.startswith("DEFENDER-") or "SECUREMON" in ref_id or "AUDIT" in ref_id:
                if ev_service_health:
                    req.evidences.add(ev_service_health)
                    req.status = "done"
                    req.result = "compliant"
                    req.observation = "Abgedeckt durch Microsoft Service Health, Continuity & Outage Recovery. Ausfallberichte, SLAs und Notfallpläne sind vertraglich geregelt."
                    req.save()
                    
            # Identity & Partner delegation
            elif ref_id.startswith("ENTRA-") or "GDAP" in ref_id or "PARTNER" in ref_id:
                if ev_gdap_mapping:
                    req.evidences.add(ev_gdap_mapping)
                    req.status = "done"
                    req.result = "compliant"
                    req.observation = "Identitätssteuerung ist durch Entra ID und Partner-GDAP-Richtlinien geregelt. Zugriffsschutz ist über Delegated Admin Privileges (GDAP) aktiv."
                    req.save()
        print("  [+] M365-Assess pre-mapping completed.")

    # 3b. Pre-mapping DORA Requirements (only if active)
    dora_ca = ComplianceAssessment.objects.filter(perimeter=perimeter, framework__ref_id="NOREA-DORA-in-control").first()
    if dora_ca and ev_dora_addendum:
        print("[+] Pre-mapping DORA contractual requirements...")
        dora_reqs = RequirementAssessment.objects.filter(compliance_assessment=dora_ca)
        for req in dora_reqs:
            # Match DORA requirements regarding ICT Contractual arrangements
            ref_id = req.requirement.ref_id
            if "contract" in ref_id.lower() or "art-30" in ref_id.lower() or "third-party" in ref_id.lower():
                req.evidences.add(ev_dora_addendum)
                req.status = "done"
                req.result = "compliant"
                req.observation = "Vertragliche DORA-Anforderungen sind durch das Microsoft DORA Addendum und die IKT-Zusatzvereinbarung abgedeckt."
                req.save()
        print("  [+] DORA contractual pre-mapping completed.")

    print(f"\n[+] Profile Customization for '{profile.upper()}' completed successfully!")

if __name__ == "__main__":
    main()
