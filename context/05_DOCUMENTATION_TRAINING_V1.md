# FILE 5: TRAINING DATASET - DOCUMENTATION AGENT EXAMPLES (V1 UPDATE)
**Version:** 1.0.1 (V1 Aligned)  
**Date:** January 19, 2026  
**Status:** Data Resource Curated + Documentation Examples  
**Update Type:** Additive (new section for DOCUMENTATION examples)

---

## NEW SECTION: DOCUMENTATION AGENT TRAINING DATA (V1)

### Overview

DOCUMENTATION Agent (Phi-3.5-mini 3.8B Q6_K) needs training data to:
1. Convert RED Agent vulnerability findings → human-readable descriptions
2. Generate structured Google Docs reports
3. Format compliance mappings
4. Prioritize vulnerabilities by risk

**Training Data Size:** 1-2GB  
**Format:** Q&A pairs (vulnerability input → report section output)  
**Fine-tuning approach:** QLoRA (parameter-efficient)

---

## Dataset 1: Vulnerability Description Translation

**Size:** 500MB  
**Source:** NVD CVE descriptions, HackerOne reports, real security findings  
**Format:** JSON Q&A pairs

**Download:**
```bash
cd /data/documentation_agent_training

# Download real CVE descriptions from NVD
mkdir -p nvd_descriptions
for year in {2023..2026}; do
  curl -O https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-${year}.json.gz
  gunzip nvdcve-1.1-${year}.json.gz
done

# Convert to training format
python scripts/convert_nvd_to_doc_training.py \
  --input nvd/ \
  --output training_data/vulnerability_descriptions.jsonl
```

**Training Format:**

```json
{
  "instruction": "Convert this technical vulnerability finding into an executive summary",
  "input": {
    "vulnerability_type": "SQL Injection",
    "location": {
      "file": "src/api/users.py",
      "line": 42,
      "function": "get_user_by_id"
    },
    "cwe": "CWE-89",
    "cvss": 8.5,
    "poc_code": "GET /api/user?id=1' OR '1'='1'"
  },
  "output": {
    "executive_summary": "SQL injection vulnerability in user lookup endpoint allows unauthenticated attackers to bypass authentication and retrieve entire user database.",
    "technical_description": "The application constructs SQL queries by directly concatenating user-supplied input without parameterization or validation. An attacker can inject SQL syntax to alter query logic.",
    "attack_vector": "Network (CVSS vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)",
    "business_impact": "Complete data breach: attacker can steal user PII, passwords, financial data, leading to regulatory violations (GDPR, HIPAA, PCI-DSS)",
    "immediate_action": "Urgently patch using parameterized queries or ORM"
  }
}
```

### Dataset 2: Report Structure Generation

**Size:** 300MB  
**Source:** Real security audit reports, OWASP templates  
**Format:** Section templates + vulnerability data → complete section

**Source:** Manually curated security report examples

```bash
# Manual collection
mkdir -p /data/documentation_agent_training/report_templates

# Create example reports
# report_templates/executive_summary_example.md
# report_templates/vulnerability_details_example.md
# report_templates/remediation_plan_example.md
# report_templates/compliance_impact_example.md

python scripts/extract_report_sections.py \
  --input report_templates/ \
  --output training_data/report_sections.jsonl
```

**Training Format:**

```json
{
  "instruction": "Generate Executive Summary section for security report",
  "input": {
    "repository": "github.com/company/app",
    "branch": "main",
    "scan_date": "2026-01-19",
    "scan_duration_seconds": 175,
    "vulnerabilities_found": 12,
    "by_severity": {
      "critical": 3,
      "high": 5,
      "medium": 4,
      "low": 0
    },
    "overall_risk_score": 72
  },
  "output": {
    "section_title": "Executive Summary",
    "content": "## Executive Summary\n\n**Repository:** github.com/company/app  \n**Branch:** main  \n**Scan Date:** January 19, 2026  \n**Scan Duration:** 175 seconds  \n\n### Vulnerability Summary\n\n**Total Vulnerabilities Found: 12**\n\n- 🔴 **Critical:** 3 vulnerabilities\n- 🟠 **High:** 5 vulnerabilities\n- 🟡 **Medium:** 4 vulnerabilities\n- 🔵 **Low:** 0 vulnerabilities\n\n### Risk Assessment\n\n**Overall Risk Score:** 72/100 (HIGH RISK)\n\n**Key Findings:**\n1. **SQL Injection in /api/user** (CVSS 8.5) - Allows unauthenticated database access\n2. **RCE via file upload** (CVSS 9.1) - Arbitrary code execution possible\n3. **Authentication bypass** (CVSS 7.8) - Session validation missing\n\n### Compliance Impact\n\nThese vulnerabilities put the following frameworks AT RISK if not remediated within 7 days:\n- SOC2 (CC6.1, CC7.2)\n- PCI-DSS (6.5.1)\n- GDPR (Article 32)\n\n### Next Steps\n\nImmediately review the Remediation Plan section for prioritized fix recommendations."
  }
}
```

### Dataset 3: Compliance Framework Mapping

**Size:** 200MB  
**Source:** SOC2, ISO27001, GDPR, HIPAA, PCI-DSS documentation  
**Format:** Vulnerability → framework control mapping

**Download & Process:**
```bash
cd /data/documentation_agent_training/compliance

# SOC2 Trust Service Criteria
curl -O https://www.aicpa.org/soc2-downloads
# ISO27001 Control Objectives
curl -O https://www.iso.org/iso-iec-27001-information-security-management.html
# GDPR Articles
curl -O https://gdpr-info.eu/

python scripts/convert_compliance_mappings_to_doc_training.py \
  --input compliance/ \
  --output training_data/compliance_mappings_doc.jsonl
```

**Training Format:**

```json
{
  "instruction": "Map this vulnerability to compliance frameworks and explain impact",
  "input": {
    "vulnerability_type": "SQL Injection",
    "cwe": "CWE-89",
    "cvss": 8.5,
    "severity": "critical",
    "affected_data": "user_passwords, credit_cards, pii"
  },
  "output": {
    "compliance_mappings": {
      "SOC2": [
        {
          "criterion": "CC6.1",
          "name": "Logical and Physical Access Controls",
          "description": "Unauthorized access to database via SQL injection violates access control requirements",
          "impact": "CRITICAL - Access controls failed"
        },
        {
          "criterion": "CC7.2",
          "name": "System Monitoring",
          "description": "Injection attack allows undetected unauthorized queries",
          "impact": "HIGH - Logging bypassed"
        }
      ],
      "ISO27001": [
        {
          "control": "12.2.1",
          "name": "User Access Management",
          "description": "SQL injection allows unauthorized access to restricted database",
          "impact": "CRITICAL"
        },
        {
          "control": "14.2.5",
          "name": "Secure Development",
          "description": "Code lacks input validation",
          "impact": "HIGH"
        }
      ],
      "GDPR": [
        {
          "article": "Article 32",
          "name": "Security of Processing",
          "requirement": "Technical and organizational measures to ensure personal data security",
          "impact": "CRITICAL - Personal data (passwords, PII) at risk of disclosure",
          "fine_potential": "€20 million or 4% annual revenue (whichever higher)"
        },
        {
          "article": "Article 33",
          "name": "Notification of a Personal Data Breach",
          "requirement": "Must notify supervisory authority within 72 hours if breach occurs",
          "impact": "HIGH - Breach notification required if exploited"
        }
      ],
      "PCI-DSS": [
        {
          "requirement": "6.5.1",
          "name": "Injection Flaws Prevention",
          "requirement_text": "Protect against injection flaws",
          "impact": "CRITICAL - Direct violation"
        },
        {
          "requirement": "6.2",
          "name": "Ensure Security Patches Installed",
          "requirement_text": "Implement application security patches promptly",
          "impact": "HIGH - Patch needed immediately"
        }
      ]
    },
    "risk_summary": "CRITICAL COMPLIANCE RISK: This vulnerability violates multiple compliance frameworks. If exploited, the organization would be non-compliant with SOC2, ISO27001, GDPR, and PCI-DSS. Potential fines up to €20M under GDPR alone.",
    "urgency": "PATCH IMMEDIATELY"
  }
}
```

### Dataset 4: Remediation Plan Prioritization

**Size:** 200MB  
**Source:** Real fix histories, developer experience data  
**Format:** Vulnerability + fix options → prioritized remediation plan

**Training Format:**

```json
{
  "instruction": "Generate prioritized remediation plan from vulnerability and fix data",
  "input": {
    "vulnerabilities": [
      {
        "id": "RED-001",
        "type": "SQL Injection",
        "cvss": 8.5,
        "severity": "critical",
        "location": {"file": "api.py", "line": 42},
        "estimated_fix_time_minutes": 15
      },
      {
        "id": "RED-002",
        "type": "RCE via file upload",
        "cvss": 9.1,
        "severity": "critical",
        "location": {"file": "upload.py", "line": 28},
        "estimated_fix_time_minutes": 25
      },
      {
        "id": "RED-003",
        "type": "XSS in search",
        "cvss": 7.5,
        "severity": "high",
        "location": {"file": "search.html", "line": 156},
        "estimated_fix_time_minutes": 10
      }
    ],
    "team_capacity": {
      "available_engineers": 2,
      "total_capacity_minutes": 240
    }
  },
  "output": {
    "remediation_plan": "# Remediation Plan (Prioritized by Risk)\n\n**Total Estimated Time:** 50 minutes (fits in team capacity)\n**Recommended Timeline:** Fix all vulnerabilities within 4 hours\n\n## Phase 1: CRITICAL vulnerabilities (0-30 minutes)\n\n### 1. RCE via file upload (CVSS 9.1) - HIGHEST PRIORITY\n- **Impact:** Remote code execution - attacker gains full system access\n- **File:** upload.py, line 28\n- **Recommended Fix:** Validate file type, store outside webroot, use signed URLs\n- **Estimated Time:** 25 minutes\n- **Developer:** Assign to Senior Engineer (high complexity)\n- **Merge Target:** emergency-fix branch → main (expedited review)\n- **Testing Required:** Upload shell.php, verify execution fails\n\n### 2. SQL Injection in /api/user (CVSS 8.5) - SECOND PRIORITY\n- **Impact:** Complete database breach - access to user data\n- **File:** api.py, line 42\n- **Recommended Fix:** Use parameterized queries (Django ORM)\n- **Estimated Time:** 15 minutes\n- **Developer:** Assign to any Engineer (low complexity)\n- **Merge Target:** main (normal PR review)\n- **Testing Required:** Test with malicious input: id=1' OR '1'='1'\n\n## Phase 2: HIGH severity vulnerabilities (30-50 minutes)\n\n### 3. XSS in search (CVSS 7.5) - THIRD PRIORITY\n- **Impact:** Stored XSS - attacker can steal user sessions\n- **File:** search.html, line 156\n- **Recommended Fix:** Escape HTML output using markupsafe\n- **Estimated Time:** 10 minutes\n- **Developer:** Assign to Junior Engineer (practice opportunity)\n- **Merge Target:** main\n- **Testing Required:** Search for `<script>alert('xss')</script>`, verify rendered as text\n\n## Rollout Strategy\n\n1. **Immediate:** Deploy RCE and SQL injection fixes to production\n2. **Within 1 hour:** Deploy XSS fix\n3. **Follow-up:** Run full security scan to verify all vulnerabilities closed",
    "risk_reduction": {
      "before_fixes": 72,  // Risk score /100
      "after_fixes": 15,   // Risk score after all remediated
      "improvement_percent": 79
    }
  }
}
```

### Dataset 5: Real Google Docs Report Examples (V1)

**Size:** 100MB  
**Source:** Exported from real Ouroboros scans (sanitized)  
**Format:** Complete report content → document formatting

**Collection Process:**

```bash
# After each test scan, export report as markdown
# Store in sanitized form (remove actual repo names, internal IPs)

cd /data/documentation_agent_training/real_reports

# Example sanitized report
cat > report_example_1.md << 'EOF'
# Ouroboros Security Report - [COMPANY-APP] - January 19, 2026

## Executive Summary

**Repository:** github.com/company/application  
**Branch:** main  
**Scan Date:** January 19, 2026  
**Scan Duration:** 175 seconds

### Vulnerability Summary

- **Total Vulnerabilities:** 12
- 🔴 **Critical:** 3
- 🟠 **High:** 5
- 🟡 **Medium:** 4
- 🔵 **Low:** 0

**Overall Risk Score:** 72/100

...rest of report...
EOF

# Convert to training data
python scripts/convert_real_reports_to_training.py \
  --input real_reports/ \
  --output training_data/real_report_examples.jsonl
```

**Training Format:**

```json
{
  "instruction": "Format this report data into a professional Google Docs security report",
  "input": {
    "scan_metadata": {
      "repo": "company/application",
      "branch": "main",
      "date": "2026-01-19",
      "duration_seconds": 175
    },
    "raw_findings": [
      {
        "id": "RED-001",
        "type": "SQL Injection",
        "file": "api.py",
        "line": 42,
        "cvss": 8.5
      },
      ...
    ]
  },
  "output": {
    "formatted_report": "# Ouroboros Security Report - [Company App] - January 19, 2026\n\n[Complete formatted report with all sections, proper markdown, compliance mappings, etc.]\n\n**Key Features:**\n- Executive summary with statistics\n- Detailed vulnerability descriptions\n- Remediation plan with prioritization\n- Compliance framework mappings\n- Google Docs formatting applied\n- Real-time updateable structure"
  }
}
```

---

## Data Preparation for DOCUMENTATION Agent

### Step 1: Download All DOCUMENTATION Training Data

```bash
#!/bin/bash
# download_doc_training_data.sh

BASE_DIR="/data/documentation_agent_training"
mkdir -p $BASE_DIR

echo "Downloading DOCUMENTATION Agent training data..."

# Dataset 1: Vulnerability descriptions (500MB)
cd $BASE_DIR/nvd_descriptions
for year in {2023..2026}; do
  curl -O https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-${year}.json.gz
  gunzip nvdcve-1.1-${year}.json.gz
done

# Dataset 2: Report templates (300MB)
cd $BASE_DIR/report_templates
git clone https://github.com/OWASP/www-project-testing-guide.git

# Dataset 3: Compliance docs (200MB)
cd $BASE_DIR/compliance
# Manual downloads from sources listed above

# Dataset 4: Real reports (sanitized, 200MB)
cd $BASE_DIR/real_reports
# Export from internal scans

echo "All DOCUMENTATION training data downloaded!"
du -sh $BASE_DIR/
```

### Step 2: Convert to Training Format

```python
# convert_documentation_training.py
import json
from pathlib import Path

def convert_all_doc_datasets():
    datasets = {
        'nvd': convert_nvd_to_doc_training(),
        'reports': convert_report_templates(),
        'compliance': convert_compliance_mappings(),
        'remediation': convert_remediation_plans(),
        'real_examples': convert_real_reports()
    }
    
    # Combine into single training file
    with open('documentation_agent_training.jsonl', 'w') as f:
        for dataset in datasets.values():
            for example in dataset:
                f.write(json.dumps(example) + '\n')
    
    print(f"Created documentation_agent_training.jsonl")
    print(f"Total examples: {sum(len(d) for d in datasets.values())}")
```

### Step 3: Fine-tune DOCUMENTATION Agent

```bash
# Fine-tune Phi-3.5 on documentation examples
python -m llama_cpp_python.server \
  --model /models/phi-3.5-mini-instruct-q6_k.gguf \
  --lora /models/documentation_agent_lora.bin \
  --load-in-8bit \
  --max-tokens 2048 \
  --temperature 0.15 \
  --port 8000

# Or using HuggingFace trainer
python finetune_documentation_agent.py \
  --base_model microsoft/Phi-3.5-mini-instruct \
  --train_data documentation_agent_training.jsonl \
  --output_dir /models/documentation_agent_finetuned \
  --num_epochs 3 \
  --batch_size 8 \
  --lr 2e-4
```

---

## Summary: DOCUMENTATION Agent Training (V1)

| Dataset | Size | Source | Examples |
|---------|------|--------|----------|
| 1. Vulnerability Descriptions | 500MB | NVD CVEs | 10,000+ |
| 2. Report Sections | 300MB | OWASP templates | 5,000+ |
| 3. Compliance Mappings | 200MB | Framework docs | 3,000+ |
| 4. Remediation Plans | 200MB | Developer data | 2,000+ |
| 5. Real Report Examples | 100MB | Sanitized scans | 500+ |
| **TOTAL** | **1.3GB** | Mixed | **20,500+** |

**Model:** Phi-3.5-mini 3.8B Q6_K  
**Fine-tuning:** QLoRA (4-bit)  
**Total training time:** ~2.5 hours on RTX 4090  

---

**End of File 5 Update: Training Dataset Resources**

