# populate_privacy_custom.py
import os
import sys
import django
import random
from datetime import datetime, timedelta

# Setup Django
sys.path.append("/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from core.models import Perimeter, Evidence, AppliedControl, Actor
from tprm.models import Entity
from iam.models import Folder
from privacy.models import (
    Processing,
    Purpose,
    PersonalData,
    DataSubject,
    DataRecipient,
    DataContractor,
    DataTransfer,
    RightRequest,
    DataBreach
)

def main():
    print("[*] Starting Custom GDPR / Privacy Data Seeding...")

    # 1. Clean up existing test privacy data (delete child records first due to cascade or clean dependencies)
    print("[*] Cleaning existing test privacy data...")
    RightRequest.objects.filter(ref_id__startswith="REQ-TEST").delete()
    DataBreach.objects.filter(ref_id__startswith="BR-TEST").delete()
    Processing.objects.filter(name__startswith="[TEST]").delete()

    root_folder = Folder.get_root_folder()
    
    # Get or create actors for assignments
    actors = list(Actor.objects.all())
    if not actors:
        actors = [Actor.objects.create(name="GDPR Officer", folder=root_folder)]
    
    entities = list(Entity.objects.all())
    controls = list(AppliedControl.objects.all()[:5])

    # 2. Seed Processing Activities (RoPA - Record of Processing Activities)
    print("[*] Seeding Record of Processing Activities (RoPA) and associated Personal Data...")
    
    processing_specs = [
        # (name, desc, inf_channel, usage_channel, dpia_req, status, [personal_data_list])
        (
            "Customer Authentication & Registration",
            "Management of customer accounts, registration, login, profile updates, and MFA.",
            "Account Creation",
            "User interface, database storage",
            False,
            "privacy_approved",
            [
                ("Customer Name", "privacy_name", False),
                ("Contact Details", "privacy_contact_details", False),
                ("Online Identifiers", "privacy_online_identifiers", False),
                ("IP Address", "privacy_ip_address", False),
            ]
        ),
        (
            "Newsletter & Marketing Campaigns",
            "Mailing newsletters, customized promotions, and product updates via email to consented users.",
            "Opt-in sign-up form",
            "Email marketing platform (SaaS)",
            False,
            "privacy_draft",
            [
                ("Customer Name", "privacy_name", False),
                ("Email Address", "privacy_email", False),
                ("Cookies Data", "privacy_cookies", False),
            ]
        ),
        (
            "E-Commerce Order Processing & Billing",
            "Processing payments, shipping goods, managing invoice data, and handling refund requests.",
            "Web Checkout",
            "Payment Gateway, ERP system, logistics partner",
            True,
            "privacy_approved",
            [
                ("Customer Name", "privacy_name", False),
                ("Address Details", "privacy_address", False),
                ("Payment Card Information", "privacy_payment_card", True),
                ("Transaction History", "privacy_transaction_history", False),
            ]
        ),
        (
            "Customer Support & Ticketing",
            "Receiving support inquiries, communicating with customers, resolving technical issues.",
            "Support contact form, email support",
            "Support ticketing system",
            False,
            "privacy_draft",
            [
                ("Customer Name", "privacy_name", False),
                ("Email Address", "privacy_email", False),
                ("Correspondence Content", "privacy_correspondence", False),
            ]
        ),
        (
            "Employee Payroll & HR Management",
            "Processing salaries, social security contributions, managing personnel files, and performance reviews.",
            "HR Onboarding forms",
            "Internal HR database, tax authorities",
            True,
            "privacy_approved",
            [
                ("Employee Name", "privacy_name", False),
                ("Salary Information", "privacy_salary_information", True),
                ("Health Data", "privacy_health_data", True),
                ("Social Security Information", "privacy_social_security", True),
            ]
        ),
    ]

    processings = []
    all_created_pd = []
    
    for i, (name, desc, inf_channel, usage_channel, dpia_req, status, pd_list) in enumerate(processing_specs):
        proc = Processing.objects.create(
            name=f"[TEST] {name}",
            folder=root_folder,
            description=desc,
            ref_id=f"PRC-TEST-{i+1:03d}",
            status=status,
            information_channel=inf_channel,
            usage_channel=usage_channel,
            dpia_required=dpia_req,
            dpia_reference=f"DPIA-TEST-{i+1:03d}" if dpia_req else "",
            author=random.choice(actors) if actors else None,
        )
        processings.append(proc)
        print(f"  [+] Processing Activity: {proc.name} (Status: {proc.status})")

        # Assign actors
        if actors:
            proc.assigned_to.add(*random.sample(actors, min(len(actors), 2)))

        # Create Personal Data items for this processing activity
        for pd_name, pd_cat, pd_sensitive in pd_list:
            pd = PersonalData.objects.create(
                processing=proc,
                name=f"[TEST] {pd_name}",
                category=pd_cat,
                is_sensitive=pd_sensitive,
                description=f"GDPR Category: {pd_cat}",
            )
            all_created_pd.append(pd)
            print(f"    [+] Personal Data: {pd.name} (Category: {pd_cat}, Sensitive: {pd_sensitive})")

        # Update sensitive data flag
        proc.update_sensitive_data_flag()

        # Create Purposes
        Purpose.objects.create(
            processing=proc,
            name=f"Purpose for {name}",
            description=f"Primary purpose for processing {name.lower()}.",
            legal_basis="contract" if "Billing" in name or "Payroll" in name or "Authentication" in name else ("consent" if "Marketing" in name else "legitimate_interests"),
        )
        if i % 2 == 0:
            Purpose.objects.create(
                processing=proc,
                name=f"Secondary Purpose for {name}",
                description=f"Supporting analytics and platform improvement for {name.lower()}.",
                legal_basis="legitimate_interests",
            )

        # Create Data Recipients
        categories = ["privacy_internal", "privacy_public", "privacy_other"]
        DataRecipient.objects.create(
            processing=proc,
            category=random.choice(categories),
            name="Internal Analytics Team" if i % 2 == 0 else "External Cloud Provider",
        )

        # Create Data Contractors (Vendors involved)
        if entities:
            DataContractor.objects.create(
                processing=proc,
                entity=random.choice(entities),
                relationship_type="privacy_data_processor",
                country="IE",
                documentation_link="https://www.microsoft.com/privacy",
            )

        # Create Data Transfers
        if entities:
            DataTransfer.objects.create(
                processing=proc,
                entity=random.choice(entities),
                country="US" if i % 2 == 1 else "IE",
                transfer_mechanism="privacy_sccs" if i % 2 == 1 else "privacy_adequacy_decision",
                documentation_link="https://www.microsoft.com/trust-center",
            )

    # 3. Seed Right Requests (SARs)
    print("[*] Seeding Data Subject Access Requests (SARs)...")
    request_specs = [
        ("access", "new", 5),
        ("deletion", "in_progress", 10),
        ("portability", "done", -2),
        ("rectification", "on_hold", 15),
    ]
    
    for i, (req_type, status, days_offset) in enumerate(request_specs):
        req = RightRequest.objects.create(
            folder=root_folder,
            name=f"[TEST] Request {i+1} - {req_type.capitalize()}",
            description=f"Standard GDPR {req_type} request submitted by customer.",
            ref_id=f"REQ-TEST-{i+1:03d}",
            requested_on=datetime.now().date() - timedelta(days=15),
            due_date=datetime.now().date() + timedelta(days=days_offset),
            request_type=req_type,
            status=status,
            observation=f"GDPR officer reviewing request. Verification completed." if status != "new" else "",
        )
        # Link processings
        req.processings.add(random.choice(processings))
        if actors:
            req.owner.add(random.choice(actors))
        print(f"  [+] Right Request: {req.ref_id} (Type: {req_type}, Status: {status})")

    # 4. Seed Data Breaches
    print("[*] Seeding Data Breaches...")
    breach_specs = [
        ("privacy_unauthorized_access", "privacy_high_risk", "privacy_under_investigation", 450, 150),
        ("privacy_loss", "privacy_risk", "privacy_discovered", 50, 0),
        ("privacy_unauthorized_disclosure", "privacy_no_risk", "privacy_closed", 1200, 200),
    ]

    for i, (b_type, risk, status, subjects, data_count) in enumerate(breach_specs):
        breach = DataBreach.objects.create(
            folder=root_folder,
            name=f"[TEST] Data Breach {i+1}",
            description=f"Data incident involving {b_type.split('_')[-1]} of credentials/personal records.",
            ref_id=f"BR-TEST-{i+1:03d}",
            discovered_on=datetime.now() - timedelta(days=random.randint(1, 10)),
            breach_type=b_type,
            risk_level=risk,
            status=status,
            affected_subjects_count=subjects,
            affected_personal_data_count=data_count,
            potential_consequences="Loss of account control, potential phishing targeting affected users.",
            observation="Incident logged, forensic analysis ongoing." if status != "privacy_closed" else "Remediation applied. Case closed.",
        )
        breach.affected_processings.add(random.choice(processings))
        if all_created_pd:
            breach.affected_personal_data.add(random.choice(all_created_pd))
        if controls:
            breach.remediation_measures.add(random.choice(controls))
        if actors:
            breach.assigned_to.add(random.choice(actors))
        print(f"  [+] Data Breach: {breach.ref_id} (Type: {b_type}, Risk: {risk}, Status: {status})")

    print("[+] GDPR / Privacy Data Seeding completed successfully!")

if __name__ == "__main__":
    main()
