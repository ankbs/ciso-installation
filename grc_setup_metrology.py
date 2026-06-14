# grc_setup_metrology.py
# Script to configure the CISO Assistant GRC "Metrology" app.
# It registers 31 custom metric definitions (bilingual), creates instances,
# populates initial sample data points, deletes any old dashboards,
# and creates 7 separate dashboards: DORA, NIS 2, M365, BSI, ISO 27001, GDPR, and EU AI Act.

import os
import sys
import django
from django.utils import timezone

# Add /code to path to import django models
sys.path.append("/code")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from core.models import Terminology, ComplianceAssessment
from django.contrib.contenttypes.models import ContentType
from metrology.models import MetricDefinition, MetricInstance, CustomMetricSample, Dashboard, DashboardWidget
from iam.models import Folder

def main():
    print("[*] Starting Extended 7 GRC Dashboards Configuration...")
    
    # 1. Get root folder
    root_folder = Folder.get_root_folder()
    print(f"[+] Root folder: {root_folder.name}")
    
    # 2. Query Metric Unit Terminologies
    units = {t.name: t for t in Terminology.objects.filter(field_path="metric_definition.unit")}
    percentage_unit = units.get("percentage")
    count_unit = units.get("count")
    score_unit = units.get("score")
    hours_unit = units.get("hours")
    
    if not percentage_unit or not count_unit or not hours_unit:
        print("[ERROR] Required Terminology units (percentage, count, hours) not found.")
        return
        
    print(f"[+] Resolved units - Percentage ID: {percentage_unit.id}, Count ID: {count_unit.id}, Hours ID: {hours_unit.id}")

    # 3. Define 31 Real-World Custom Metrics
    metrics_data = [
        {
            "ref_id": "MET-MS-SECURE-SCORE",
            "urn": "urn:ciso-assistant:metric:ms-secure-score",
            "name": "Microsoft Secure Score",
            "description": "Overall security posture score for the M365 tenant.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 85.0,
            "initial_value": 68.5,
            "translations": {
                "de": {
                    "name": "Microsoft Secure Score",
                    "description": "Gesamtbewertung des Sicherheitsniveaus des M365-Tenants."
                }
            }
        },
        {
            "ref_id": "MET-MS-CONFIG-DRIFTS",
            "urn": "urn:ciso-assistant:metric:ms-config-drifts",
            "name": "M365 Configuration Drifts",
            "description": "Number of failed security checks detected in automated scans.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": count_unit,
            "higher_is_better": False,
            "default_target": 0.0,
            "initial_value": 12.0,
            "translations": {
                "de": {
                    "name": "M365 Konfigurationsabweichungen",
                    "description": "Anzahl der fehlgeschlagenen Sicherheitsprüfungen bei automatisierten Scans."
                }
            }
        },
        {
            "ref_id": "MET-DORA-CRITICAL-SERVICES",
            "urn": "urn:ciso-assistant:metric:dora-critical-ict-services",
            "name": "DORA Critical ICT Services",
            "description": "Number of critical Microsoft SaaS/PaaS solutions registered in GRC TPRM.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": count_unit,
            "higher_is_better": True,
            "default_target": 18.0,
            "initial_value": 18.0,
            "translations": {
                "de": {
                    "name": "DORA Kritische IKT-Dienstleistungen",
                    "description": "Anzahl der in GRC TPRM registrierten kritischen Microsoft SaaS/PaaS-Lösungen."
                }
            }
        },
        {
            "ref_id": "MET-DORA-EXIT-PLAN-COVERAGE",
            "urn": "urn:ciso-assistant:metric:dora-exit-plan-coverage",
            "name": "BCDR Exit Plan Coverage",
            "description": "Percentage of critical services with a validated BCDR exit plan.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 83.3,
            "translations": {
                "de": {
                    "name": "BCDR Exit-Plan Abdeckung",
                    "description": "Prozentsatz der kritischen Dienste mit einem validierten BCDR Exit-Plan."
                }
            }
        },
        {
            "ref_id": "MET-LEGACY-AUTH-DISABLEMENT",
            "urn": "urn:ciso-assistant:metric:legacy-auth-disablement",
            "name": "Legacy Authentication Disablement Rate",
            "description": "Percentage of legacy authentication protocols blocked across the tenant.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "Deaktivierungsrate veralteter Authentifizierung",
                    "description": "Prozentsatz der blockierten Legacy-Authentifizierungsprotokolle im Tenant."
                }
            }
        },
        {
            "ref_id": "MET-MFA-ADMINS-ENABLEMENT",
            "urn": "urn:ciso-assistant:metric:mfa-admins-enablement",
            "name": "MFA Enablement Rate for Admins",
            "description": "Percentage of administrative accounts with MFA enforced and active.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "MFA-Aktivierungsrate für Administratoren",
                    "description": "Prozentsatz der administrativen Konten mit erzwungener und aktiver MFA."
                }
            }
        },
        {
            "ref_id": "MET-GDAP-RELATIONSHIP-HEALTH",
            "urn": "urn:ciso-assistant:metric:gdap-relationship-health",
            "name": "GDAP Partner Relationship Health",
            "description": "Percentage of partner delegated administration relations migrated to GDAP.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "GDAP-Partnerbeziehungs-Integrität",
                    "description": "Prozentsatz der zu GDAP migrierten Partneradministrationsrechte."
                }
            }
        },
        {
            "ref_id": "MET-SLA-REMEDIATION-RATE",
            "urn": "urn:ciso-assistant:metric:sla-remediation-rate",
            "name": "Inherent Risk Remediation SLA Rate",
            "description": "Percentage of findings remediated within established SLA timeframes.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 95.0,
            "initial_value": 91.5,
            "translations": {
                "de": {
                    "name": "SLA-Einhaltungsrate der Risikobehebung",
                    "description": "Prozentsatz der Befunde, die innerhalb der SLA-Fristen behoben wurden."
                }
            }
        },
        {
            "ref_id": "MET-DLP-POLICY-MATCHES",
            "urn": "urn:ciso-assistant:metric:dlp-policy-matches",
            "name": "Data Loss Prevention Policy Match Count",
            "description": "Number of high-severity DLP rule matches in Microsoft Purview during the last 30 days.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": count_unit,
            "higher_is_better": False,
            "default_target": 0.0,
            "initial_value": 4.0,
            "translations": {
                "de": {
                    "name": "Anzahl der DLP-Richtlinientreffer",
                    "description": "Anzahl der schwerwiegenden DLP-Regeltreffer in Microsoft Purview in den letzten 30 Tagen."
                }
            }
        },
        {
            "ref_id": "MET-PHISHING-FAIL-RATE",
            "urn": "urn:ciso-assistant:metric:phishing-simulation-fail-rate",
            "name": "Phishing Simulation Fail Rate",
            "description": "Percentage of users who clicked on a simulated phishing email in the last run.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": False,
            "default_target": 3.0,
            "initial_value": 7.2,
            "translations": {
                "de": {
                    "name": "Phishing-Simulations-Quote",
                    "description": "Prozentsatz der Benutzer, die beim letzten Test auf eine simulierte Phishing-E-Mail geklickt haben."
                }
            }
        },
        {
            "ref_id": "MET-BREAK-GLASS-STATUS",
            "urn": "urn:ciso-assistant:metric:break-glass-status",
            "name": "Tenant Break-Glass Accounts Status",
            "description": "Verification rate and monitoring status of emergency access accounts.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "Notfallkonten-Status (Break-Glass)",
                    "description": "Überprüfungsrate und Überwachungsstatus von Notfallzugriffskonten."
                }
            }
        },
        # DORA specific
        {
            "ref_id": "MET-DORA-CONTRACT-COMPLIANCE",
            "urn": "urn:ciso-assistant:metric:dora-contract-compliance",
            "name": "DORA Contract Compliance",
            "description": "Percentage of critical provider contractual arrangements meeting DORA Article 30 requirements.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 90.0,
            "translations": {
                "de": {
                    "name": "DORA-Vertragskonformität",
                    "description": "Prozentsatz der Verträge mit kritischen IKT-Drittdienstleistern, die die Mindestinhalte nach DORA Artikel 30 erfüllen."
                }
            }
        },
        {
            "ref_id": "MET-DORA-VENDOR-ASSESSMENTS",
            "urn": "urn:ciso-assistant:metric:dora-vendor-assessments",
            "name": "DORA Vendor Assessments Completed",
            "description": "Percentage of registered critical third-party providers with fully completed annual security assessments.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "Abgeschlossene DORA-Dienstleisterbewertungen",
                    "description": "Prozentsatz der kritischen Drittdienstleister mit vollständig abgeschlossenem jährlichen Sicherheitsaudit."
                }
            }
        },
        {
            "ref_id": "MET-DORA-INCIDENT-SLA",
            "urn": "urn:ciso-assistant:metric:dora-incident-sla",
            "name": "DORA Incident Notification SLA",
            "description": "Percentage of major ICT incidents reported to supervisory authorities within regulatory timeframes.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "DORA-Vorfallsmeldefrist-SLA",
                    "description": "Prozentsatz der schwerwiegenden IKT-Vorfälle, die innerhalb der gesetzlichen Fristen an die Behörden gemeldet wurden."
                }
            }
        },
        # NIS 2 specific
        {
            "ref_id": "MET-NIS2-MFA-RATE",
            "urn": "urn:ciso-assistant:metric:nis2-mfa-rate",
            "name": "NIS2 MFA Enablement Rate",
            "description": "Percentage of all active corporate user accounts with multi-factor authentication enforced.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 98.5,
            "translations": {
                "de": {
                    "name": "NIS2 MFA-Aktivierungsquote",
                    "description": "Prozentsatz aller aktiven Unternehmens-Benutzerkonten mit erzwungener Mehrfaktor-Authentifizierung."
                }
            }
        },
        {
            "ref_id": "MET-NIS2-IR-TIME",
            "urn": "urn:ciso-assistant:metric:nis2-incident-response-time",
            "name": "NIS2 Incident Mitigation Time",
            "description": "Average time in hours taken to contain and mitigate security incidents.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": hours_unit,
            "higher_is_better": False,
            "default_target": 2.0,
            "initial_value": 1.5,
            "translations": {
                "de": {
                    "name": "NIS2 Vorfallsbehebungszeit",
                    "description": "Durchschnittliche Zeit in Stunden zur Eindämmung und Behebung von Sicherheitsvorfällen."
                }
            }
        },
        {
            "ref_id": "MET-NIS2-AWARENESS-TRAINING",
            "urn": "urn:ciso-assistant:metric:nis2-awareness-training",
            "name": "NIS2 Security Awareness Training",
            "description": "Completion rate of mandatory cybersecurity awareness training among employees.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 92.0,
            "translations": {
                "de": {
                    "name": "NIS2 Sicherheitsunterweisung-Quote",
                    "description": "Abschlussquote der jährlichen Pflichtschulungen zur Cybersicherheit unter allen Mitarbeitern."
                }
            }
        },
        {
            "ref_id": "MET-NIS2-VULN-SLA",
            "urn": "urn:ciso-assistant:metric:nis2-vuln-sla",
            "name": "NIS2 Vulnerability Remediation SLA",
            "description": "Percentage of high and critical vulnerabilities remediated within the SLA window.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 95.0,
            "initial_value": 88.5,
            "translations": {
                "de": {
                    "name": "NIS2 Schwachstellenbehebung-SLA",
                    "description": "Prozentsatz der hohen und kritischen Sicherheitslücken, die innerhalb des SLA-Zeitfensters behoben wurden."
                }
            }
        },
        {
            "ref_id": "MET-NIS2-BACKUP-TEST",
            "urn": "urn:ciso-assistant:metric:nis2-backup-test",
            "name": "NIS2 Backup Test Frequency",
            "description": "Percentage of critical datasets with successfully tested backup restorations in the last 30 days.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "NIS2 Backup-Testabdeckung",
                    "description": "Prozentsatz der kritischen Datensätze, für die in den letzten 30 Tagen erfolgreiche Wiederherstellungstests durchgeführt wurden."
                }
            }
        },
        # BSI specific
        {
            "ref_id": "MET-BSI-GS-IMPLEMENTATION",
            "urn": "urn:ciso-assistant:metric:bsi-gs-implementation",
            "name": "BSI Grundschutz Safeguards Implementation Rate",
            "description": "Percentage of required BSI IT-Grundschutz kompendium safeguards fully implemented.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 78.5,
            "translations": {
                "de": {
                    "name": "BSI Grundschutz-Umsetzungsquote",
                    "description": "Prozentsatz der erforderlichen Sicherheitsanforderungen des BSI IT-Grundschutz-Kompendiums, die vollständig umgesetzt sind."
                }
            }
        },
        {
            "ref_id": "MET-BSI-C5-STATUS",
            "urn": "urn:ciso-assistant:metric:bsi-c5-status",
            "name": "BSI C5 Cloud Attestation Status",
            "description": "Percentage of active cloud service solutions covered under a validated BSI C5 SOC 2 audit report.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 88.9,
            "translations": {
                "de": {
                    "name": "BSI C5 Cloud-Testierungsquote",
                    "description": "Prozentsatz der genutzten Cloud-Dienste, für die ein gültiger Testierungsbericht nach BSI C5 vorliegt."
                }
            }
        },
        {
            "ref_id": "MET-BSI-AUDIT-CADENCE",
            "urn": "urn:ciso-assistant:metric:bsi-audit-cadence",
            "name": "BSI Internal Audit Cadence",
            "description": "Fulfillment rate of scheduled quarterly internal security self-assessments.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "BSI Interne Audit-Quote",
                    "description": "Erfüllungsquote der geplanten vierteljährlichen internen Sicherheitsaudits und Selbstauskünfte."
                }
            }
        },
        # ISO 27001 specific
        {
            "ref_id": "MET-ISO-CONTROL-EFFECTIVENESS",
            "urn": "urn:ciso-assistant:metric:iso-control-effectiveness",
            "name": "ISO 27001 Annex A Control Effectiveness",
            "description": "Percentage of Annex A security controls assessed as fully effective in the last management review.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 95.0,
            "initial_value": 86.5,
            "translations": {
                "de": {
                    "name": "ISO 27001 Wirksamkeit Annex A Kontrollen",
                    "description": "Prozentsatz der Sicherheitskontrollen aus Annex A, die im letzten Management-Review als voll wirksam eingestuft wurden."
                }
            }
        },
        {
            "ref_id": "MET-ISO-SECURITY-EXCEPTIONS",
            "urn": "urn:ciso-assistant:metric:iso-security-exceptions",
            "name": "Active Security Exceptions",
            "description": "Number of active, formally approved policy deviations or security exceptions.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": count_unit,
            "higher_is_better": False,
            "default_target": 0.0,
            "initial_value": 3.0,
            "translations": {
                "de": {
                    "name": "Aktive Sicherheitsausnahmen",
                    "description": "Anzahl der aktiven, formal genehmigten Richtlinienabweichungen und Sicherheitsausnahmen."
                }
            }
        },
        {
            "ref_id": "MET-ISO-INTERNAL-AUDIT-SLA",
            "urn": "urn:ciso-assistant:metric:iso-internal-audit-sla",
            "name": "Internal Audit Findings Remediation SLA",
            "description": "Percentage of internal audit non-conformities remediated within defined corrective action plans.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 90.0,
            "initial_value": 82.0,
            "translations": {
                "de": {
                    "name": "ISO 27001 Mängelbehebungsquote (Audit)",
                    "description": "Prozentsatz der im internen Audit festgestellten Abweichungen, die fristgerecht behoben wurden."
                }
            }
        },
        # GDPR specific
        {
            "ref_id": "MET-GDPR-DPIA-COVERAGE",
            "urn": "urn:ciso-assistant:metric:gdpr-dpia-coverage",
            "name": "DPIA Coverage for Critical Processing Systems",
            "description": "Percentage of high-risk processing systems covered by a fully completed Data Protection Impact Assessment.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 94.4,
            "translations": {
                "de": {
                    "name": "DSGVO DSFA-Abdeckungsquote",
                    "description": "Prozentsatz der Hochrisiko-Verarbeitungstätigkeiten, für die eine Datenschutz-Folgenabschätzung (DSFA) vorliegt."
                }
            }
        },
        {
            "ref_id": "MET-GDPR-SAR-SLA",
            "urn": "urn:ciso-assistant:metric:gdpr-sar-sla",
            "name": "Subject Access Request (SAR) SLA Adherence",
            "description": "Percentage of subject access requests completed and answered within the 30-day statutory limit.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "DSGVO Betroffenenanfragen-SLA",
                    "description": "Prozentsatz der Auskunftsbegehren von Betroffenen, die innerhalb der gesetzlichen 30-Tage-Frist beantwortet wurden."
                }
            }
        },
        {
            "ref_id": "MET-GDPR-TRAINING-RATE",
            "urn": "urn:ciso-assistant:metric:gdpr-training-rate",
            "name": "Data Privacy Training Completion Rate",
            "description": "Percentage of employees who completed data protection and GDPR awareness training.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 95.0,
            "translations": {
                "de": {
                    "name": "DSGVO Datenschutzunterweisung-Quote",
                    "description": "Abschlussquote der Pflichtunterweisungen zum Datenschutz unter den Mitarbeitern."
                }
            }
        },
        # AI Act specific
        {
            "ref_id": "MET-AI-SYSTEM-INVENTORY",
            "urn": "urn:ciso-assistant:metric:ai-system-inventory",
            "name": "AI Model Risk Classification Rate",
            "description": "Percentage of deployed AI systems fully inventoried and risk-classified under EU AI Act.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 100.0,
            "translations": {
                "de": {
                    "name": "KI-Modell Risikoklassifizierungsquote",
                    "description": "Prozentsatz der im Unternehmen eingesetzten KI-Systeme, die gemäß dem EU AI Act inventarisiert und klassifiziert sind."
                }
            }
        },
        {
            "ref_id": "MET-AI-RISK-ASSESSMENTS",
            "urn": "urn:ciso-assistant:metric:ai-risk-assessments",
            "name": "AI Conformity & Safety Assessments",
            "description": "Percentage of high-risk AI models with fully completed conformity assessments and safety documentations.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": percentage_unit,
            "higher_is_better": True,
            "default_target": 100.0,
            "initial_value": 80.0,
            "translations": {
                "de": {
                    "name": "KI-Konformitätsbewertungsquote",
                    "description": "Prozentsatz der Hochrisiko-KI-Systeme mit vollständig abgeschlossener Konformitätsbewertung und Sicherheitsdokumentation."
                }
            }
        },
        {
            "ref_id": "MET-AI-SECURITY-MATCHES",
            "urn": "urn:ciso-assistant:metric:ai-security-matches",
            "name": "AI Security Policy Violations",
            "description": "Number of detected AI security incidents, data leakages, or prompt injection attempts.",
            "category": MetricDefinition.Category.QUANTITATIVE,
            "unit": count_unit,
            "higher_is_better": False,
            "default_target": 0.0,
            "initial_value": 2.0,
            "translations": {
                "de": {
                    "name": "KI-Sicherheitsverstöße",
                    "description": "Anzahl der detektierten KI-Sicherheitsvorfälle, Prompt-Injections oder Datenabflüsse über Copilot."
                }
            }
        }
    ]

    metric_instances = {}

    print("[*] Registering bilingual Metric Definitions & Instances...")
    for m in metrics_data:
        # Get or create definition
        metric_def, def_created = MetricDefinition.objects.get_or_create(
            ref_id=m["ref_id"],
            defaults={
                "urn": m["urn"],
                "name": m["name"],
                "description": m["description"],
                "translations": m["translations"],
                "locale": "en",
                "default_locale": True,
                "category": m["category"],
                "unit": m["unit"],
                "higher_is_better": m["higher_is_better"],
                "default_target": m["default_target"],
                "is_published": True
            }
        )
        if def_created:
            print(f"  [+] Created Metric Definition: {m['name']}")
        else:
            # Update fields
            metric_def.urn = m["urn"]
            metric_def.name = m["name"]
            metric_def.description = m["description"]
            metric_def.translations = m["translations"]
            metric_def.unit = m["unit"]
            metric_def.higher_is_better = m["higher_is_better"]
            metric_def.default_target = m["default_target"]
            metric_def.save()
            print(f"  [+] Updated Metric Definition: {m['name']}")

        # Get or create instance
        metric_inst, inst_created = MetricInstance.objects.get_or_create(
            ref_id=m["ref_id"],
            defaults={
                "folder": root_folder,
                "metric_definition": metric_def,
                "name": m["name"],
                "description": m["description"],
                "status": MetricInstance.Status.ACTIVE,
                "collection_frequency": MetricInstance.Frequency.DAILY,
                "target_value": m["default_target"]
            }
        )
        metric_instances[m["ref_id"]] = metric_inst
        if inst_created:
            print(f"    [+] Created Metric Instance: {m['name']}")
        else:
            metric_inst.metric_definition = metric_def
            metric_inst.name = m["name"]
            metric_inst.description = m["description"]
            metric_inst.status = MetricInstance.Status.ACTIVE
            metric_inst.target_value = m["default_target"]
            metric_inst.save()
            print(f"    [+] Updated Metric Instance: {m['name']}")

        # Add initial sample if none exists
        if not metric_inst.samples.exists():
            CustomMetricSample.objects.create(
                metric_instance=metric_inst,
                folder=root_folder,
                timestamp=timezone.now(),
                value={"result": m["initial_value"]},
                observation="Initialer Wert aus Sicherheits- und Compliance-Audit. (Automatisch importiert)"
            )
            print(f"      [+] Created Initial Sample: {m['initial_value']}")
        else:
            print("      [+] Sample already exists. Skipping.")

    # 4. Clean up old combined dashboard
    Dashboard.objects.filter(ref_id="seed:m365-dora-compliance").delete()

    # 5. Resolve Compliance Assessments
    print("[*] Resolving Compliance Assessments for built-in widgets...")
    assessments = {}
    
    # helper query
    def get_assessment(ref_id):
        return ComplianceAssessment.objects.filter(
            perimeter__name="M365 Security & Compliance Audit",
            framework__ref_id=ref_id
        ).first()

    # Resolve assessments
    m365_assess = get_assessment("M365-ASSESS")
    if m365_assess: assessments["m365_assess"] = m365_assess
    
    dora_assess = get_assessment("NOREA-DORA-in-control")
    if dora_assess: assessments["dora_assess"] = dora_assess
    
    nis2_assess = get_assessment("annex-nis2-regulation--2024-2690-with-technical-implementation-guidance-by-enisa") or ComplianceAssessment.objects.filter(perimeter__name="M365 Security & Compliance Audit", framework__ref_id__icontains="nis2").first()
    if nis2_assess: assessments["nis2_assess"] = nis2_assess
    
    bsi_c5 = get_assessment("BSI-C5-2020")
    if bsi_c5: assessments["bsi_c5"] = bsi_c5
    
    bsi_isms = get_assessment("bs-it-gs-2023-isms-sicherheitsmanagement")
    if bsi_isms: assessments["bsi_isms"] = bsi_isms
    
    bsi_ops = get_assessment("bs-it-gs-2023-ops-betrieb")
    if bsi_ops: assessments["bsi_ops"] = bsi_ops
    
    bsi_net = get_assessment("bs-it-gs-2023-net-netze-und-kommunikation")
    if bsi_net: assessments["bsi_net"] = bsi_net
    
    iso27001 = get_assessment("ISO/IEC 27001:2022")
    if iso27001: assessments["iso27001"] = iso27001
    
    gdpr_checklist = get_assessment("GDPR-checklist")
    if gdpr_checklist: assessments["gdpr_checklist"] = gdpr_checklist
    
    gdpr_full = get_assessment("GDPR")
    if gdpr_full: assessments["gdpr_full"] = gdpr_full

    # AI specific assessments
    eu_ai_act = get_assessment("AI Act")
    if eu_ai_act: assessments["eu_ai_act"] = eu_ai_act

    nist_ai_rmf = get_assessment("NIST-AI-RMF-1.0")
    if nist_ai_rmf: assessments["nist_ai_rmf"] = nist_ai_rmf

    owasp_llm = get_assessment("owasp-llm-checklist")
    if owasp_llm: assessments["owasp_llm"] = owasp_llm

    for k, v in assessments.items():
        print(f"  [+] Resolved {k}: UUID={v.id}")

    # 6. Configure Dashboards
    dashboards_config = [
        # Dashboard 1: DORA
        {
            "ref_id": "seed:dora-compliance-dashboard",
            "name": "DORA Compliance Dashboard",
            "description": "Zentrales Dashboard für IKT-Drittparteienrisiko, Exit-Planungen und Betriebskontinuität gemäß DORA.",
            "widgets": [
                {
                    "title": "DORA Critical Services",
                    "metric_instance": metric_instances["MET-DORA-CRITICAL-SERVICES"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Exit Plan Coverage",
                    "metric_instance": metric_instances["MET-DORA-EXIT-PLAN-COVERAGE"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 3, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "DORA Contract Compliance",
                    "metric_instance": metric_instances["MET-DORA-CONTRACT-COMPLIANCE"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 6, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Vendor Assessments Completed",
                    "metric_instance": metric_instances["MET-DORA-VENDOR-ASSESSMENTS"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 9, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Incident Notification SLA",
                    "metric_instance": metric_instances["MET-DORA-INCIDENT-SLA"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 1, "width": 4, "height": 1
                },
                *( [{
                    "title": "DORA Audit Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["dora_assess"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 4, "position_y": 1, "width": 8, "height": 2
                },
                {
                    "title": "DORA Compliance Results",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["dora_assess"].id,
                    "metric_key": "result_breakdown",
                    "chart_type": DashboardWidget.ChartType.DONUT,
                    "position_x": 0, "position_y": 3, "width": 6, "height": 3
                },
                {
                    "title": "DORA Requirement Status",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["dora_assess"].id,
                    "metric_key": "status_breakdown",
                    "chart_type": DashboardWidget.ChartType.DONUT,
                    "position_x": 6, "position_y": 3, "width": 6, "height": 3
                }] if "dora_assess" in assessments else [] )
            ]
        },
        # Dashboard 2: NIS 2
        {
            "ref_id": "seed:nis2-compliance-dashboard",
            "name": "NIS 2 Security Dashboard",
            "description": "Zentrales Dashboard für technische Sicherheitsmaßnahmen, Vorfallsbehebung und Cybersicherheitshygiene gemäß NIS 2.",
            "widgets": [
                {
                    "title": "NIS2 MFA Rate",
                    "metric_instance": metric_instances["MET-NIS2-MFA-RATE"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Incident Mitigation Time",
                    "metric_instance": metric_instances["MET-NIS2-IR-TIME"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 3, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Security Awareness Training",
                    "metric_instance": metric_instances["MET-NIS2-AWARENESS-TRAINING"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 6, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Vulnerability Remediation SLA",
                    "metric_instance": metric_instances["MET-NIS2-VULN-SLA"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 9, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Backup Test Frequency",
                    "metric_instance": metric_instances["MET-NIS2-BACKUP-TEST"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 1, "width": 4, "height": 1
                },
                *( [{
                    "title": "NIS 2 Audit Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["nis2_assess"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 4, "position_y": 1, "width": 8, "height": 2
                },
                {
                    "title": "NIS 2 Requirement Status",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["nis2_assess"].id,
                    "metric_key": "status_breakdown",
                    "chart_type": DashboardWidget.ChartType.DONUT,
                    "position_x": 0, "position_y": 3, "width": 12, "height": 3
                }] if "nis2_assess" in assessments else [] )
            ]
        },
        # Dashboard 3: M365 Security
        {
            "ref_id": "seed:m365-security-dashboard",
            "name": "M365 Security & Governance Dashboard",
            "description": "Technisches Dashboard für Microsoft 365 Tenant-Sicherheitskontrollen, Identitätsgovernance und DLP.",
            "widgets": [
                {
                    "title": "Microsoft Secure Score",
                    "metric_instance": metric_instances["MET-MS-SECURE-SCORE"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Config Drifts",
                    "metric_instance": metric_instances["MET-MS-CONFIG-DRIFTS"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 3, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Legacy Auth Blocked",
                    "metric_instance": metric_instances["MET-LEGACY-AUTH-DISABLEMENT"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 6, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "Admin MFA Rate",
                    "metric_instance": metric_instances["MET-MFA-ADMINS-ENABLEMENT"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 9, "position_y": 0, "width": 3, "height": 1
                },
                {
                    "title": "GDAP Partner Health",
                    "metric_instance": metric_instances["MET-GDAP-RELATIONSHIP-HEALTH"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 1, "width": 3, "height": 1
                },
                {
                    "title": "Break-Glass Status",
                    "metric_instance": metric_instances["MET-BREAK-GLASS-STATUS"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 3, "position_y": 1, "width": 3, "height": 1
                },
                {
                    "title": "DLP Policy Matches",
                    "metric_instance": metric_instances["MET-DLP-POLICY-MATCHES"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 6, "position_y": 1, "width": 3, "height": 1
                },
                {
                    "title": "Phishing Fail Rate",
                    "metric_instance": metric_instances["MET-PHISHING-FAIL-RATE"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 9, "position_y": 1, "width": 3, "height": 1
                },
                *( [{
                    "title": "M365-Assess Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["m365_assess"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 0, "position_y": 2, "width": 12, "height": 2
                },
                {
                    "title": "M365-Assess Requirements Status",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["m365_assess"].id,
                    "metric_key": "status_breakdown",
                    "chart_type": DashboardWidget.ChartType.DONUT,
                    "position_x": 0, "position_y": 4, "width": 12, "height": 3
                }] if "m365_assess" in assessments else [] )
            ]
        },
        # Dashboard 4: BSI IT-Grundschutz & C5
        {
            "ref_id": "seed:bsi-compliance-dashboard",
            "name": "BSI IT-Grundschutz & C5 Dashboard",
            "description": "Zentrales Dashboard für Konformitätsberichte nach BSI C5 und Umsetzungsgrade des IT-Grundschutz-Kompendiums.",
            "widgets": [
                {
                    "title": "BSI Grundschutz Implementation",
                    "metric_instance": metric_instances["MET-BSI-GS-IMPLEMENTATION"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 0, "width": 4, "height": 1
                },
                {
                    "title": "BSI C5 Cloud Attestation",
                    "metric_instance": metric_instances["MET-BSI-C5-STATUS"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 4, "position_y": 0, "width": 4, "height": 1
                },
                {
                    "title": "ISB Audit Cadence",
                    "metric_instance": metric_instances["MET-BSI-AUDIT-CADENCE"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 8, "position_y": 0, "width": 4, "height": 1
                },
                *( [{
                    "title": "BSI C5 Audit Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["bsi_c5"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 0, "position_y": 1, "width": 6, "height": 2
                }] if "bsi_c5" in assessments else [] ),
                *( [{
                    "title": "BSI IT-Grundschutz ISMS Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["bsi_isms"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 6, "position_y": 1, "width": 6, "height": 2
                }] if "bsi_isms" in assessments else [] ),
                *( [{
                    "title": "BSI IT-Grundschutz Ops Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["bsi_ops"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 0, "position_y": 3, "width": 6, "height": 2
                }] if "bsi_ops" in assessments else [] ),
                *( [{
                    "title": "BSI IT-Grundschutz Net Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["bsi_net"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 6, "position_y": 3, "width": 6, "height": 2
                }] if "bsi_net" in assessments else [] )
            ]
        },
        # Dashboard 5: ISO/IEC 27001
        {
            "ref_id": "seed:iso27001-compliance-dashboard",
            "name": "ISO/IEC 27001 ISMS Dashboard",
            "description": "Zentrales Dashboard für Wirksamkeitsbewertungen der ISO 27001 Annex A Sicherheitskontrollen und Audit-Abweichungen.",
            "widgets": [
                {
                    "title": "Annex A Control Effectiveness",
                    "metric_instance": metric_instances["MET-ISO-CONTROL-EFFECTIVENESS"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 0, "width": 4, "height": 1
                },
                {
                    "title": "Active Exceptions",
                    "metric_instance": metric_instances["MET-ISO-SECURITY-EXCEPTIONS"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 4, "position_y": 0, "width": 4, "height": 1
                },
                {
                    "title": "Audit Remediation SLA",
                    "metric_instance": metric_instances["MET-ISO-INTERNAL-AUDIT-SLA"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 8, "position_y": 0, "width": 4, "height": 1
                },
                *( [{
                    "title": "ISO 27001 Audit Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["iso27001"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 0, "position_y": 1, "width": 12, "height": 2
                },
                {
                    "title": "ISO 27001 Status Breakdown",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["iso27001"].id,
                    "metric_key": "status_breakdown",
                    "chart_type": DashboardWidget.ChartType.DONUT,
                    "position_x": 0, "position_y": 3, "width": 12, "height": 3
                }] if "iso27001" in assessments else [] )
            ]
        },
        # Dashboard 6: GDPR & Data Privacy
        {
            "ref_id": "seed:gdpr-privacy-dashboard",
            "name": "GDPR & Data Privacy Dashboard",
            "description": "Zentrales Dashboard für DSGVO-Betroffenenrechte, DSFA-Bewertungen und Datenschutz-Unterweisungen.",
            "widgets": [
                {
                    "title": "DPIA Coverage",
                    "metric_instance": metric_instances["MET-GDPR-DPIA-COVERAGE"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 0, "width": 4, "height": 1
                },
                {
                    "title": "SAR SLA Adherence",
                    "metric_instance": metric_instances["MET-GDPR-SAR-SLA"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 4, "position_y": 0, "width": 4, "height": 1
                },
                {
                    "title": "Staff Training Rate",
                    "metric_instance": metric_instances["MET-GDPR-TRAINING-RATE"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 8, "position_y": 0, "width": 4, "height": 1
                },
                *( [{
                    "title": "GDPR Checklist Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["gdpr_checklist"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 0, "position_y": 1, "width": 6, "height": 2
                }] if "gdpr_checklist" in assessments else [] ),
                *( [{
                    "title": "GDPR Framework Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["gdpr_full"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 6, "position_y": 1, "width": 6, "height": 2
                }] if "gdpr_full" in assessments else [] ),
                *( [{
                    "title": "GDPR Status Breakdown",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["gdpr_full"].id,
                    "metric_key": "status_breakdown",
                    "chart_type": DashboardWidget.ChartType.DONUT,
                    "position_x": 0, "position_y": 3, "width": 12, "height": 3
                }] if "gdpr_full" in assessments else [] )
            ]
        },
        # Dashboard 7: EU AI Act & AI Governance
        {
            "ref_id": "seed:ai-compliance-dashboard",
            "name": "EU AI Act & AI Governance Dashboard",
            "description": "Zentrales Dashboard zur Überwachung von KI-Risikoklassifizierungen, Konformitätsbewertungen und Sicherheitsrichtlinien unter dem EU AI Act.",
            "widgets": [
                {
                    "title": "AI Model Classification",
                    "metric_instance": metric_instances["MET-AI-SYSTEM-INVENTORY"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 0, "position_y": 0, "width": 4, "height": 1
                },
                {
                    "title": "AI Conformity Assessments",
                    "metric_instance": metric_instances["MET-AI-RISK-ASSESSMENTS"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 4, "position_y": 0, "width": 4, "height": 1
                },
                {
                    "title": "AI Security Violations",
                    "metric_instance": metric_instances["MET-AI-SECURITY-MATCHES"],
                    "chart_type": DashboardWidget.ChartType.KPI_CARD,
                    "position_x": 8, "position_y": 0, "width": 4, "height": 1
                },
                *( [{
                    "title": "EU AI Act Audit Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["eu_ai_act"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 0, "position_y": 1, "width": 4, "height": 2
                }] if "eu_ai_act" in assessments else [] ),
                *( [{
                    "title": "NIST AI RMF Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["nist_ai_rmf"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 4, "position_y": 1, "width": 4, "height": 2
                }] if "nist_ai_rmf" in assessments else [] ),
                *( [{
                    "title": "OWASP LLM Checklist Progress",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["owasp_llm"].id,
                    "metric_key": "progress",
                    "chart_type": DashboardWidget.ChartType.GAUGE,
                    "position_x": 8, "position_y": 1, "width": 4, "height": 2
                }] if "owasp_llm" in assessments else [] ),
                *( [{
                    "title": "EU AI Act Status Breakdown",
                    "target_content_type": ContentType.objects.get_for_model(ComplianceAssessment),
                    "target_object_id": assessments["eu_ai_act"].id,
                    "metric_key": "status_breakdown",
                    "chart_type": DashboardWidget.ChartType.DONUT,
                    "position_x": 0, "position_y": 3, "width": 12, "height": 3
                }] if "eu_ai_act" in assessments else [] )
            ]
        }
    ]

    for db_cfg in dashboards_config:
        dashboard, db_created = Dashboard.objects.get_or_create(
            ref_id=db_cfg["ref_id"],
            defaults={
                "folder": root_folder,
                "name": db_cfg["name"],
                "description": db_cfg["description"],
                "dashboard_definition": {
                    "layout": {"columns": 12, "row_height": 100},
                    "global_filters": {"time_range": "last_30_days", "refresh_interval": 300}
                }
            }
        )
        if db_created:
            print(f"[+] Created Dashboard: {dashboard.name}")
        else:
            dashboard.name = db_cfg["name"]
            dashboard.description = db_cfg["description"]
            dashboard.save()
            print(f"[+] Updated Dashboard: {dashboard.name}")

        # Rebuild widgets
        dashboard.widgets.all().delete()
        for w in db_cfg["widgets"]:
            widget = DashboardWidget(
                dashboard=dashboard,
                folder=root_folder,
                title=w["title"],
                chart_type=w["chart_type"],
                position_x=w["position_x"],
                position_y=w["position_y"],
                width=w["width"],
                height=w["height"],
                metric_instance=w.get("metric_instance"),
                target_content_type=w.get("target_content_type"),
                target_object_id=w.get("target_object_id"),
                metric_key=w.get("metric_key"),
                show_target=True,
                show_legend=True
            )
            widget.full_clean()
            widget.save()
            print(f"  [+] Added Widget: '{w['title']}' to Dashboard '{dashboard.name}'")

    print("[+] Successfully configured all 7 specific GRC Dashboards!")

if __name__ == "__main__":
    main()
