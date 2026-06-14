# grc_link_all_frameworks.py
# Python script to propagate Microsoft Ireland and MSP Partner EntityAssessments,
# including all constituent Solutions, Assets, and Evidences, to all active
# ComplianceAssessments in the M365 perimeter.

import os
import sys
import django

# Add /code to path to import django models
sys.path.append("/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from core.models import Perimeter, ComplianceAssessment, Evidence
from tprm.models import Entity, Solution, EntityAssessment
from iam.models import Folder

def main():
    print("[*] Starting propagation of TPRM data to all active GRC frameworks...")
    
    # 1. Resolve Root Folder & Perimeter
    root_folder = Folder.get_root_folder()
    perimeter = Perimeter.objects.filter(name="M365 Security & Compliance Audit").first()
    if not perimeter:
        print("[ERROR] Perimeter 'M365 Security & Compliance Audit' not found.")
        return
        
    print(f"[+] Active Perimeter: {perimeter.name}")

    # 2. Resolve Entities
    msft = Entity.objects.filter(name="Microsoft Ireland Operations Limited").first()
    msp = Entity.objects.filter(name="Managed Cloud Service Provider (MSP)").first()
    
    if not msft or not msp:
        print("[ERROR] Critical TPRM entities (Microsoft, MSP) not found.")
        return
        
    print(f"[+] Entities - Microsoft: {msft.name}, MSP: {msp.name}")

    # 3. Resolve Solutions
    msft_solutions = list(Solution.objects.filter(provider_entity=msft))
    msp_solutions = list(Solution.objects.filter(provider_entity=msp))
    
    print(f"[+] Found {len(msft_solutions)} Microsoft solutions and {len(msp_solutions)} MSP solutions.")

    # 4. Resolve Evidences
    msft_evidence = Evidence.objects.filter(name__icontains="Partner Tenant Governance").first()
    if not msft_evidence:
        msft_evidence = Evidence.objects.filter(name__icontains="M365 Platform Description").first()
        
    msp_evidence = Evidence.objects.filter(name__icontains="GDAP").first()
    if not msp_evidence:
        msp_evidence = Evidence.objects.filter(name__icontains="MSP").first()
        
    print(f"[+] Primary Evidence - Microsoft: {msft_evidence.name if msft_evidence else 'None'}, MSP: {msp_evidence.name if msp_evidence else 'None'}")

    # 5. Resolve active ComplianceAssessments
    assessments = ComplianceAssessment.objects.filter(perimeter=perimeter)
    print(f"[+] Found {assessments.count()} active framework audits in perimeter.")

    # 6. Propagate EntityAssessments and Solutions
    for assessment in assessments:
        print(f"\n[*] Propagating to framework: {assessment.framework.name} ({assessment.framework.ref_id})")
        try:
            # 6a. Microsoft Ireland Operations Limited
            msft_name = f"Microsoft Ireland - {assessment.id} - {assessment.framework.ref_id}"
            msft_ea, msft_created = EntityAssessment.objects.get_or_create(
                entity=msft,
                compliance_assessment=assessment,
                perimeter=perimeter,
                defaults={
                    "name": msft_name,
                    "folder": root_folder,
                    "description": f"Bewertung der IKT-Drittparteienrisiken und Betriebskontinuität von Microsoft Ireland unter dem Framework {assessment.framework.name}.",
                    "status": "done",
                    "conclusion": "ok",
                    "criticality": 4 if assessment.framework.ref_id in ["DORA", "NOREA-DORA-in-control", "annex-nis2-regulation--2024-2690-with-technical-implementation-guidance-by-enisa"] else 3,
                    "dependency": 4,
                    "maturity": 4,
                    "trust": 4,
                    "evidence": msft_evidence
                }
            )
            # Link solutions
            msft_ea.solutions.add(*msft_solutions)
            if msft_evidence and not msft_ea.evidence:
                msft_ea.evidence = msft_evidence
                msft_ea.save()
            print(f"  [+] Microsoft EntityAssessment: '{msft_ea.name}' (Linked Solutions: {msft_ea.solutions.count()})")

            # 6b. MSP Partner
            msp_name = f"MSP Partner - {assessment.id} - {assessment.framework.ref_id}"
            msp_ea, msp_created = EntityAssessment.objects.get_or_create(
                entity=msp,
                compliance_assessment=assessment,
                perimeter=perimeter,
                defaults={
                    "name": msp_name,
                    "folder": root_folder,
                    "description": f"Bewertung der Dienstleistungsrisiken und Zugriffskontrolle des MSP-Partners unter dem Framework {assessment.framework.name}.",
                    "status": "done",
                    "conclusion": "ok",
                    "criticality": 3,
                    "dependency": 3,
                    "maturity": 3,
                    "trust": 3,
                    "evidence": msp_evidence
                }
            )
            # Link solutions
            msp_ea.solutions.add(*msp_solutions)
            if msp_evidence and not msp_ea.evidence:
                msp_ea.evidence = msp_evidence
                msp_ea.save()
            print(f"  [+] MSP EntityAssessment: '{msp_ea.name}' (Linked Solutions: {msp_ea.solutions.count()})")
        except Exception as e:
            print(f"  [WARNING] Skipping framework {assessment.framework.name}: {e}")

    print("\n[+] TPRM propagation completed successfully!")

if __name__ == "__main__":
    main()
