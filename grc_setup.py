# grc_setup.py
# Script to automate the initial configuration of CISO Assistant GRC platform.
# Renames the project to "M365 Security & Compliance Audit", imports all relevant
# EU/German compliance libraries, AI security, CIS controls, MITRE threat catalogs (ATT&CK, D3FEND),
# and links frameworks to the project. It is fully idempotent and safe to run on both fresh and pre-configured systems.

import os
import sys
import json
import uuid

# Add the /code directory to sys.path so Django can find the settings and apps
sys.path.append("/code")

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from django.contrib.auth import get_user_model
from knox.models import AuthToken
from core.models import Perimeter, Framework, ComplianceAssessment, StoredLibrary, RiskMatrix, RiskAssessment, RiskScenario, Threat, Evidence, EvidenceRevision
from iam.models import Folder, UserGroup, Role, RoleAssignment
from tprm.models import Entity, Solution, Contract, EntityAssessment
from django.core.files import File

def setup_tprm(root_folder, perimeter):
    print("[*] Configuring Third-Party Risk Management (TPRM) for DORA and NIST CSF 2.0...")
    try:
        # 1. Get or create Main Entity
        main_entity, created = Entity.objects.get_or_create(
            name="Main",
            defaults={
                "folder": root_folder,
                "description": "Haupt-Finanzunternehmen (Mandant).",
                "ref_id": "ENT-MAIN",
                "is_active": True
            }
        )
        if created:
            print("  [+] Main Entity created.")
        else:
            print("  [+] Main Entity already exists.")
            
        # 2. Get or create Microsoft Ireland
        msft, msft_created = Entity.objects.get_or_create(
            name="Microsoft Ireland Operations Limited",
            defaults={
                "folder": root_folder,
                "description": "Kritischer ICT-Drittdienstleister für Cloud-Infrastruktur, SaaS-Produktivität und Security.",
                "ref_id": "ENT-MSFT",
                "is_active": True,
                "country": "IE",
                "currency": "EUR",
                "dora_provider_person_type": "eba_CT:x212" # Legal person
            }
        )
        if msft_created:
            print("  [+] Microsoft Ireland Entity created.")
        else:
            print("  [+] Microsoft Ireland Entity already exists.")
            
        # 3. Get or create Managed Cloud Service Provider (MSP)
        msp, msp_created = Entity.objects.get_or_create(
            name="Managed Cloud Service Provider (MSP)",
            defaults={
                "folder": root_folder,
                "description": "IT-Betriebspartner für Managed Services, Patching, Support und Security Operations.",
                "ref_id": "ENT-MSP-PARTNER",
                "is_active": True,
                "country": "DE",
                "currency": "EUR",
                "dora_provider_person_type": "eba_CT:x212" # Legal person
            }
        )
        if msp_created:
            print("  [+] MSP Entity created.")
        else:
            print("  [+] MSP Entity already exists.")
            
        # 4. Create or get Solutions
        # M365 Solution
        m365_sol, m365_created = Solution.objects.get_or_create(
            name="Microsoft 365 Enterprise Suite",
            provider_entity=msft,
            recipient_entity=main_entity,
            defaults={
                "description": "SaaS-Kollaboration und Mail (Exchange Online, SharePoint Online, OneDrive, Teams, Purview, Defender).",
                "ref_id": "SOL-M365",
                "is_active": True,
                "dora_ict_service_type": "eba_TA:S19", # SaaS
                "storage_of_data": True,
                "data_location_storage": "IE", # Ireland
                "data_location_processing": "IE",
                "dora_data_sensitiveness": "eba_ZZ:x793", # High
                "dora_reliance_level": "eba_ZZ:x797", # Full reliance
                "dora_substitutability": "eba_ZZ:x960", # Highly complex
                "dora_non_substitutability_reason": "eba_ZZ:x965", # Alternatives & Migration
                "dora_has_exit_plan": "eba_BT:x28", # Yes
                "dora_reintegration_possibility": "eba_ZZ:x967", # Highly complex
                "dora_discontinuing_impact": "eba_ZZ:x793", # High
                "dora_alternative_providers_identified": "eba_BT:x28", # Yes
                "dora_alternative_providers": "Google Workspace"
            }
        )
        
        # Azure Solution
        azure_sol, azure_created = Solution.objects.get_or_create(
            name="Microsoft Azure Cloud Platform",
            provider_entity=msft,
            recipient_entity=main_entity,
            defaults={
                "description": "IaaS/PaaS-Infrastrukturdienste, Cloud-Hosting, Computing und DB-Dienste.",
                "ref_id": "SOL-AZURE",
                "is_active": True,
                "dora_ict_service_type": "eba_TA:S18", # PaaS (or IaaS/PaaS)
                "storage_of_data": True,
                "data_location_storage": "DE", # Germany (Frankfurt)
                "data_location_processing": "DE",
                "dora_data_sensitiveness": "eba_ZZ:x793", # High
                "dora_reliance_level": "eba_ZZ:x797", # Full reliance
                "dora_substitutability": "eba_ZZ:x961", # Medium complexity
                "dora_non_substitutability_reason": "eba_ZZ:x964", # Migration difficulties
                "dora_has_exit_plan": "eba_BT:x28", # Yes
                "dora_reintegration_possibility": "eba_ZZ:x966", # Difficult
                "dora_discontinuing_impact": "eba_ZZ:x793", # High
                "dora_alternative_providers_identified": "eba_BT:x28", # Yes
                "dora_alternative_providers": "Amazon Web Services (AWS), Google Cloud Platform (GCP)"
            }
        )
        
        # Microsoft Sentinel & Defender Security Operations
        sentinel_sol, sentinel_created = Solution.objects.get_or_create(
            name="Microsoft Sentinel & Defender Security Operations",
            provider_entity=msft,
            recipient_entity=main_entity,
            defaults={
                "description": "Cloud-native SIEM/XDR-Sicherheitsüberwachung, Threat Hunting und Endpoint-Detection.",
                "ref_id": "SOL-SENTINEL",
                "is_active": True,
                "dora_ict_service_type": "eba_TA:S04", # Security management services
                "storage_of_data": True,
                "data_location_storage": "DE", # Germany
                "data_location_processing": "DE",
                "dora_data_sensitiveness": "eba_ZZ:x793", # High
                "dora_reliance_level": "eba_ZZ:x796", # Material reliance
                "dora_substitutability": "eba_ZZ:x961", # Medium complexity
                "dora_has_exit_plan": "eba_BT:x28", # Yes
                "dora_reintegration_possibility": "eba_ZZ:x966", # Difficult
                "dora_discontinuing_impact": "eba_ZZ:x793", # High
                "dora_alternative_providers_identified": "eba_BT:x28" # Yes
            }
        )
        
        # MSP Managed Security & Operation Services
        msp_sol, msp_sol_created = Solution.objects.get_or_create(
            name="M365 & Azure Managed Security Services",
            provider_entity=msp,
            recipient_entity=main_entity,
            defaults={
                "description": "First/Second Level Support, Patch-Management, Systemadministration und Security-SOC-Monitoring.",
                "ref_id": "SOL-MSP-MSS",
                "is_active": True,
                "dora_ict_service_type": "eba_TA:S03", # Help desk & support
                "storage_of_data": False,
                "dora_reliance_level": "eba_ZZ:x796", # Material reliance
                "dora_substitutability": "eba_ZZ:x962", # Easily substitutable
                "dora_has_exit_plan": "eba_BT:x28", # Yes
                "dora_reintegration_possibility": "eba_ZZ:x798", # Easy
                "dora_discontinuing_impact": "eba_ZZ:x792" # Medium
            }
        )
        
        print("  [+] TPRM Solutions initialized.")
        
        # 5. Create or get Contracts
        # Microsoft Enterprise Agreement (EA)
        ea_contract, ea_contract_created = Contract.objects.get_or_create(
            name="Microsoft Enterprise Agreement (EA) - M248 & M1186",
            folder=root_folder,
            provider_entity=msft,
            beneficiary_entity=main_entity,
            defaults={
                "description": "Rahmenvereinbarung für Microsoft Volumenlizenzen und Cloud-Dienste (EA-M248 / Enrollment M1186).",
                "status": "active",
                "ref_id": "CON-MSFT-EA-M248",
                "dora_contractual_arrangement": "eba_CO:x2", # Overarching
                "currency": "EUR",
                "governing_law_country": "IE" # Ireland
            }
        )
        if ea_contract_created or ea_contract.solutions.count() == 0:
            ea_contract.solutions.add(m365_sol, azure_sol, sentinel_sol)
            ea_contract.save()
            
        # Microsoft DORA Addendum
        dora_addendum, dora_created = Contract.objects.get_or_create(
            name="Microsoft DORA Addendum (Zusatzvereinbarung IKT)",
            folder=root_folder,
            provider_entity=msft,
            beneficiary_entity=main_entity,
            defaults={
                "description": "Zusatzvereinbarung gemäß DORA Artikel 30 (Wesentliche Vertragsbestimmungen) und RTS 53 (Subunternehmer).",
                "status": "active",
                "ref_id": "CON-MSFT-DORA-ADD",
                "dora_contractual_arrangement": "eba_CO:x3", # Subsequent/associated
                "overarching_contract": ea_contract,
                "currency": "EUR",
                "governing_law_country": "IE"
            }
        )
        if dora_created or dora_addendum.solutions.count() == 0:
            dora_addendum.solutions.add(m365_sol, azure_sol, sentinel_sol)
            dora_addendum.save()
            
        # MSP SLA Contract
        msp_contract, msp_contract_created = Contract.objects.get_or_create(
            name="Managed Services SLA & Support Agreement",
            folder=root_folder,
            provider_entity=msp,
            beneficiary_entity=main_entity,
            defaults={
                "description": "Dienstleistungs- und Supportvertrag für den Betrieb und die Absicherung der Microsoft Cloud-Infrastrukturen.",
                "status": "active",
                "ref_id": "CON-MSP-MSS",
                "dora_contractual_arrangement": "eba_CO:x1", # Standalone
                "currency": "EUR",
                "governing_law_country": "DE" # Germany
            }
        )
        if msp_contract_created or msp_contract.solutions.count() == 0:
            msp_contract.solutions.add(msp_sol)
            msp_contract.save()
            
        print("  [+] TPRM Contracts initialized.")
        
        # 6. Ingest all 20 Evidence Files
        print("[*] Ingesting compliance evidence documents...")
        evidences = {}
        
        # Dictionary format: filename: (name, description)
        evidence_files = {
            "Microsoft General - Microsoft Contract Mapping for DORA (M248 & M1186) (March 2025).docx": (
                "Microsoft Contract Mapping for DORA (Enrollments M248 & M1186)",
                "Microsoft Contract Mapping for DORA (M248 & M1186) showing compliance of Enterprise Agreements."
            ),
            "Microsoft General - Microsoft Contract Mapping for DORA (M850 & M1187) (March 2025).docx": (
                "Microsoft Contract Mapping for DORA (Enrollments M850 & M1187)",
                "Microsoft Contract Mapping for DORA (M850 & M1187) showing compliance of Enterprise Agreements."
            ),
            "dora-zusatzvereinbarung-ikt.pdf": (
                "Microsoft DORA Zusatzvereinbarung (IKT-Zusatzvereinbarung)",
                "Zusatzvereinbarung für IKT-Dienstleistungen gemäß DORA Artikel 30."
            ),
            "DORA_M365_Exit_Strategie.pdf": (
                "Microsoft 365 Exit-Strategie (PDF)",
                "Detaillierte Exit-Strategie und Migrationskonzept für Microsoft 365."
            ),
            "DORA_M365_Exit_Strategie.docx": (
                "Microsoft 365 Exit-Strategie (Word)",
                "Bearbeitbares Migrations- und Exit-Konzept für Microsoft 365."
            ),
            "IT-Notfallplan-0.3.docx": (
                "IT-Notfallplan und Krisenhandbuch",
                "Notfall- und Wiederanlaufplan zur Gewährleistung der Betriebskontinuität (BCDR)."
            ),
            "Microsoft Partner Tenant Governance.pdf": (
                "Microsoft Partner Tenant Governance-Richtlinie",
                "Sicherheitsrichtlinien für die Verwaltung und Absicherung von Partner-Tenants."
            ),
            "P3_Intern_Security_Management.pdf": (
                "MSP Internal Security Management Policy",
                "Sicherheitsleitlinie des Managed Service Providers zur Absicherung der Kundeninfrastrukturen."
            ),
            "Service-Katalog_P3_cloud_solutions_GmbH.pptx": (
                "MSP Service-Katalog und Dienstleistungsverzeichnis",
                "Leistungskatalog des MSP für Cloud-Betrieb und Security-Dienstleistungen."
            ),
            "Microsoft General - ERCM - Business Continuity and Disaster Recovery Plan Validation Report (2025 April - June).pdf": (
                "Microsoft Business Continuity and Disaster Recovery Plan Validation Report",
                "Offizieller Validierungsbericht der Business Continuity Maßnahmen von Microsoft."
            ),
            "Microsoft General - Checklist for Financial Institutions in Germany.pdf": (
                "Microsoft Compliance-Checkliste für Finanzinstitute in Deutschland",
                "Spezifische regulatorische Compliance-Checkliste für die deutsche Finanzbranche."
            ),
            "Microsoft General - Digital Operational Resilience Act (DORA) E-Book (Jan 2025).pdf": (
                "Microsoft Digital Operational Resilience Act (DORA) E-Book",
                "Leitfaden und Erläuterungen zur DORA-Konformität in Microsoft-Umgebungen."
            ),
            "Microsoft General - Helping financial services meet AI compliance needs full paper (May 2024).pdf": (
                "Microsoft AI Compliance Paper for Financial Services",
                "Leitfaden zur Einhaltung von AI-Compliance-Richtlinien im Finanzsektor."
            ),
            "Microsoft General - Microsoft Product to DORA Regulation Guide for Customers (May 2024).pdf": (
                "Microsoft Product to DORA Regulation Guide",
                "Zuordnung von Microsoft Security-Produkten zu den DORA-Artikeln."
            ),
            "dl_Mindestvertragsinhalte_DORA_DE_EN.xlsx": (
                "DORA Mindestvertragsinhalte Checkliste (DE/EN)",
                "Excel-Prüfungsmatrix zur Validierung der DORA-Mindestvertragsinhalte."
            ),
            "ZeroTrustAssessment-2025-06-21T195604.xlsx": (
                "Zero Trust Sicherheits-Assessment",
                "Technisches Assessment des Reifegrades der Zero-Trust-Architektur."
            ),
            "Created_Policies_Mapping_19ae3a92_20260224_1933.json": (
                "GDAP Partner Policy Mapping (M365)",
                "Granular Delegated Admin Privileges (GDAP) Rollenzuordnung und Richtlinienkonfiguration."
            ),
            "EntraRoles_Export.json": (
                "Entra ID Administrative Roles Export",
                "Export der administrativen Berechtigungen und Vergabe im Microsoft Entra ID Tenant."
            ),
            "GDAP_Export_Final.json": (
                "GDAP Delegation Configuration Export",
                "Detaillierter Export der Partner-Berechtigungen und GDAP-Gruppenzuweisungen."
            ),
            "DS-09-Module Delivery Guide-Data security for AI - v8.5.1.docx": (
                "Module Delivery Guide - Data Security for AI",
                "Technischer Leitfaden zur Implementierung von Datensicherheitskontrollen bei Generativer KI."
            )
        }
        
        for filename, (name, desc) in evidence_files.items():
            ev, ev_created = Evidence.objects.get_or_create(
                name=name,
                defaults={
                    "folder": root_folder,
                    "description": desc,
                    "status": Evidence.Status.APPROVED
                }
            )
            evidences[filename] = ev
            if ev_created:
                print(f"  [+] Created Evidence: {name}")
            
            # Create revision if it doesn't exist
            revision = ev.revisions.first()
            if not revision:
                file_path = f"/code/db/evidences/{filename}"
                if os.path.exists(file_path):
                    revision = EvidenceRevision(
                        evidence=ev,
                        version=1,
                        observation="Automatisch importierter Nachweis aus dem GRC-Setup."
                    )
                    with open(file_path, "rb") as f:
                        revision.attachment.save(filename, File(f), save=True)
                    print(f"    [+] Ingested file attachment: {filename}")
                else:
                    print(f"    [WARNING] Physical file not found at: {file_path}")
            else:
                # Ensure status is approved
                if ev.status != Evidence.Status.APPROVED:
                    ev.status = Evidence.Status.APPROVED
                    ev.save()
                    
        # 7. Link Evidence to Contracts
        # ea_contract
        ea_ev_files = [
            "Microsoft General - Microsoft Contract Mapping for DORA (M248 & M1186) (March 2025).docx",
            "Microsoft General - Microsoft Contract Mapping for DORA (M850 & M1187) (March 2025).docx",
            "Microsoft General - ERCM - Business Continuity and Disaster Recovery Plan Validation Report (2025 April - June).pdf",
            "Microsoft General - Microsoft Product to DORA Regulation Guide for Customers (May 2024).pdf"
        ]
        for f in ea_ev_files:
            if f in evidences:
                ea_contract.evidences.add(evidences[f])
        ea_contract.save()
        
        # dora_addendum
        dora_ev_files = [
            "dora-zusatzvereinbarung-ikt.pdf",
            "dl_Mindestvertragsinhalte_DORA_DE_EN.xlsx"
        ]
        for f in dora_ev_files:
            if f in evidences:
                dora_addendum.evidences.add(evidences[f])
        dora_addendum.save()
        
        # msp_contract
        msp_ev_files = [
            "Service-Katalog_P3_cloud_solutions_GmbH.pptx",
            "P3_Intern_Security_Management.pdf"
        ]
        for f in msp_ev_files:
            if f in evidences:
                msp_contract.evidences.add(evidences[f])
        msp_contract.save()
        
        print("  [+] Evidence linked to Contracts successfully.")
        
        # 8. Retrieve Compliance Assessments
        dora_assess = ComplianceAssessment.objects.filter(
            name="M365 Security & Compliance Audit - NOREA - DORA in Control Framework V3.0"
        ).first()
        nist_assess = ComplianceAssessment.objects.filter(
            name="M365 Security & Compliance Audit - NIST CSF v2.0"
        ).first()
        
        if not dora_assess or not nist_assess:
            print("  [WARNING] DORA or NIST ComplianceAssessment objects not found in database. Searching without perimeter prefix...")
            dora_assess = ComplianceAssessment.objects.filter(framework__name="NOREA - DORA in Control Framework V3.0").first()
            nist_assess = ComplianceAssessment.objects.filter(framework__name="NIST CSF v2.0").first()
            
        if not dora_assess:
            print("  [ERROR] DORA ComplianceAssessment not found!")
        if not nist_assess:
            print("  [ERROR] NIST CSF 2.0 ComplianceAssessment not found!")
            
        # 9. Create Third-Party Assessments (Entity Assessments)
        if dora_assess:
            # Microsoft Ireland - DORA Assessment
            msft_dora, created = EntityAssessment.objects.get_or_create(
                name="Microsoft Ireland - DORA Compliance Evaluation",
                entity=msft,
                compliance_assessment=dora_assess,
                perimeter=perimeter,
                defaults={
                    "folder": root_folder,
                    "description": "DORA Artikel 30 & RTS 53 Bewertung von Microsoft Ireland als kritischem Cloud-SaaS-Provider.",
                    "status": "done",
                    "conclusion": "ok",
                    "criticality": 4, # High
                    "dependency": 4,  # High
                    "maturity": 4,    # High
                    "trust": 4,       # High
                    "evidence": evidences.get("Microsoft Partner Tenant Governance.pdf")
                }
            )
            if created or msft_dora.solutions.count() == 0:
                msft_dora.solutions.set([m365_sol, azure_sol, sentinel_sol])
                msft_dora.save()
            print(f"  [+] EntityAssessment created/linked: {msft_dora.name}")
            
            # MSP Partner - DORA Assessment
            msp_dora, created = EntityAssessment.objects.get_or_create(
                name="MSP Partner - DORA Compliance Evaluation",
                entity=msp,
                compliance_assessment=dora_assess,
                perimeter=perimeter,
                defaults={
                    "folder": root_folder,
                    "description": "Bewertung des Managed Service Providers hinsichtlich DORA IKT-Sicherheitsanforderungen und Zugriffskontrolle.",
                    "status": "done",
                    "conclusion": "ok",
                    "criticality": 3, # Medium
                    "dependency": 3,  # Medium
                    "maturity": 3,    # Medium
                    "trust": 3,       # Medium
                    "evidence": evidences.get("GDAP_Export_Final.json")
                }
            )
            if created or msp_dora.solutions.count() == 0:
                msp_dora.solutions.set([msp_sol])
                msp_dora.save()
            print(f"  [+] EntityAssessment created/linked: {msp_dora.name}")
            
        if nist_assess:
            # Microsoft Ireland - NIST CSF 2.0 Assessment
            msft_nist, created = EntityAssessment.objects.get_or_create(
                name="Microsoft Ireland - NIST CSF 2.0 Evaluation",
                entity=msft,
                compliance_assessment=nist_assess,
                perimeter=perimeter,
                defaults={
                    "folder": root_folder,
                    "description": "NIST CSF v2.0 (GV.SC - Supply Chain Risk Management) Audit von Microsoft Ireland.",
                    "status": "done",
                    "conclusion": "ok",
                    "criticality": 4, # High
                    "dependency": 4,  # High
                    "maturity": 4,    # High
                    "trust": 4,       # High
                    "evidence": evidences.get("Microsoft Partner Tenant Governance.pdf")
                }
            )
            if created or msft_nist.solutions.count() == 0:
                msft_nist.solutions.set([m365_sol, azure_sol, sentinel_sol])
                msft_nist.save()
            print(f"  [+] EntityAssessment created/linked: {msft_nist.name}")
            
            # MSP Partner - NIST CSF 2.0 Assessment
            msp_nist, created = EntityAssessment.objects.get_or_create(
                name="MSP Partner - NIST CSF 2.0 Evaluation",
                entity=msp,
                compliance_assessment=nist_assess,
                perimeter=perimeter,
                defaults={
                    "folder": root_folder,
                    "description": "Audit des Managed Service Providers für die Absicherung und IAM-Delegation im Kunden-Tenant nach NIST CSF 2.0.",
                    "status": "done",
                    "conclusion": "ok",
                    "criticality": 3, # Medium
                    "dependency": 3,  # Medium
                    "maturity": 3,    # Medium
                    "trust": 3,       # Medium
                    "evidence": evidences.get("GDAP_Export_Final.json")
                }
            )
            if created or msp_nist.solutions.count() == 0:
                msp_nist.solutions.set([msp_sol])
                msp_nist.save()
            print(f"  [+] EntityAssessment created/linked: {msp_nist.name}")
            
        print("  [+] Third-Party Assessments linked to DORA & NIST CSF 2.0 successfully.")
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Failed to configure TPRM for DORA/NIST: {e}")
        traceback.print_exc()

def setup():
    print("[*] Starting GRC Multi-Framework Configuration (including AI, CIS & MITRE)...")
    
    # 1. Get or create superuser (Idempotent)
    User = get_user_model()
    email = "admin@local.test"
    password = "admin12345"
    user, created = User.objects.get_or_create(email=email, defaults={"is_superuser": True, "is_active": True})
    if created:
        user.set_password(password)
        user.save()
        print(f"[+] Superuser {email} created.")
    else:
        print(f"[+] Superuser {email} already exists.")

    # 1b. Assign superuser to all user groups and create folder role assignments (to ensure visibility in UI)
    try:
        # Add user to all groups
        for g in UserGroup.objects.all():
            user.user_groups.add(g)
        
        # Link user directly to root folder roles
        root = Folder.get_root_folder()
        admin_role = Role.objects.filter(name='BI-RL-ADM').first()
        super_role = Role.objects.filter(name='BI-RL-ADE').first()
        
        if admin_role and root:
            RoleAssignment.objects.get_or_create(user=user, role=admin_role, folder=root, defaults={'is_recursive': True})
        if super_role and root:
            RoleAssignment.objects.get_or_create(user=user, role=super_role, folder=root, defaults={'is_recursive': True})
            
        # Clear cache to ensure Django picks it up
        from django.core.cache import cache
        cache.clear()
        print("[+] Superuser permissions successfully initialized.")
    except Exception as perm_err:
        print(f"[WARNING] Failed to assign permissions to superuser: {perm_err}")

    # 2. Get or create API token (Knox token)
    instance, token = AuthToken.objects.create(user=user)
    print("[+] New Knox API token generated.")

    # 3. Find root folder
    root_folder = Folder.get_root_folder()

    # 4. Rename old project if exists, or create/get "M365 Security & Compliance Audit" (Idempotent)
    perimeter_name = "M365 Security & Compliance Audit"
    
    # Check if old name exists and rename it
    old_perimeter = Perimeter.objects.filter(name="M365 Security Audit").first()
    if old_perimeter:
        old_perimeter.name = perimeter_name
        old_perimeter.save()
        perimeter = old_perimeter
        print(f"[+] Existing perimeter renamed to '{perimeter_name}'.")
    else:
        perimeter, p_created = Perimeter.objects.get_or_create(
            name=perimeter_name,
            defaults={"folder": root_folder, "description": "Automatisierter Microsoft 365 Sicherheits- und Compliance-Audit (ISO 27001, BSI C5, IT-Grundschutz, NIS2, GDPR, DORA, TISAX, CIS, AI, MITRE)"}
        )
        if p_created:
            print(f"[+] Perimeter '{perimeter_name}' created.")
        else:
            print(f"[+] Perimeter '{perimeter_name}' already exists.")

    # 5. Libraries that need to be loaded (Frameworks, Threats, and Mappings)
    # Format: (display_name, urn) – URN used as reliable fallback if name lookup fails
    libraries_to_load = [
        # Standard Regulations (Core)
        ("International standard ISO/IEC 27001:2022",         "urn:intuitem:risk:library:iso27001-2022"),
        ("NIST CSF version 2.0",                              "urn:intuitem:risk:library:nist-csf-2.0"),
        ("NOREA - DORA in Control Framework V3.0",            "urn:intuitem:risk:library:norea"),
        ("NIS 2 directive requirements",                      "urn:intuitem:risk:library:nis2-directive"),
        ("EU Artificial Intelligence Act (AI Act)",           "urn:intuitem:risk:library:ai-act"),
        ("5x5 ISO-27005",                                     "urn:intuitem:risk:library:risk-matrix-5x5-iso-27005"),

        # EU / German Regulations & Core Frameworks
        ("BSI C5 Library",                                    "urn:intuitem:risk:library:bsi-c5-2020"),
        ("GDPR checklist for data controllers",               "urn:intuitem:risk:library:gdpr-checklist"),
        ("General Data Protection Regulation",                "urn:intuitem:risk:library:gdpr"),
        ("IT-Grundschutz-Kompendium – Werkzeug für Informationssicherheit - ISMS: Sicherheitsmanagement", "urn:intuitem:risk:library:bs-it-gs-2023-isms-sicherheitsmanagement"),
        ("IT-Grundschutz-Kompendium – Werkzeug für Informationssicherheit - SYS: IT-Systeme",             "urn:intuitem:risk:library:bs-it-gs-2023-sys-it-systeme"),
        ("IT-Grundschutz-Kompendium – Werkzeug für Informationssicherheit - OPS: Betrieb",               "urn:intuitem:risk:library:bs-it-gs-2023-ops-betrieb"),
        ("IT-Grundschutz-Kompendium – Werkzeug für Informationssicherheit - NET: Netze und Kommunikation","urn:intuitem:risk:library:bs-it-gs-2023-net-netze-und-kommunikation"),
        ("Trusted Information Security Assessment Exchange (TISAX) v6.0.2", "urn:intuitem:risk:library:tisax-v6.0.2"),

        # AI Security & Governance Frameworks
        ("ISO 42001-2023 — Artificial intelligence  — Requirements and Controls outline", "urn:intuitem:risk:library:iso42001-2023"),
        ("NIST AI RMF 1.0",                                   "urn:intuitem:risk:library:nist-ai-rmf-1.0"),
        ("LLM AI Cybersecurity & Governance Checklist",       "urn:intuitem:risk:library:owasp-llm-checklist"),
        ("Google SAIF Framework",                             "urn:intuitem:risk:library:google-saif"),

        # CIS & Cybersecurity Controls
        ("CIS Kubernetes Benchmark",                          "urn:intuitem:risk:library:cis-benchmark-kubernetes"),
        ("Essential Cybersecurity Controls",                  "urn:intuitem:risk:library:ecc-1"),
        ("SOC2-2017 Trust Services Criteria (revision 2022)", "urn:intuitem:risk:library:soc2-2017-rev-2022"),

        # MITRE & Threat Libraries
        ("Mitre ATT&CK v18.1 - Threats and mitigations",     "urn:intuitem:risk:library:mitre-attack"),
        ("OWASP top 10 Web",                                  "urn:intuitem:risk:library:owasp-top-10-web"),

        # ---- PRIORITY ADDITIONS ----
        # Microsoft Cloud Security
        ("Microsoft cloud security benchmark",                "urn:intuitem:risk:library:mcsb-v1"),

        # NIST 800-53 (Goldstandard Compliance)
        ("NIST SP 800-53 revision 5",                         "urn:intuitem:risk:library:nist-sp-800-53-rev5"),

        # DORA Full Package (4 RTS + Base)
        ("Digital Operational Resilience Act (DORA)",         "urn:intuitem:risk:library:dora"),
        ("RTS on criteria for the classification of ICT-related incidents",             "urn:intuitem:risk:library:rts-dora-ict-related-incidents"),
        ("RTS on ICT risk management framework and on simplified ICT risk management framework", "urn:intuitem:risk:library:rts-dora-ict-risk-management"),
        ("RTS to specify the policy on ICT services supporting critical or important functions provided by ICT third-party service providers (TPPs)", "urn:intuitem:risk:library:rts-dora-ictservices-supporting"),
        ("RTS DORA - Incident reporting",                      "urn:intuitem:risk:library:rts-dora-incident-reporting_official"),

        # Cyber Resilience Act
        ("Cyber Resilience Act - Annexes (CRA)",              "urn:intuitem:risk:library:cra-resolution-annexes"),

        # Secure Controls Framework (Meta-Framework)
        ("SCF: Secure Controls Framework (2025.2.2)",         "urn:intuitem:risk:library:scf-2025.2.2"),
    ]

    def _load_library(lib_name, lib_urn):
        """Load a library by name, with URN fallback. Idempotent."""
        stored_lib = None
        # Try name-based lookup first
        try:
            stored_lib = StoredLibrary.objects.get(name=lib_name)
        except StoredLibrary.DoesNotExist:
            pass
        # Fallback: URN-based lookup
        if stored_lib is None:
            try:
                stored_lib = StoredLibrary.objects.get(urn=lib_urn)
            except StoredLibrary.DoesNotExist:
                pass
        if stored_lib is None:
            print(f"[WARNING] Library '{lib_name}' not found (URN: {lib_urn}). Skipping.")
            return
        if not stored_lib.is_loaded:
            print(f"[*] Loading library '{stored_lib.name}' ...")
            stored_lib.load()
            print(f"[+] Library '{stored_lib.name}' successfully loaded.")
        else:
            print(f"[+] Library '{stored_lib.name}' already loaded (Skipped).")

    for lib_name, lib_urn in libraries_to_load:
        try:
            _load_library(lib_name, lib_urn)
        except Exception as e:
            print(f"[ERROR] Failed to load library '{lib_name}': {e}")

    # 6. Frameworks we want to link as compliance assessments
    frameworks_to_link = [
        # Standard Frameworks (Core)
        "International standard ISO/IEC 27001:2022",
        "NIST CSF v2.0",
        "NOREA - DORA in Control Framework V3.0",
        "NIS 2 directive requirements",
        "EU Artificial Intelligence Act",

        # EU / German Regulations & Core Frameworks
        "BSI C5 Library",
        "GDPR checklist for data controllers",
        "General Data Protection Regulation",
        "IT-Grundschutz-Kompendium – Werkzeug für Informationssicherheit - ISMS: Sicherheitsmanagement",
        "IT-Grundschutz-Kompendium – Werkzeug für Informationssicherheit - SYS: IT-Systeme",
        "IT-Grundschutz-Kompendium – Werkzeug für Informationssicherheit - OPS: Betrieb",
        "IT-Grundschutz-Kompendium – Werkzeug für Informationssicherheit - NET: Netze und Kommunikation",
        "Trusted Information Security Assessment Exchange (TISAX) v6.0.2",

        # AI Security & Governance Frameworks
        "ISO 42001-2023 — Artificial intelligence  — Requirements and Controls outline",
        "NIST AI RMF 1.0",
        "LLM AI Cybersecurity & Governance Checklist",
        "Google SAIF Framework",

        # CIS & Cybersecurity Controls
        "CIS Kubernetes Benchmark",
        "Essential Cybersecurity Controls",
        "SOC2-2017 Trust Services Criteria (revision 2022)",

        # ---- PRIORITY ADDITIONS ----
        # Microsoft Cloud Security
        "Microsoft cloud security benchmark",

        # NIST Gold Standard
        "NIST SP 800-53 revision 5",

        # DORA Full Package
        "Digital Operational Resilience Act (DORA)",
        "RTS on criteria for the classification of ICT-related incidents",
        "RTS on ICT risk management framework and on simplified ICT risk management framework",
        "RTS to specify the policy on ICT services supporting critical or important functions provided by ICT third-party service providers (TPPs)",
        "RTS DORA incident reporting",

        # Cyber Resilience Act
        "Cyber Resilience Act - Annexes (CRA)",
    ]

    active_assessments = []

    for fw_name in frameworks_to_link:
        try:
            framework = Framework.objects.get(name=fw_name)
            assessment_name = f"{perimeter_name} - {framework.name}"
            
            assessment, a_created = ComplianceAssessment.objects.get_or_create(
                name=assessment_name[:250],
                perimeter=perimeter,
                framework=framework,
                defaults={"folder": root_folder, "description": f"Automated Compliance Assessment for {framework.name}"}
            )
            
            status_str = "created" if a_created else "already linked"
            print(f"[+] Framework '{fw_name}' is {status_str} for the audit project.")
            
            active_assessments.append({
                "assessment_id": str(assessment.id),
                "assessment_name": assessment.name,
                "framework_name": framework.name
            })
        except Framework.DoesNotExist:
            print(f"[WARNING] Framework '{fw_name}' is not loaded. Cannot link to project.")
        except Exception as e:
            print(f"[ERROR] Failed to link framework '{fw_name}': {e}")

    # 7. Setup Risk Assessment & M365 Risk Scenarios
    print("[*] Configuring Risk Assessment & M365 Risk Scenarios...")
    risk_assessment_id = None
    risk_assessment_name = None
    
    try:
        # Get ISO-27005 5x5 Matrix
        matrix_name = "5x5 ISO-27005"
        risk_matrix = RiskMatrix.objects.filter(name=matrix_name).first()
        if not risk_matrix:
            # Fallback to any enabled matrix
            risk_matrix = RiskMatrix.objects.filter(is_enabled=True).first()
            
        if not risk_matrix:
            print("[WARNING] No active Risk Matrix found. Skipping Risk Assessment creation.")
        else:
            assessment_name = "M365, Dev & AI Sicherheits-Risikoanalyse"
            risk_assessment, ra_created = RiskAssessment.objects.get_or_create(
                name=assessment_name,
                perimeter=perimeter,
                defaults={
                    "folder": root_folder,
                    "description": "Systematische Analyse von Microsoft 365-, DevSecOps- und Künstliche Intelligenz (AI)-Sicherheitsrisiken.",
                    "risk_matrix": risk_matrix
                }
            )
            
            risk_assessment_id = str(risk_assessment.id)
            risk_assessment_name = risk_assessment.name
            ra_status = "created" if ra_created else "already exists"
            print(f"[+] Risk Assessment '{assessment_name}' is {ra_status}.")
            
            # Expanded Modern Risk Scenarios definition (M365, AI/LLMs, and Developer Risks)
            scenarios = [
                # --- Microsoft 365 Risks ---
                {
                    "name": "Identitätsdiebstahl & Account-Übernahme (Phishing / MFA-Bypass)",
                    "description": "Ein Angreifer kompromittiert Benutzerkonten (z. B. durch gezieltes Phishing oder MFA-Bypass wie Session Hijacking/Adversary-in-the-Middle) und erlangt unberechtigten Zugriff auf Microsoft 365-Ressourcen.",
                    "proba": 3,  # ID 3: Sehr wahrscheinlich (very likely)
                    "impact": 3, # ID 3: Kritisch (critical)
                    "threat_refs": ["T1566", "T1078", "T1546", "T1530"]
                },
                {
                    "name": "Infiltration durch Ransomware & Malware",
                    "description": "Schadsoftware wird per E-Mail (Exchange Online) oder Dateifreigabe (OneDrive/SharePoint) eingeschleust und verschlüsselt geschäftskritische Daten oder legt die Infrastruktur lahm.",
                    "proba": 2,  # ID 2: Wahrscheinlich (likely)
                    "impact": 4, # ID 4: Katastrophal (catastrophic)
                    "threat_refs": ["T1486", "T1204"]
                },
                {
                    "name": "Datenabfluss & unbefugte externe Freigaben (Information Leakage)",
                    "description": "Vertrauliche Unternehmensdaten werden absichtlich oder versehentlich über SharePoint Online, OneDrive oder Teams mit externen Parteien geteilt, was zu Compliance-Verstößen führt.",
                    "proba": 3,  # ID 3: Sehr wahrscheinlich (very likely)
                    "impact": 2, # ID 2: Erheblich (serious)
                    "threat_refs": ["T1530", "T1114"]
                },
                {
                    "name": "Missbrauch von OAuth-App-Berechtigungen (Illegitimate Consent)",
                    "description": "Mitarbeiter stimmen unwissentlich bösartigen Drittanbieter-Apps zu (Consent Grant), die weitreichende API-Rechte auf das M365-Postfach oder SharePoint-Daten erhalten (Data Exfiltration).",
                    "proba": 2,  # ID 2: Wahrscheinlich (likely)
                    "impact": 3, # ID 3: Kritisch (critical)
                    "threat_refs": ["T1546"]
                },
                {
                    "name": "Innentäter-Bedrohungen (Insider Threats)",
                    "description": "Mitarbeiter mit legitimen Berechtigungen greifen unbefugt auf sensible Daten zu, löschen diese oder leiten sie vor dem Verlassen des Unternehmens an Konkurrenten weiter.",
                    "proba": 1,  # ID 1: Eher unwahrscheinlich (rather unlikely)
                    "impact": 3, # ID 3: Kritisch (critical)
                    "threat_refs": ["T1078", "T1114", "T1530"]
                },
                # --- AI, LLM & Agent Risks ---
                {
                    "name": "Datenabfluss über Microsoft 365 Copilot (Prompt Leakage)",
                    "description": "Microsoft 365 Copilot greift aufgrund ungenauer SharePoint-Berechtigungen auf vertrauliche interne Dokumente (Gehaltslisten, Strategien) zu und gibt diese über Prompts an unbefugte Mitarbeiter weiter.",
                    "proba": 3,  # ID 3: Sehr wahrscheinlich (very likely)
                    "impact": 3, # ID 3: Kritisch (critical)
                    "threat_refs": ["T1530", "T1078"]
                },
                {
                    "name": "Prompt-Injection & Jailbreaking bei Remote-LLMs (z.B. GPT-4)",
                    "description": "Externe Angreifer manipulieren die Eingaben (Prompt Injection) an firmeneigene LLM-Anwendungen, um Systemgrenzen zu umgehen, System-Prompts auszulesen oder schädlichen Code auszuführen.",
                    "proba": 2,  # ID 2: Wahrscheinlich (likely)
                    "impact": 3, # ID 3: Kritisch (critical)
                    "threat_refs": ["T1190", "T1566"]
                },
                {
                    "name": "Rogue Agents & Kommunikationsvergiftung in Multi-Agenten-Systemen",
                    "description": "Autonome KI-Agenten werden durch manipulierte Eingaben (Prompt Injection/Jailbreak) oder vergiftete Kommunikationskanäle gekapert und führen unerwünschte Aktionen aus (z.B. Löschen von Datenbanken, unbefugter E-Mail-Versand).",
                    "proba": 2,  # ID 2: Wahrscheinlich (likely)
                    "impact": 4, # ID 4: Katastrophal (catastrophic)
                    "threat_refs": ["T1190", "T1078"]
                },
                {
                    "name": "Schatten-IT durch ungesicherte lokale LLM-Instanzen",
                    "description": "Entwickler betreiben unverschlüsselte oder ungesicherte lokale LLMs (z. B. Ollama/Llama) auf ihren Arbeitsplatzrechnern, wodurch sensible Firmendaten und Source-Code lokal im Cache oder ungesicherten Ports verbleiben.",
                    "proba": 2,  # ID 2: Wahrscheinlich (likely)
                    "impact": 2, # ID 2: Erheblich (serious)
                    "threat_refs": ["T1526", "T1530"]
                },
                # --- Developer & Software Supply Chain Risks ---
                {
                    "name": "Supply-Chain-Angriffe über NPM & PyPI (Typosquatting & Dependency Confusion)",
                    "description": "Entwickler binden versehentlich bösartige Open-Source-Bibliotheken (Typosquatting) oder manipulierte interne Abhängigkeiten (Dependency Confusion) in Software-Projekte ein, was zur Kompromittierung des Build-Servers führt.",
                    "proba": 2,  # ID 2: Wahrscheinlich (likely)
                    "impact": 4, # ID 4: Katastrophal (catastrophic)
                    "threat_refs": ["T1204.005", "T25", "T1195", "ICT-003"]
                },
                {
                    "name": "Commit von API-Keys & Zugangsdaten in öffentliche Source-Code-Repositories",
                    "description": "Entwickler checken aus Versehen Zugangsdaten, API-Tokens, SSH-Schlüssel oder Cloud-Secrets in Git-Repositories ein (z. B. auf GitHub/GitLab), was zu sofortiger Cloud-Kompromittierung führt.",
                    "proba": 3,  # ID 3: Sehr wahrscheinlich (very likely)
                    "impact": 4, # ID 4: Katastrophal (catastrophic)
                    "threat_refs": ["T1555.006", "T1552.002", "ICT-019"]
                },
                {
                    "name": "Kompromittierung von Entwickler-Workstations (Developer Target)",
                    "description": "Gezielte Angriffe auf Entwickler-Endpoints (z. B. über manipulierte IDE-Erweiterungen oder präparierte GitHub-PRs) ermöglichen Angreifern den Zugriff auf Code-Repositories und AWS/Azure-Produktionsumgebungen.",
                    "proba": 2,  # ID 2: Wahrscheinlich (likely)
                    "impact": 4, # ID 4: Katastrophal (catastrophic)
                    "threat_refs": ["T1204.002", "T1195.001"]
                },

                # --- DORA: Operationelle Resilienz & ICT-Drittparteienrisiken ---
                {
                    "name": "Ausfall eines kritischen ICT-Drittdienstleisters (DORA Art. 28 – Konzentrationsrisiko)",
                    "description": "Ein kritischer Cloud-Anbieter (z. B. Microsoft Azure / M365) erleidet einen schwerwiegenden Ausfall (Rechenzentrumsausfall, DDoS, regulatorische Abschaltung), was zu einem vollständigen Ausfall der digitalisierten Geschäftsprozesse führt. DORA Art. 28 verlangt ein Konzentrationsrisikomanagement für solche Abhängigkeiten.",
                    "proba": 1,  # ID 1: Eher unwahrscheinlich (aber hoher Impact)
                    "impact": 4, # ID 4: Katastrophal
                    "threat_refs": ["T1498", "T1499"]
                },
                {
                    "name": "Unzureichendes ICT-Vorfallsmanagement & DORA-Meldepflicht-Versäumnis",
                    "description": "Ein wesentlicher ICT-Sicherheitsvorfall (z. B. Ransomware-Angriff auf kritische Systeme) wird nicht fristgerecht nach DORA Art. 19–23 an die BaFin/EBA gemeldet (Erstmeldung: 4h, Zwischenmeldung: 24h). Dies führt zu Bußgeldern und Reputationsschäden.",
                    "proba": 2,  # ID 2: Wahrscheinlich
                    "impact": 3, # ID 3: Kritisch (Strafzahlungen, Reputationsschaden)
                    "threat_refs": ["T1486", "T1490"]
                },
                {
                    "name": "DORA TLPT-Befund: Kritische Sicherheitslücken in produktiven Systemen",
                    "description": "Im Rahmen eines Threat-Led Penetration Tests (TLPT) gemäß DORA Art. 26 werden ausnutzbare kritische Schwachstellen in produktiven Bankensystemen oder Cloud-Schnittstellen aufgedeckt, die bisher nicht bekannt waren (Zero-Day oder veraltete Konfigurationen).",
                    "proba": 2,  # ID 2: Wahrscheinlich
                    "impact": 4, # ID 4: Katastrophal
                    "threat_refs": ["T1190", "T1133", "T1566"]
                },

                # --- MCSB / NIST 800-53: Cloud-Sicherheitsrisiken ---
                {
                    "name": "Fehlkonfiguration von Azure/M365-Diensten (Cloud Misconfiguration)",
                    "description": "Sicherheitsrelevante Fehlkonfigurationen in Azure Active Directory (Entra ID), Exchange Online, SharePoint oder Azure Defender (z. B. offene Storage-Accounts, fehlende Conditional Access Policies, ungesicherte API-Endpoints) ermöglichen unbefugten Datenzugriff oder laterale Bewegung. Direkt adressiert durch Microsoft Cloud Security Benchmark (MCSB) und NIST 800-53 CM-Controls.",
                    "proba": 3,  # ID 3: Sehr wahrscheinlich
                    "impact": 3, # ID 3: Kritisch
                    "threat_refs": ["T1078.004", "T1530", "T1526"]
                },
                {
                    "name": "Privileged Identity Kompromittierung (Entra ID / PIM-Missbrauch)",
                    "description": "Angreifer erlangen dauerhaft privilegierte Rollen in Entra ID (Global Admin, Application Admin) durch schwache Just-in-Time-Konfiguration, fehlende PIM-Richtlinien oder kompromittierte Break-Glass-Accounts. MCSB NS-2/IM-3 und NIST 800-53 AC-6/AC-2 fordern strenge Privilegienverwaltung.",
                    "proba": 2,  # ID 2: Wahrscheinlich
                    "impact": 4, # ID 4: Katastrophal (vollständige Tenant-Übernahme möglich)
                    "threat_refs": ["T1078", "T1098", "T1548"]
                },

                # --- CRA: Produkt- & Hardware-Sicherheitsrisiken ---
                {
                    "name": "Ungepatchte Sicherheitslücken in vernetzten Produkten & IoT-Geräten (CRA Art. 13)",
                    "description": "Im Unternehmen eingesetzte vernetzte Produkte (z. B. IP-Kameras, Smart-Building-Systeme, Industrie-Router) enthalten bekannte, ungepatchte CVEs. Der Cyber Resilience Act verpflichtet Hersteller ab 2027 zur Bereitstellung von Sicherheitsupdates. Bis dahin bleibt das Unternehmen als Betreiber exponiert und muss diese Lücken durch Kompensationsmaßnahmen (Netzwerksegmentierung, Monitoring) absichern.",
                    "proba": 3,  # ID 3: Sehr wahrscheinlich (bekannte CVEs oft ungepacht)
                    "impact": 3, # ID 3: Kritisch
                    "threat_refs": ["T1190", "T1203", "T1068"]
                },

                # --- Regulatory / Compliance-Risiken (übergreifend) ---
                {
                    "name": "Datenschutzverletzung mit DSGVO-Meldepflichtverletzung",
                    "description": "Personenbezogene Daten (Kundendaten, Mitarbeiterdaten) werden durch einen Sicherheitsvorfall (z. B. Datenbankexport, kompromittierter M365-Account) unbefugt offengelegt. Die 72-Stunden-Meldefrist an die Datenschutzaufsichtsbehörde (DSGVO Art. 33) wird aufgrund unzureichender Erkennung oder Eskalationsprozesse nicht eingehalten.",
                    "proba": 2,  # ID 2: Wahrscheinlich
                    "impact": 3, # ID 3: Kritisch (bis 4% Jahresumsatz Bußgeld)
                    "threat_refs": ["T1005", "T1530", "T1114"]
                },
            ]
            
            for sc in scenarios:
                rs, rs_created = RiskScenario.objects.get_or_create(
                    name=sc["name"],
                    risk_assessment=risk_assessment,
                    defaults={
                        "folder": root_folder,
                        "description": sc["description"],
                        "inherent_proba": sc["proba"],
                        "inherent_impact": sc["impact"],
                        "current_proba": sc["proba"],
                        "current_impact": sc["impact"],
                        "residual_proba": sc["proba"],
                        "residual_impact": sc["impact"],
                    }
                )
                
                # Fetch matching threats
                threats = Threat.objects.filter(ref_id__in=sc["threat_refs"])
                if threats.exists():
                    rs.threats.set(threats)
                    rs.save()
                    
                rs_status = "created" if rs_created else "already exists (updated threats)"
                print(f"  [+] Risk Scenario '{sc['name']}' is {rs_status} with {threats.count()} linked threats.")
                
    except Exception as e:
        print(f"[ERROR] Failed to configure Risk Assessment or Scenarios: {e}")

    # 8. Setup TPRM (Third-Party Risk Management)
    setup_tprm(root_folder, perimeter)

    # 9. Write output to json file
    output_data = {
        "api_url": "https://localhost:8443",
        "api_token": token,
        "perimeter_id": str(perimeter.id),
        "perimeter_name": perimeter.name,
        "assessments": active_assessments,
        "risk_assessment_id": risk_assessment_id,
        "risk_assessment_name": risk_assessment_name
    }

    output_path = "/code/db/grc_setup_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)
    print(f"[+] Multi-Framework Configuration written to {output_path}")

if __name__ == "__main__":
    setup()
