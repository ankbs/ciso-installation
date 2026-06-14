# grc_setup_m365_deconstruction.py
import os
import sys
import django

# Add /code to path to import django models
sys.path.append("/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from core.models import Asset, Evidence, EvidenceRevision, Perimeter, ComplianceAssessment
from tprm.models import Solution, Entity, Contract, EntityAssessment
from iam.models import Folder
from django.core.files import File

def main():
    print("[*] Starting Microsoft 365 Solution Deconstruction and Ingestion...")
    
    # 1. Get root folder
    root_folder = Folder.get_root_folder()
    
    # 2. Get active perimeter
    perimeter = Perimeter.objects.filter(name="M365 Security & Compliance Audit").first()
    if not perimeter:
        print("[ERROR] Perimeter 'M365 Security & Compliance Audit' not found. Cannot proceed.")
        return
        
    # 3. Retrieve Entity for Microsoft Ireland
    msft = Entity.objects.filter(name="Microsoft Ireland Operations Limited").first()
    if not msft:
        print("[ERROR] Microsoft Ireland entity not found. Cannot proceed.")
        return
    
    main_entity = Entity.objects.filter(name="MKN1411 IT Operations").first()
    if not main_entity:
        # Fallback to any non-microsoft entity as recipient
        main_entity = Entity.objects.exclude(id=msft.id).first()
        
    print(f"[+] Provider: {msft.name}, Recipient: {main_entity.name if main_entity else 'None'}")

    # 4. Retrieve Contracts
    ea_contract = Contract.objects.filter(ref_id="CON-MSFT-EA-M248").first()
    dora_addendum = Contract.objects.filter(ref_id="CON-MSFT-DORA-ADD").first()
    if not ea_contract or not dora_addendum:
        print("[WARNING] EA Contract or DORA Addendum not found by ref_id. Finding by name contains...")
        if not ea_contract:
            ea_contract = Contract.objects.filter(name__icontains="Enterprise Agreement").first()
        if not dora_addendum:
            dora_addendum = Contract.objects.filter(name__icontains="DORA Addendum").first()

    print(f"[+] EA Contract: {ea_contract.name if ea_contract else 'Not Found'}")
    print(f"[+] DORA Addendum: {dora_addendum.name if dora_addendum else 'Not Found'}")

    # 5. Ingest the 3 Compiled PDF files as Evidence
    evidence_dir = "/code/db/evidences"
    evidence_files = {
        "MS-DOC-M365-Platform-Description.pdf": (
            "Microsoft 365 Platform Description & Overview (Official)",
            "Official platform description detailing subscriptions, plans, and integrated apps."
        ),
        "MS-DOC-Exchange-Online-Description.pdf": (
            "Microsoft Exchange Online Service Description (Official)",
            "Official service description detailing mailboxes, transport, and EWS deprecation."
        ),
        "MS-DOC-Service-Health-Continuity.pdf": (
            "Microsoft Service Health, Continuity & Outage Recovery (Official)",
            "Official service health SLAs, uptime metrics, incident response times, and BCDR policies."
        )
    }

    evidences = {}
    print("[*] Ingesting compiled Microsoft PDFs into Evidence repository...")
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
        else:
            print(f"  [+] Evidence already exists: {name}")
            if ev.status != Evidence.Status.APPROVED:
                ev.status = Evidence.Status.APPROVED
                ev.save()
        
        # Attach file revision
        revision = ev.revisions.first()
        if not revision:
            file_path = os.path.join(evidence_dir, filename)
            if os.path.exists(file_path):
                revision = EvidenceRevision(
                    evidence=ev,
                    version=1,
                    observation="Automatisch importierte offizielle Dienstbeschreibung von Microsoft."
                )
                with open(file_path, "rb") as f:
                    revision.attachment.save(filename, File(f), save=True)
                print(f"    [+] Attached PDF file: {filename}")
            else:
                print(f"    [WARNING] PDF file not found at: {file_path}")
        else:
            print(f"    [+] PDF revision already exists.")

    # 6. Link Evidence to Contracts
    if ea_contract and "MS-DOC-M365-Platform-Description.pdf" in evidences:
        ea_contract.evidences.add(evidences["MS-DOC-M365-Platform-Description.pdf"])
        ea_contract.save()
        print("[+] Linked Platform Description to EA Contract.")
        
    if dora_addendum:
        if "MS-DOC-Exchange-Online-Description.pdf" in evidences:
            dora_addendum.evidences.add(evidences["MS-DOC-Exchange-Online-Description.pdf"])
        if "MS-DOC-Service-Health-Continuity.pdf" in evidences:
            dora_addendum.evidences.add(evidences["MS-DOC-Service-Health-Continuity.pdf"])
        dora_addendum.save()
        print("[+] Linked Exchange and Service Health descriptions to DORA Addendum.")

    # 7. Create 18 Constituent Microsoft Solutions
    # Format: ref_id: (name, description, service_type, criticality)
    solutions_data = {
        "SOL-MS-ENTRA": (
            "Microsoft Entra ID (IAM)",
            "Cloud-Identitäts- und Zugriffsverwaltung (SSO, MFA, Conditional Access, PIM). Schützt Anmeldedaten und rollenbasierte Rechte.",
            "eba_TA:S19", # SaaS
            4 # Critical
        ),
        "SOL-MS-EXCHANGE": (
            "Microsoft Exchange Online (E-Mail)",
            "Sichere E-Mail-Kommunikation, Kalenderverwaltung und Postfächer in der Cloud. EOP filtert Phishing und Malware.",
            "eba_TA:S19", # SaaS
            3 # High
        ),
        "SOL-MS-TEAMS": (
            "Microsoft Teams (Collaboration)",
            "Echtzeit-Kommunikation, Online-Meetings, Chats und Zusammenarbeit. Verschlüsselte Sprach-/Videodatenströme.",
            "eba_TA:S19", # SaaS
            3 # High
        ),
        "SOL-MS-SHAREPOINT": (
            "Microsoft SharePoint & OneDrive (Storage)",
            "Cloud-Speicher, Dokumentenverwaltung und Intranet-Webportale. Unterstützt granular gesteuerte Dateifreigaben und Audit-Logs.",
            "eba_TA:S19", # SaaS
            3 # High
        ),
        "SOL-MS-INTUNE": (
            "Microsoft Intune (Endpoint Management)",
            "Geräteverwaltung (MDM) und Anwendungsverwaltung (MAM). Validiert Sicherheitsstatus von Endgeräten vor dem Systemzugriff.",
            "eba_TA:S19", # SaaS
            3 # High
        ),
        "SOL-MS-DEFENDER-ENDPOINT": (
            "Microsoft Defender for Endpoint (EDR)",
            "Endpunkterkennung und -reaktion (EDR), Antimalware, Verhaltensanalyse und integriertes Schwachstellenmanagement.",
            "eba_TA:S04", # Security management
            3 # High
        ),
        "SOL-MS-DEFENDER-O365": (
            "Microsoft Defender for Office 365",
            "Erweiterter Schutz für Exchange/Teams vor Zero-Day-Malware, Phishing-Angriffen und bösartigen Links (Safe Links/Attachments).",
            "eba_TA:S04", # Security management
            3 # High
        ),
        "SOL-MS-PURVIEW-IP": (
            "Microsoft Purview Information Protection & DLP",
            "Datenklassifizierung, Vertraulichkeitskennzeichnung und Verhinderung von Datenabfluss (DLP) für Dateien und E-Mails.",
            "eba_TA:S19", # SaaS
            3 # High
        ),
        "SOL-MS-PURVIEW-AUDIT": (
            "Microsoft Purview Audit & eDiscovery",
            "Zentralisierte Protokollierung von Administrator- und Benutzeraktivitäten (Unified Audit Log), Forensik und eDiscovery.",
            "eba_TA:S19", # SaaS
            3 # High
        ),
        "SOL-MS-POWER-PLATFORM": (
            "Microsoft Power Platform & Copilot (Automation/AI)",
            "Automatisierte Workflows (Power Automate), Low-Code Apps (Power Apps), Datenanalyse (Power BI) und Generative KI (Copilot).",
            "eba_TA:S19", # SaaS
            2 # Medium
        ),
        "SOL-MS-ENTRA-SSE": (
            "Microsoft Entra SSE (Internet/Private Access)",
            "Secure Service Edge (SSE) Lösung bestehend aus Microsoft Entra Internet Access und Microsoft Entra Private Access. Schützt IKT-Netzwerkverbindungen.",
            "eba_TA:S04", # Security management
            4 # Critical
        ),
        "SOL-MS-DEFENDER-EXPERTS": (
            "Microsoft Defender Experts (Managed SOC/XDR)",
            "Ausgelagerte, von Microsoft-Experten betriebene Sicherheitsüberwachung und Bedrohungsjagd (Defender Experts for Hunting & XDR).",
            "eba_TA:S04", # Security management
            4 # Critical
        ),
        "SOL-MS-WINDOWS365": (
            "Windows 365 & AVD (DaaS)",
            "Desktop-as-a-Service (DaaS) für virtualisierte Windows 11 Arbeitsplätze in der Cloud (Cloud-PCs und Azure Virtual Desktop).",
            "eba_TA:S19", # SaaS
            3 # High
        ),
        "SOL-MS-PURVIEW-INSIDER": (
            "Microsoft Purview Insider Risk Management",
            "Identifiziert und entschärft interne Risiken wie Datenabfluss, Verletzung von Richtlinien und Datenmissbrauch. Inkludiert Customer Lockbox.",
            "eba_TA:S19", # SaaS
            3 # High
        ),
        "SOL-MS-INTUNE-SUITE": (
            "Microsoft Intune Suite (Advanced Endpoint Security)",
            "Erweiterte Funktionen für Gerätesicherheit und Verwaltung: Cloud PKI, Endpoint Privilege Management (EPM), Advanced Analytics und Remote Help.",
            "eba_TA:S04", # Security management
            3 # High
        ),
        "SOL-MS-VIVA-SUITE": (
            "Microsoft Viva Suite (Insights & Learning)",
            "Mitarbeitererfahrung und Analyseplattform. Enthält Viva Insights zur Produktivitätsanalyse und Viva Learning für Schulungen.",
            "eba_TA:S19", # SaaS
            1 # Low
        ),
        "SOL-MS-UNIVERSAL-PRINT": (
            "Microsoft Universal Print (Cloud Printing)",
            "Cloudbasierte Druckinfrastruktur für Organisationen. Eliminiert die Notwendigkeit von lokalen Druckservern.",
            "eba_TA:S19", # SaaS
            1 # Low
        ),
        "SOL-MS-SECURITY-COPILOT": (
            "Microsoft Security Copilot (AI Security)",
            "Generative KI-Plattform für Sicherheitsanalysen. Unterstützt SOC-Teams bei der Erkennung und Reaktion auf Cyberbedrohungen.",
            "eba_TA:S04", # Security management
            3 # High
        ),
        "SOL-MS-FORMS": (
            "Microsoft Forms",
            "SaaS-Formular- und Umfrage-Tool zur internen und externen Datenerfassung.",
            "eba_TA:S19", # SaaS
            1 # Low
        ),
        "SOL-MS-PLANNER": (
            "Microsoft Planner & To-Do",
            "SaaS-Aufgaben- und Projektverwaltungstool zur Teamorganisation und Task-Nachverfolgung.",
            "eba_TA:S19", # SaaS
            2 # Medium
        ),
        "SOL-MS-STREAM": (
            "Microsoft Stream",
            "SaaS-Videodienst zur sicheren Aufzeichnung, Freigabe und Verwaltung von Videos und Meetings.",
            "eba_TA:S19", # SaaS
            2 # Medium
        ),
        "SOL-MS-COPILOT-STUDIO": (
            "Microsoft Copilot Studio",
            "SaaS-Entwicklungsplattform zur Erstellung und Verwaltung von intelligenten KI-Copiloten und autonomen Chatbots.",
            "eba_TA:S19", # SaaS
            3 # High
        ),
        "SOL-MS-BOOKINGS": (
            "Microsoft Bookings & Shifts",
            "SaaS-Planungs- und Buchungsanwendung zur Terminvereinbarung für Kunden sowie Schichtplanung für Frontline Workers.",
            "eba_TA:S19", # SaaS
            1 # Low
        )
    }


    alternative_providers_map = {
        "SOL-MS-ENTRA": "Okta / Ping Identity / Google Cloud Identity",
        "SOL-MS-EXCHANGE": "Google Workspace (Gmail) / On-Premises Exchange",
        "SOL-MS-TEAMS": "Zoom / Slack / Webex",
        "SOL-MS-SHAREPOINT": "Google Workspace (Drive) / Box / Dropbox / Nextcloud",
        "SOL-MS-INTUNE": "VMware Workspace ONE / MobileIron (Ivanti) / Jamf",
        "SOL-MS-DEFENDER-ENDPOINT": "CrowdStrike Falcon / SentinelOne / Palo Alto Cortex XDR",
        "SOL-MS-DEFENDER-O365": "Proofpoint / Mimecast / Barracuda",
        "SOL-MS-PURVIEW-IP": "Forcepoint DLP / Netskope / Broadcom (Symantec) DLP",
        "SOL-MS-PURVIEW-AUDIT": "Splunk / Sumo Logic / LogRhythm",
        "SOL-MS-POWER-PLATFORM": "UiPath / Salesforce (MuleSoft) / OutSystems / Mendix",
        "SOL-MS-ENTRA-SSE": "Zscaler Private Access / Cloudflare One / Palo Alto Prisma Access",
        "SOL-MS-DEFENDER-EXPERTS": "CrowdStrike Falcon Complete / SentinelOne Vigilance / Secureworks",
        "SOL-MS-WINDOWS365": "Citrix Virtual Desktops / VMware Horizon / Amazon WorkSpaces",
        "SOL-MS-PURVIEW-INSIDER": "Forcepoint Insider Threat / DTEX Systems / Proofpoint ObserveIT",
        "SOL-MS-INTUNE-SUITE": "BeyondTrust / Ivanti / Jamf Pro",
        "SOL-MS-VIVA-SUITE": "Workday / Culture Amp / Lattice",
        "SOL-MS-UNIVERSAL-PRINT": "Printix / PaperCut Hive / ezeep Blue",
        "SOL-MS-SECURITY-COPILOT": "CrowdStrike Charlotte AI / SentinelOne Purple AI / Google Security AI",
        "SOL-MS-FORMS": "Google Forms / Typeform / SurveyMonkey",
        "SOL-MS-PLANNER": "Trello / Asana / Monday.com",
        "SOL-MS-STREAM": "Vimeo / YouTube (Private)",
        "SOL-MS-COPILOT-STUDIO": "OpenAI Custom GPTs / Flowise / LangFlow",
        "SOL-MS-BOOKINGS": "Calendly / Doodle / Deputy"
    }


    solutions = {}
    print("[*] Initializing constituent Microsoft Solutions...")
    for ref_id, (name, desc, s_type, crit) in solutions_data.items():
        alt_providers = alternative_providers_map.get(ref_id, "Google Workspace")
        sol, sol_created = Solution.objects.get_or_create(
            ref_id=ref_id,
            defaults={
                "name": name,
                "description": desc,
                "provider_entity": msft,
                "recipient_entity": main_entity,
                "is_active": True,
                "dora_ict_service_type": s_type,
                "criticality": crit,
                "storage_of_data": True if "SaaS" in desc or s_type == "eba_TA:S19" else False,
                "data_location_storage": "IE",
                "data_location_processing": "IE",
                "dora_data_sensitiveness": "eba_ZZ:x793" if crit >= 3 else "eba_ZZ:x794",
                "dora_reliance_level": "eba_ZZ:x797", # Full reliance
                "dora_substitutability": "eba_ZZ:x960" if crit >= 3 else "eba_ZZ:x961", # Highly complex / Complex
                "dora_non_substitutability_reason": "eba_ZZ:x965", # Migration complexity
                "dora_has_exit_plan": "eba_BT:x28", # Yes
                "dora_reintegration_possibility": "eba_ZZ:x967", # Highly complex
                "dora_discontinuing_impact": "eba_ZZ:x793" if crit >= 3 else "eba_ZZ:x794",
                "dora_alternative_providers_identified": "eba_BT:x28",
                "dora_alternative_providers": alt_providers
            }
        )
        solutions[ref_id] = sol
        if sol_created:
            print(f"  [+] Created Solution: {name}")
        else:
            print(f"  [+] Solution already exists: {name}")
            sol.dora_alternative_providers = alt_providers
            if not sol.is_active:
                sol.is_active = True
            sol.save()
        
        # Link to DORA Addendum
        if dora_addendum:
            dora_addendum.solutions.add(sol)
            
        # Link to EA Contract for specific enterprise features
        ea_linked_solutions = [
            "SOL-MS-ENTRA", "SOL-MS-INTUNE", "SOL-MS-DEFENDER-ENDPOINT", "SOL-MS-PURVIEW-IP",
            "SOL-MS-ENTRA-SSE", "SOL-MS-DEFENDER-EXPERTS", "SOL-MS-WINDOWS365", "SOL-MS-PURVIEW-INSIDER",
            "SOL-MS-INTUNE-SUITE", "SOL-MS-SECURITY-COPILOT"
        ]
        if ea_contract and ref_id in ea_linked_solutions:
            ea_contract.solutions.add(sol)

    if dora_addendum:
        dora_addendum.save()
    if ea_contract:
        ea_contract.save()

    # 8. Map Solutions to Internal Assets
    print("[*] Mapping Solutions to Internal Assets...")
    
    # 8a. Pre-create all 17 standard assets in their correct folders
    dora_folder, _ = Folder.objects.get_or_create(
        name="DORA — Digital Operational Resilience",
        defaults={
            "parent_folder": root_folder,
            "description": "Folder containing DORA operational resilience assets."
        }
    )
    nist_folder, _ = Folder.objects.get_or_create(
        name="NIST CSF 2.0 — Full Organisational Journey",
        defaults={
            "parent_folder": root_folder,
            "description": "Folder containing NIST CSF 2.0 assets."
        }
    )
    demo_folder, _ = Folder.objects.get_or_create(
        name="DEMO",
        defaults={
            "parent_folder": root_folder,
            "description": "Folder containing Demo assets."
        }
    )

    assets_specs = [
        # DORA Folder
        {
            "name": "Core financial system",
            "type": "SP",
            "folder": dora_folder,
            "description": "Primary banking, trading, or payment processing platform and its databases.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "ICT network infrastructure",
            "type": "SP",
            "folder": dora_folder,
            "description": "Network infrastructure including firewalls, switches, VPN, and segmentation supporting financial operations.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Identity and access management",
            "type": "SP",
            "folder": dora_folder,
            "description": "Directory services, privileged access management, and authentication systems.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Client and transaction data",
            "type": "PR",
            "folder": dora_folder,
            "description": "Financial transaction records, client personal data, account information, and regulatory reporting data.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Backup and recovery systems",
            "type": "SP",
            "folder": dora_folder,
            "description": "Backup infrastructure, disaster recovery sites, and business continuity systems.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        # NIST Folder
        {
            "name": "IT Infrastructure",
            "type": "SP",
            "folder": nist_folder,
            "description": "Servers, network equipment, firewalls, switches, and cloud infrastructure supporting business operations.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Endpoints and User Devices",
            "type": "SP",
            "folder": nist_folder,
            "description": "Laptops, desktops, tablets, and smartphones used by employees and contractors.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Identity and Access Management Systems",
            "type": "SP",
            "folder": nist_folder,
            "description": "Directory services, SSO platforms, MFA systems, and privileged access management tooling.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Business Applications",
            "type": "SP",
            "folder": nist_folder,
            "description": "ERP, CRM, finance, HR, and other core business applications — whether on-premises or SaaS.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Email and Collaboration Platforms",
            "type": "SP",
            "folder": nist_folder,
            "description": "Email services, messaging, file sharing, and video conferencing platforms (e.g. Microsoft 365, Google Workspace).",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Sensitive and Regulated Data",
            "type": "PR",
            "folder": nist_folder,
            "description": "Personally identifiable information (PII), financial records, intellectual property, regulated data, and other critical information assets.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Operational Technology and IoT",
            "type": "SP",
            "folder": nist_folder,
            "description": "Industrial control systems, building management systems, and Internet of Things devices where applicable.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        {
            "name": "Third-Party and Supply Chain Connections",
            "type": "SP",
            "folder": nist_folder,
            "description": "Vendor integrations, managed service providers, API connections, and supply chain dependencies.",
            "security_objectives": {},
            "disaster_recovery_objectives": {}
        },
        # DEMO Folder
        {
            "name": "Ecommerce portal",
            "type": "PR",
            "folder": demo_folder,
            "description": "",
            "security_objectives": {'objectives': {'proof': {'is_enabled': False}, 'safety': {'is_enabled': False}, 'privacy': {'value': 2, 'is_enabled': True}, 'integrity': {'is_enabled': False}, 'authenticity': {'is_enabled': False}, 'availability': {'value': 3, 'is_enabled': True}, 'confidentiality': {'value': 1, 'is_enabled': True}}},
            "disaster_recovery_objectives": {'objectives': {'mtd': {'value': 10800}, 'rpo': {'value': 7200}, 'rto': {'value': 3600}}}
        },
        {
            "name": "hypervisor",
            "type": "SP",
            "folder": demo_folder,
            "description": "",
            "security_objectives": {'objectives': {'proof': {'is_enabled': False}, 'safety': {'is_enabled': False}, 'privacy': {'is_enabled': False}, 'integrity': {'is_enabled': False}, 'authenticity': {'is_enabled': False}, 'availability': {'is_enabled': False}, 'confidentiality': {'is_enabled': False}}},
            "disaster_recovery_objectives": {'objectives': {'mtd': {'value': 0}, 'rpo': {'value': 0}, 'rto': {'value': 0}}}
        },
        {
            "name": "Reseller platform",
            "type": "PR",
            "folder": demo_folder,
            "description": "",
            "security_objectives": {'objectives': {'proof': {'is_enabled': False}, 'safety': {'is_enabled': False}, 'privacy': {'is_enabled': False}, 'integrity': {'value': 2, 'is_enabled': True}, 'authenticity': {'is_enabled': False}, 'availability': {'value': 1, 'is_enabled': True}, 'confidentiality': {'value': 2, 'is_enabled': True}}},
            "disaster_recovery_objectives": {'objectives': {'mtd': {'value': 21600}, 'rpo': {'value': 18000}, 'rto': {'value': 14400}}}
        },
        {
            "name": "kubernetes cluster",
            "type": "SP",
            "folder": demo_folder,
            "description": "",
            "security_objectives": {'objectives': {'proof': {'is_enabled': False}, 'safety': {'is_enabled': False}, 'privacy': {'is_enabled': False}, 'integrity': {'is_enabled': True}, 'authenticity': {'is_enabled': False}, 'availability': {'is_enabled': False}, 'confidentiality': {'value': 1, 'is_enabled': True}}},
            "disaster_recovery_objectives": {'objectives': {'mtd': {'value': 0}, 'rpo': {'value': 0}, 'rto': {'value': 0}}}
        }
    ]

    assets_by_name = {}
    for spec in assets_specs:
        asset, created = Asset.objects.get_or_create(
            name=spec["name"],
            defaults={
                "folder": spec["folder"],
                "type": spec["type"],
                "description": spec["description"] or f"Automatisches GRC-Asset für {spec['name']}.",
                "security_objectives": spec["security_objectives"],
                "disaster_recovery_objectives": spec["disaster_recovery_objectives"]
            }
        )
        assets_by_name[spec["name"]] = asset
        if created:
            print(f"  [+] Created Asset '{asset.name}' ({spec['type']}) in folder '{spec['folder'].name}'")
        else:
            # Update fields if necessary
            updated = False
            if asset.folder != spec["folder"]:
                asset.folder = spec["folder"]
                updated = True
            if asset.type != spec["type"]:
                asset.type = spec["type"]
                updated = True
            if spec["description"] and asset.description != spec["description"]:
                asset.description = spec["description"]
                updated = True
            if asset.security_objectives != spec["security_objectives"]:
                asset.security_objectives = spec["security_objectives"]
                updated = True
            if asset.disaster_recovery_objectives != spec["disaster_recovery_objectives"]:
                asset.disaster_recovery_objectives = spec["disaster_recovery_objectives"]
                updated = True
            if updated:
                asset.save()
                print(f"  [~] Updated Asset '{asset.name}'")
            else:
                print(f"  [.] Asset already exists: '{asset.name}'")

    # 8b. Map Solutions to Internal Assets
    asset_mappings = {
        "SOL-MS-ENTRA": ["Identity and Access Management Systems"],
        "SOL-MS-EXCHANGE": ["Email and Collaboration Platforms"],
        "SOL-MS-TEAMS": ["Email and Collaboration Platforms"],
        "SOL-MS-SHAREPOINT": ["Email and Collaboration Platforms", "Sensitive and Regulated Data"],
        "SOL-MS-INTUNE": ["Endpoints and User Devices"],
        "SOL-MS-DEFENDER-ENDPOINT": ["Endpoints and User Devices"],
        "SOL-MS-DEFENDER-O365": ["Email and Collaboration Platforms"],
        "SOL-MS-PURVIEW-IP": ["Sensitive and Regulated Data"],
        "SOL-MS-PURVIEW-AUDIT": ["IT Infrastructure"],
        "SOL-MS-POWER-PLATFORM": ["Business Applications"],
        "SOL-MS-ENTRA-SSE": ["ICT network infrastructure"],
        "SOL-MS-DEFENDER-EXPERTS": ["IT Infrastructure"],
        "SOL-MS-WINDOWS365": ["Endpoints and User Devices"],
        "SOL-MS-PURVIEW-INSIDER": ["Sensitive and Regulated Data"],
        "SOL-MS-INTUNE-SUITE": ["Identity and Access Management Systems", "Endpoints and User Devices"],
        "SOL-MS-VIVA-SUITE": ["Business Applications"],
        "SOL-MS-UNIVERSAL-PRINT": ["Endpoints and User Devices"],
        "SOL-MS-SECURITY-COPILOT": ["IT Infrastructure"],
        "SOL-MS-FORMS": ["Email and Collaboration Platforms"],
        "SOL-MS-PLANNER": ["Email and Collaboration Platforms"],
        "SOL-MS-STREAM": ["Email and Collaboration Platforms"],
        "SOL-MS-COPILOT-STUDIO": ["Business Applications"],
        "SOL-MS-BOOKINGS": ["Email and Collaboration Platforms"]
    }

    for ref_id, asset_names in asset_mappings.items():
        sol = solutions.get(ref_id)
        if sol:
            for a_name in asset_names:
                asset = assets_by_name.get(a_name)
                if asset:
                    if not sol.assets.filter(id=asset.id).exists():
                        sol.assets.add(asset)
                        print(f"  [+] Mapped Solution '{sol.name}' ➡️ Asset '{asset.name}'")
                    else:
                        print(f"  [.] Solution '{sol.name}' already mapped to '{asset.name}'")
            sol.save()

    # 9. Link Solutions to DORA and NIST Assessments
    print("[*] Linking Solutions to Entity Assessments...")
    dora_assess = ComplianceAssessment.objects.filter(
        name="M365 Security & Compliance Audit - NOREA - DORA in Control Framework V3.0"
    ).first()
    nist_assess = ComplianceAssessment.objects.filter(
        name="M365 Security & Compliance Audit - NIST CSF v2.0 – Journey"
    ).first()

    if dora_assess:
        msft_dora = EntityAssessment.objects.filter(
            entity=msft,
            compliance_assessment=dora_assess
        ).first()
        if msft_dora:
            for sol in solutions.values():
                msft_dora.solutions.add(sol)
            msft_dora.save()
            print(f"  [+] Linked solutions to DORA Entity Assessment: {msft_dora.name}")
        else:
            print("  [WARNING] Microsoft DORA Entity Assessment not found.")
            
    if nist_assess:
        msft_nist = EntityAssessment.objects.filter(
            entity=msft,
            compliance_assessment=nist_assess
        ).first()
        if msft_nist:
            for sol in solutions.values():
                msft_nist.solutions.add(sol)
            msft_nist.save()
            print(f"  [+] Linked solutions to NIST Entity Assessment: {msft_nist.name}")
        else:
            print("  [WARNING] Microsoft NIST Entity Assessment not found.")

    print("[+] Microsoft 365 Solution Deconstruction and Ingestion completed successfully!")

if __name__ == "__main__":
    main()
