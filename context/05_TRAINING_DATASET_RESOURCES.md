# OUROBOROS AI: 10-20GB TRAINING DATASET GUIDE
**Version:** 1.0  
**Date:** January 17, 2026  
**Status:** Data Resource Curated  
**Total Pages:** 11+

---

## CRITICAL PREAMBLE

**These datasets are for fine-tuning quantized models (Q4_K_M, Q6_K) to specialize in security:**

- RED Agent (WhiteRabbitNeo 7B): Vulnerability detection patterns
- BLUE Agent (Qwen Coder 7B): Secure code fix generation
- GOVERNANCE Agent (Llama 3.2 3B): Policy evaluation
- AUDIT Agent (Qwen 2.5 3B): Compliance logging

**Total combined**: 15-20GB (compressed, 50-60GB uncompressed)  
**Fine-tuning approach**: QLoRA (parameter-efficient, fit on single GPU)

---

## TABLE OF CONTENTS
1. [RED Agent Training Data](#red-agent-training-data)
2. [BLUE Agent Training Data](#blue-agent-training-data)
3. [GOVERNANCE Agent Training Data](#governance-agent-training-data)
4. [AUDIT Agent Training Data](#audit-agent-training-data)
5. [Data Preparation Pipeline](#data-preparation-pipeline)
6. [Fine-Tuning Instructions](#fine-tuning-instructions)

---

## RED AGENT TRAINING DATA

### Dataset 1: Nuclei Templates (Vulnerability Patterns)
**Size**: 1-2GB  
**Source**: https://github.com/projectdiscovery/nuclei-templates  
**Format**: YAML templates + JSON metadata  
**Count**: 6,000+ templates

```bash
# Download
cd /data/red_agent_training
git clone https://github.com/projectdiscovery/nuclei-templates.git
du -sh nuclei-templates/  # ~500MB

# Convert YAML to training format
python scripts/convert_nuclei_to_training.py \
  --input nuclei-templates/ \
  --output training_data/nuclei_patterns.jsonl
```

**Training format**:
```json
{
  "instruction": "Analyze this HTTP request for SQL injection vulnerabilities",
  "input": "GET /api/user?id=1' OR '1'='1' HTTP/1.1",
  "output": {
    "vulnerability_type": "sql_injection",
    "cwe": "CWE-89",
    "cvss": 8.5,
    "poc_code": "curl 'http://target/api/user?id=1%27%20OR%20%271%27=%271%27'",
    "confidence": 0.95
  }
}
```

### Dataset 2: OWASP Top 10 CVE Descriptions
**Size**: 2-3GB  
**Source**: https://nvd.nist.gov/vuln/full-listing  
**Format**: JSON CVE records  
**Count**: 50,000+ CVEs (1998-2026)

```bash
# Download NVD data
mkdir -p /data/red_agent_training/nvd
cd /data/red_agent_training/nvd

# Monthly JSON feeds
for year in {2020..2026}; do
  for month in {01..12}; do
    curl -O https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-${year}.json.gz
  done
done

# Extract (~8GB uncompressed)
gunzip *.gz

# Convert to training format
python scripts/convert_nvd_to_training.py \
  --input nvd/ \
  --output training_data/nvd_cves.jsonl
```

**Training format**:
```json
{
  "instruction": "Generate a vulnerability report for this CVE",
  "input": {
    "cve_id": "CVE-2023-12345",
    "description": "SQL injection in database query handler",
    "affected_versions": ["< 3.5.2"]
  },
  "output": {
    "type": "sql_injection",
    "severity": "high",
    "cvss": 8.2,
    "remediation": "Update to version 3.5.2 or later"
  }
}
```

### Dataset 3: CodeQL Query Samples
**Size**: 500MB-1GB  
**Source**: https://github.com/github/codeql  
**Format**: CodeQL queries + results  
**Count**: 1,000+ queries

```bash
# Clone CodeQL repo
cd /data/red_agent_training
git clone https://github.com/github/codeql.git
du -sh codeql/  # ~200MB

# Extract query examples
python scripts/extract_codeql_queries.py \
  --input codeql/ \
  --output training_data/codeql_patterns.jsonl
```

### Dataset 4: Real Vulnerability Reports (Bug Bounty Programs)
**Size**: 2-3GB  
**Source**: HackerOne, Bugcrowd, Intigriti (public disclosures)  
**Format**: JSON reports  
**Count**: 10,000+ real-world vulnerabilities

```bash
# Download from public archives
# HackerOne: https://www.hackerone.com/researchers/reports
# Bugcrowd: https://www.bugcrowd.com/bug-bounty-programs/
# Intigriti: https://intigriti.com/public/discover

# Parse and convert
python scripts/convert_bounty_to_training.py \
  --input bounty_reports/ \
  --output training_data/bounty_samples.jsonl
```

**Training format**:
```json
{
  "instruction": "Classify and analyze this vulnerability report",
  "input": {
    "title": "Unauthenticated RCE in admin panel",
    "description": "Due to missing authentication checks...",
    "affected_component": "admin/upload.php",
    "attack_vector": "network"
  },
  "output": {
    "type": "rce",
    "cwe": "CWE-78",
    "cvss": 9.8,
    "attack_vector": "network",
    "poc_steps": ["1. Navigate to /admin/upload.php", "2. Upload shell.php"]
  }
}
```

### Dataset 5: CWE/CVSS Classification Corpus
**Size**: 1GB  
**Source**: https://cwe.mitre.org/, https://www.first.org/cvss/  
**Format**: Structured classification data  
**Count**: 1,000+ CWE mappings × 10,000+ examples

```bash
# CWE mappings
curl -O https://cwe.mitre.org/data/definitions/1000.json.zip
unzip 1000.json.zip
python scripts/convert_cwe_to_training.py --output training_data/cwe_mappings.jsonl

# CVSS calculations
# Manual generation of CVSS score prediction training
python scripts/generate_cvss_training.py \
  --metrics "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H" \
  --output training_data/cvss_scoring.jsonl
```

---

## BLUE AGENT TRAINING DATA

### Dataset 1: Secure Code Examples (CWE Remediation)
**Size**: 3-4GB  
**Source**: https://cwe.mitre.org/documents/, OWASP Secure Coding Practices  
**Format**: Before/after code snippets  
**Count**: 5,000+ remediation examples

```bash
cd /data/blue_agent_training

# Manual collection (these are the gold standard)
# - Each CWE should have 5-10 examples of vulnerable + fixed code
# - Multiple programming languages (Python, JavaScript, Go, Java)

mkdir -p datasets/{python,javascript,go,java}

# Example structure:
# datasets/python/cwe-89-sql-injection/
#   ├─ vulnerable.py
#   ├─ fixed.py
#   ├─ test.py
#   └─ explanation.md

# Convert to training format
python scripts/convert_code_examples_to_training.py \
  --input datasets/ \
  --output training_data/secure_code_examples.jsonl
```

**Training format**:
```json
{
  "instruction": "Fix this SQL injection vulnerability in Python",
  "input": {
    "vulnerable_code": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
    "vulnerability_type": "sql_injection",
    "cwe": "CWE-89",
    "programming_language": "python",
    "framework": "django"
  },
  "output": {
    "fixed_code": "user = User.objects.get(id=user_id)  # ORM automatically parameterizes",
    "approach": "use_orm",
    "explanation": "Use parameterized queries via ORM to prevent injection",
    "test_code": "assert User.objects.filter(id=1).exists()"
  }
}
```

### Dataset 2: GitHub Secure Code Patches
**Size**: 4-5GB  
**Source**: https://github.com/trending?since=monthly&spoken_language_code=en (security-related repos)  
**Format**: Git diffs + commit messages  
**Count**: 10,000+ real security patches

```bash
# Clone top security repositories
repos=(
  "rails/rails"
  "django/django"
  "expressjs/express"
  "gohugoio/hugo"
  "rust-lang/rust"
)

for repo in "${repos[@]}"; do
  git clone https://github.com/$repo.git /data/blue_agent_training/repos/$repo
done

# Extract security-related commits
python scripts/extract_security_patches.py \
  --input repos/ \
  --keywords "security,vulnerability,xss,injection,cve" \
  --output training_data/github_patches.jsonl
```

**Training format**:
```json
{
  "instruction": "Generate a patch for this security issue",
  "input": {
    "before_code": "user_input = request.GET['search']\nhtml = f\"<h1>Results for {user_input}</h1>\"",
    "vulnerability": "Cross-site scripting (XSS)",
    "cwe": "CWE-79",
    "affected_line": 2
  },
  "output": {
    "after_code": "user_input = request.GET['search']\nhtml = f\"<h1>Results for {escape(user_input)}</h1>\"",
    "explanation": "Escape HTML characters to prevent XSS",
    "test_cases": ["<script>alert('xss')</script>", "'; DROP TABLE users; --"],
    "test_assertions": ["Malicious script not executed", "HTML properly escaped"]
  }
}
```

### Dataset 3: OWASP Secure Coding Practices
**Size**: 1-2GB  
**Source**: https://owasp.org/www-project-secure-coding-practices/  
**Format**: Guidelines + code examples  
**Count**: 5,000+ practices

```bash
cd /data/blue_agent_training

# OWASP resources
curl -O https://owasp.org/www-community/attacks/attacks.json
curl -O https://owasp.org/www-community/vulnerabilities/vulnerabilities.json

# Convert to training
python scripts/convert_owasp_to_training.py \
  --output training_data/owasp_practices.jsonl
```

### Dataset 4: Security-Focused Stack Overflow Answers
**Size**: 2-3GB  
**Source**: Stack Overflow (security-tagged questions)  
**Format**: Q&A pairs  
**Count**: 50,000+ security questions

```bash
# Use Stack Overflow data dump
# https://archive.org/download/stackexchange
# Download stackoverflow.com-Posts.7z (~60GB, extract posts.xml)

python scripts/extract_stackoverflow_security.py \
  --input posts.xml \
  --tags "security,cryptography,authentication" \
  --min_score 10 \
  --output training_data/stackoverflow_security.jsonl
```

### Dataset 5: Test Case Generation Examples
**Size**: 1GB  
**Source**: OWASP WebGoat, HackTheBox writeups  
**Format**: Challenge + solution  
**Count**: 5,000+ test cases

```bash
# WebGoat challenges
git clone https://github.com/WebGoat/WebGoat.git /data/blue_agent_training/webgoat

python scripts/extract_test_cases.py \
  --input webgoat/ \
  --output training_data/test_cases.jsonl
```

---

## GOVERNANCE AGENT TRAINING DATA

### Dataset 1: OPA Policy Examples
**Size**: 500MB  
**Source**: https://github.com/open-policy-agent/library  
**Format**: Rego policy files  
**Count**: 1,000+ policies

```bash
cd /data/governance_agent_training

git clone https://github.com/open-policy-agent/library.git
du -sh library/  # ~100MB

# Convert policies to training format
python scripts/convert_opa_policies_to_training.py \
  --input library/ \
  --output training_data/opa_policies.jsonl
```

**Training format**:
```json
{
  "instruction": "Evaluate this fix proposal against security policies",
  "input": {
    "fix": {
      "vulnerability_cvss": 8.5,
      "fix_confidence": 0.92,
      "test_coverage": 0.85
    },
    "environment": "production",
    "previous_approvals": 2
  },
  "output": {
    "decision": "require",
    "risk_score": 45,
    "reasoning": "High CVSS + production environment requires explicit approval",
    "required_approvers": ["security_team"]
  }
}
```

### Dataset 2: Compliance Framework Mappings
**Size**: 1GB  
**Source**: SOC2, ISO27001, GDPR, HIPAA, PCI-DSS documentation  
**Format**: JSON control mappings  
**Count**: 2,000+ control-to-action mappings

```bash
# Manual curation (these must be accurate)
mkdir -p /data/governance_agent_training/compliance

# SOC2 controls
curl -O https://www.aicpa.org/soc2-downloads
# ISO27001 controls
curl -O https://www.iso.org/iso-iec-27001-information-security-management.html
# GDPR articles
curl -O https://gdpr-info.eu/

python scripts/convert_compliance_mappings.py \
  --output training_data/compliance_mappings.jsonl
```

### Dataset 3: Risk Scoring Training Data
**Size**: 500MB  
**Source**: CVSS data + historical approval decisions  
**Format**: Input features + risk score label  
**Count**: 10,000+ scoring examples

```bash
# Generate synthetic training data based on CVSS v3.1 formulas
python scripts/generate_risk_scoring_training.py \
  --num_examples 10000 \
  --output training_data/risk_scoring.jsonl \
  --include_historical_approvals
```

---

## AUDIT AGENT TRAINING DATA

### Dataset 1: Compliance Event Logs
**Size**: 1-2GB  
**Source**: Real audit logs (sanitized), OWASP Logging Project  
**Format**: Structured event JSON  
**Count**: 100,000+ events

```bash
cd /data/audit_agent_training

# OWASP Logging Project examples
git clone https://github.com/OWASP/logging-cheat-sheet.git
python scripts/convert_logging_examples_to_training.py \
  --input logging-cheat-sheet/ \
  --output training_data/audit_events.jsonl
```

**Training format**:
```json
{
  "instruction": "Normalize this security event for audit trail",
  "input": {
    "raw_event": "WARN - Red agent found sql_injection at line 42 in app.py, CVSS 8.5"
  },
  "output": {
    "event_id": "uuid",
    "timestamp": "2026-01-17T12:34:56Z",
    "event_type": "vulnerability_discovered",
    "severity": "high",
    "compliance_mappings": {
      "SOC2": ["CC6.1"],
      "ISO27001": ["12.2.1"]
    }
  }
}
```

### Dataset 2: Digital Signature Examples
**Size**: 500MB  
**Source**: Cryptography libraries, PKI samples  
**Format**: Event + signature pairs  
**Count**: 50,000+ signed events

```bash
# Generate training data with cryptographic signatures
python scripts/generate_signed_events.py \
  --num_examples 50000 \
  --output training_data/signed_events.jsonl \
  --include_verification_proofs
```

### Dataset 3: Compliance Mapping Examples
**Size**: 500MB  
**Source**: Real compliance audit mappings  
**Format**: Event + framework mapping  
**Count**: 5,000+ mapping examples

```bash
# Curate compliance mappings
python scripts/convert_compliance_mappings_for_audit.py \
  --frameworks "SOC2,ISO27001,GDPR,HIPAA,PCI-DSS" \
  --output training_data/compliance_mappings_audit.jsonl
```

---


---

## DeepSeek-R1 Training Data (BLUE Agent)

### Dataset 6: Chain-of-Thought Security Reasoning

**Size:** 500MB  
**Source:** Academic papers on vulnerability analysis, security reasoning datasets  
**Format:** Input vulnerability → Reasoning chain → Fix

**Training Format:**

```json
{
  "instruction": "Fix this SQL injection vulnerability with step-by-step reasoning",
  "input": {
    "vulnerable_code": "query = f\"SELECT * FROM users WHERE id = {user_id}\"",
    "vulnerability_type": "sql_injection",
    "cwe": "CWE-89"
  },
  "output": {
    "reasoning": {
      "step_1_analysis": "The code uses string interpolation to construct SQL query. User-controlled `user_id` is inserted directly without sanitization.",
      "step_2_attack_vector": "Attacker can inject SQL syntax: user_id='1 OR 1=1' returns all users.",
      "step_3_approaches": [
        "Approach 1: Parameterized query with placeholder",
        "Approach 2: ORM (Django/SQLAlchemy) with automatic escaping",
        "Approach 3: Input validation + whitelist"
      ],
      "step_4_trade_offs": "Parameterized queries are fastest to implement, ORM is safest long-term. Input validation alone is insufficient (bypass possible).",
      "step_5_selected": "Use parameterized query with placeholder - balance of security and simplicity"
    },
    "fixed_code": "cursor.execute(\"SELECT * FROM users WHERE id = ?\", (user_id,))",
    "test_code": "assert cursor.execute(\"...\", (\"1' OR '1'='1\",)) returns empty"
  }
}
```

**Collection:**
```bash
cd /data/blue_agent_training/reasoning

# Collect academic papers on vulnerability analysis
# - "A Survey of Software Vulnerability Discovery Techniques"
# - "Automated Vulnerability Repair"
# - Security CTF writeups with step-by-step analysis

python scripts/convert_reasoning_to_training.py \
  --input papers/ \
  --output training_data/cot_security_reasoning.jsonl
```

---

## Phi-3.5 Training Data (GOV/DOC/AUDIT Agents)

### Dataset 7: Microsoft Instruction-Following Examples

**Size:** 300MB  
**Source:** Microsoft Phi-3 fine-tuning datasets  
**Format:** Instruction → Structured output

**Why:** Phi-3.5 is pre-trained on instruction-following. Fine-tune on security-specific instructions.

**Training Format:**

```json
{
  "instruction": "Evaluate this vulnerability and assign risk score using policy",
  "input": {
    "vulnerability": {
      "cvss": 8.5,
      "environment": "production",
      "exploit_ease": 0.9
    },
    "policy": {
      "critical_threshold": 8.0,
      "production_multiplier": 5.0
    }
  },
  "output": {
    "risk_score": 38.25,  // 8.5 * 0.9 * 5.0
    "autonomy_level": "require",
    "reasoning": "CVSS 8.5 exceeds critical threshold + production environment = high risk"
  }
}
```

**Collection:**
```bash
cd /data/support_agents_training

# Microsoft Phi-3 datasets
git clone https://huggingface.co/datasets/microsoft/Phi-3.5-mini-instruct-train

python scripts/convert_phi3_to_training.py \
  --input Phi-3.5-mini-instruct-train/ \
  --output training_data/phi3_instruction_following.jsonl
```

---

## DATA PREPARATION PIPELINE

### Step 1: Download All Datasets

```bash
#!/bin/bash
# download_training_data.sh

BASE_DIR="/data/training_datasets"
mkdir -p $BASE_DIR

echo "Downloading RED Agent training data..."
# Nuclei templates
cd $BASE_DIR/red_agent && git clone https://github.com/projectdiscovery/nuclei-templates.git

# NVD CVE data (WARNING: Large! 8-10GB)
mkdir -p nvd && cd nvd
for year in {2020..2026}; do
  curl -O https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-${year}.json.gz
  gunzip nvdcve-1.1-${year}.json.gz
done

echo "Downloading BLUE Agent training data..."
cd $BASE_DIR/blue_agent

# GitHub security repos
for repo in rails/rails django/django expressjs/express; do
  git clone https://github.com/$repo.git
done

# Stack Overflow (requires API or dump)
# ...

echo "Downloading GOVERNANCE Agent training data..."
cd $BASE_DIR/governance_agent
git clone https://github.com/open-policy-agent/library.git

echo "All datasets downloaded!"
du -sh $BASE_DIR/
```

### Step 2: Convert to Training Format

```python
# convert_all_datasets.py
import os
import json
from pathlib import Path

def convert_all_datasets():
    """Convert all raw datasets to JSONL format"""
    
    datasets = {
        "nuclei_patterns": convert_nuclei_templates,
        "nvd_cves": convert_nvd_cves,
        "github_patches": convert_github_patches,
        "owasp_practices": convert_owasp_practices,
        "stackoverflow": convert_stackoverflow,
        "opa_policies": convert_opa_policies,
        "compliance_mappings": convert_compliance_mappings,
        "audit_events": convert_audit_events,
    }
    
    output_dir = Path("/data/training_datasets/converted")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for dataset_name, converter_func in datasets.items():
        print(f"Converting {dataset_name}...")
        output_file = output_dir / f"{dataset_name}.jsonl"
        converter_func(output_file)
        print(f"  ✓ {output_file} ({os.path.getsize(output_file) / 1e9:.2f}GB)")

if __name__ == "__main__":
    convert_all_datasets()
```

### Step 3: Combine and Shuffle

```python
# prepare_training_data.py
import json
import random
from pathlib import Path

def prepare_training_data():
    """Combine all datasets and prepare for fine-tuning"""
    
    converted_dir = Path("/data/training_datasets/converted")
    output_file = Path("/data/training_datasets/combined_training_data.jsonl")
    
    all_examples = []
    
    # Load all datasets
    for jsonl_file in sorted(converted_dir.glob("*.jsonl")):
        print(f"Loading {jsonl_file.name}...")
        with open(jsonl_file) as f:
            examples = [json.loads(line) for line in f]
            all_examples.extend(examples)
    
    print(f"Total examples: {len(all_examples)}")
    
    # Shuffle
    random.seed(42)  # Reproducible
    random.shuffle(all_examples)
    
    # Split: 80% train, 10% val, 10% test
    train_size = int(0.8 * len(all_examples))
    val_size = int(0.1 * len(all_examples))
    
    train_data = all_examples[:train_size]
    val_data = all_examples[train_size:train_size + val_size]
    test_data = all_examples[train_size + val_size:]
    
    # Write splits
    for split_name, split_data in [("train", train_data), ("val", val_data), ("test", test_data)]:
        output_path = Path(f"/data/training_datasets/{split_name}_data.jsonl")
        with open(output_path, 'w') as f:
            for example in split_data:
                f.write(json.dumps(example) + '\n')
        print(f"Wrote {len(split_data)} examples to {split_name}_data.jsonl")
```

---

## FINE-TUNING INSTRUCTIONS

### Setup Environment

```bash
# Create fine-tuning environment
python -m venv venv_finetune
source venv_finetune/bin/activate

# Install dependencies
pip install -r requirements-finetune.txt
# Contents:
# transformers==4.37.2
# torch==2.1.2
# bitsandbytes==0.41.3
# peft==0.7.1
# datasets==2.16.1
# accelerate==0.25.0
# wandb==0.16.4
```

### Fine-Tune RED Agent (WhiteRabbitNeo 7B Q4_K_M)

```bash
# Convert quantized model to fine-tunable format first
python scripts/load_quantized_model.py \
  --model_id "white-rabbit-neo/white-rabbit-neo-7b-gguf" \
  --quantization "Q4_K_M" \
  --output_dir "./models/red_agent_base"

# Fine-tune using QLoRA (parameter-efficient)
python fine_tune.py \
  --model_id "./models/red_agent_base" \
  --train_file "/data/training_datasets/train_data.jsonl" \
  --eval_file "/data/training_datasets/val_data.jsonl" \
  --output_dir "./models/red_agent_finetuned" \
  --num_train_epochs 3 \
  --learning_rate 2e-4 \
  --lora_r 8 \
  --lora_alpha 16 \
  --lora_dropout 0.1 \
  --per_device_train_batch_size 8 \
  --gradient_accumulation_steps 4 \
  --warmup_steps 100 \
  --logging_steps 50 \
  --eval_steps 500 \
  --save_steps 500 \
  --max_seq_length 2048
```

### Evaluate Fine-Tuned Models

```bash
# Benchmark accuracy on test set
python evaluate.py \
  --model_id "./models/red_agent_finetuned" \
  --test_file "/data/training_datasets/test_data.jsonl" \
  --metrics "accuracy,precision,recall,f1"

# Expected results:
# RED Agent: >90% accuracy on vulnerability detection
# BLUE Agent: >85% test pass rate on generated fixes
# GOVERNANCE Agent: >95% policy evaluation accuracy
# AUDIT Agent: 100% compliance mapping accuracy
```

---

## TOTAL DATA BUDGET

```
RED Agent:
  - Nuclei templates: 500MB
  - NVD CVEs: 8GB
  - CodeQL: 1GB
  - Bug Bounty: 3GB
  - CWE/CVSS: 1GB
  SUBTOTAL: 13.5GB

BLUE Agent:
  - Code examples: 4GB
  - GitHub patches: 5GB
  - OWASP: 2GB
  - Stack Overflow: 3GB
  - Test cases: 1GB
  - CoT Reasoning: 500MB
  SUBTOTAL: 15.5GB

GOVERNANCE Agent:
  - OPA policies: 500MB
  - Compliance mappings: 1GB
  - Risk scoring: 500MB
  - Instruction Following: 300MB
  SUBTOTAL: 2.3GB

AUDIT Agent:
  - Event logs: 2GB
  - Signed events: 500MB
  - Compliance mappings: 500MB
  - Instruction Following: (Shared with Gov)
  SUBTOTAL: 3GB

TOTAL: 34.3GB (compressed: ~10-15GB)
```

---

**These datasets, combined with QLoRA fine-tuning, will specialize the quantized models for security tasks while maintaining 90%+ accuracy compared to full-precision models.**

---
**End of File 5: Dataset Resources Guide (11 pages)**