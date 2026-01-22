# OUROBOROS ORCHESTRATOR CONFIGURATION
**Version:** 1.0  
**Date:** January 22, 2026  
**Status:** Complete Configuration

---

## LANGGRAPH WORKFLOW ORCHESTRATION

### Workflow Definition

```yaml
# orchestrator_config.yaml (NEW FILE - CRITICAL)

langgraph:
  engine: "langgraph"
  version: "0.2.0"
  
  workflow_definition:
    nodes:
      - id: "red_agent"
        agent: "RED"
        timeout: 300  # 5 minutes max
      
      - id: "documentation_agent"
        agent: "DOCUMENTATION"
        timeout: 60  # 1 minute
      
      - id: "governance_agent"
        agent: "GOVERNANCE"
        timeout: 30  # 30 seconds
      
      - id: "blue_agent"
        agent: "BLUE"
        timeout: 3600  # 1 hour max (for many vulns)
      
      - id: "red_verification"
        agent: "RED"
        timeout: 300  # 5 minutes
      
      - id: "audit_agent"
        agent: "AUDIT"
        timeout: 10  # 10 seconds
    
    edges:
      - from: "START"
        to: "red_agent"
      
      - from: "red_agent"
        to: "documentation_agent"
      
      - from: "documentation_agent"
        to: "governance_agent"
      
      - from: "governance_agent"
        to: "blue_agent"
      
      - from: "blue_agent"
        to: "red_verification"
      
      - from: "red_verification"
        to: "governance_agent"
        condition: "verification_success"
      
      - from: "red_verification"
        to: "blue_agent"
        condition: "verification_failed"
        max_retries: 3
      
      - from: "*"
        to: "audit_agent"
        trigger: "on_every_event"
  
  error_recovery:
    strategy: "retry_with_backoff"
    max_retries: 3
    backoff_multiplier: 2
    
    fallback_actions:
      red_agent_timeout: "alert_security_team"
      blue_agent_failure: "create_manual_ticket"
      verification_loop_exceeded: "escalate_to_human"

timing_sla:
  total_workflow: 7200  # 2 hours
  
  per_agent:
    red_discovery: 300  # 5 minutes
    documentation_creation: 60  # 1 minute
    governance_decision: 30  # 30 seconds
    blue_fix_generation: 60  # 1 minute per vulnerability
    red_verification: 180  # 3 minutes
    audit_logging: 10  # 10 seconds
  
  scaling_factors:
    vulnerabilities_1_10: 1.0
    vulnerabilities_11_50: 2.0
    vulnerabilities_51_plus: 5.0
```

---

## POSTGRESQL DATABASE SCHEMA

### Complete Database Configuration

```yaml
database:
  postgres:
    host: "postgres.ouroboros.svc"
    port: 5432
    database: "ouroboros"
    
    schema:
      red_vulnerabilities:
        columns:
          - id: "VARCHAR(255) PRIMARY KEY"
          - scan_id: "UUID NOT NULL"
          - type: "VARCHAR(100)"
          - severity: "VARCHAR(20)"
          - cwe: "VARCHAR(20)"
          - cvss: "DECIMAL(3,1)"
          - file: "TEXT"
          - line: "INTEGER"
          - function: "VARCHAR(255)"
          - description: "TEXT"
          - poc_code: "TEXT"
          - poc_success_rate: "DECIMAL(3,2)"
          - confidence: "DECIMAL(3,2)"
          - created_at: "TIMESTAMP DEFAULT NOW()"
        indexes:
          - "idx_scan_id ON scan_id"
          - "idx_severity ON severity"
          - "idx_cvss ON cvss DESC"
      
      blue_fixes:
        columns:
          - id: "VARCHAR(255) PRIMARY KEY"
          - vulnerability_id: "VARCHAR(255) REFERENCES red_vulnerabilities(id)"
          - option: "INTEGER"
          - approach: "VARCHAR(255)"
          - code_diff: "JSONB"
          - test_code: "TEXT"
          - confidence: "DECIMAL(3,2)"
          - safety_gates: "JSONB"
          - created_at: "TIMESTAMP DEFAULT NOW()"
        indexes:
          - "idx_vuln_id ON vulnerability_id"
          - "idx_confidence ON confidence DESC"
      
      governance_decisions:
        columns:
          - id: "VARCHAR(255) PRIMARY KEY"
          - fix_id: "VARCHAR(255) REFERENCES blue_fixes(id)"
          - risk_score: "DECIMAL(5,2)"
          - autonomy_level: "VARCHAR(50)"
          - required_approvers: "TEXT[]"
          - created_at: "TIMESTAMP DEFAULT NOW()"
        indexes:
          - "idx_fix_id ON fix_id"
          - "idx_risk_score ON risk_score DESC"
      
      documentation_reports:
        columns:
          - id: "VARCHAR(255) PRIMARY KEY"
          - scan_id: "UUID"
          - google_doc_id: "VARCHAR(255)"
          - google_doc_url: "TEXT"
          - status: "VARCHAR(50)"
          - created_at: "TIMESTAMP DEFAULT NOW()"
          - updated_at: "TIMESTAMP DEFAULT NOW()"
        indexes:
          - "idx_scan_id ON scan_id"
          - "idx_doc_id ON google_doc_id"
    
    replication:
      method: "streaming"
      replicas: 2
      lag_threshold: 1000  # ms
    
    backup:
      method: "continuous_archiving"
      retention: 90  # days
      frequency: "daily"
```

---

## INTEGRATION FLOW DIAGRAMS

### Complete Workflow Sequence

```mermaid
graph TD
    A[START - GitHub Repo] --> B[RED Agent]
    B --> C[DOCUMENTATION Agent]
    C --> D[GOVERNANCE Agent]
    D --> E[BLUE Agent]
    E --> F[RED Verification]
    F -->|Success| D
    F -->|Failed| E
    D --> G[PR Creation]
    
    B -.-> H[AUDIT]
    C -.-> H
    D -.-> H
    E -.-> H
    F -.-> H
    G -.-> H
    
    style B fill:#ff6b6b
    style E fill:#4ecdc4
    style C fill:#95e1d3
    style D fill:#f38181
    style H fill:#aa96da
```

### Verification Loop Detail

```
RED discovers vulnerability
    ↓
BLUE generates 3 fix options
    ↓
BLUE selects best fix (highest confidence)
    ↓
RED re-runs PoC against fixed code
    ↓
    ├─→ PoC FAILS (vulnerability gone) → SUCCESS → Continue to GOVERNANCE
    └─→ PoC SUCCEEDS (still vulnerable) → FAILED → Back to BLUE (max 3 retries)
```

---

## PERFORMANCE MONITORING

### Expected Benchmarks

```yaml
performance_metrics:
  red_agent:
    avg_scan_time: 45  # seconds
    vulnerabilities_per_minute: 1.5
    poc_generation_success_rate: 0.95
  
  blue_agent:
    avg_fix_time: 45  # seconds per vulnerability
    safety_gate_pass_rate: 0.90
    fix_effectiveness: 0.98  # PoC failure rate after fix
  
  documentation_agent:
    avg_doc_creation: 30  # seconds
    update_latency: 5  # seconds
  
  governance_agent:
    avg_decision_time: 10  # seconds
    policy_evaluation_accuracy: 1.0
  
  audit_agent:
    avg_logging_time: 2  # seconds
    event_integrity_rate: 1.0
```

---

## DEPLOYMENT CONFIGURATION

### Docker Compose Services

```yaml
services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ouroboros
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
  
  immudb:
    image: codenotary/immudb:latest
    ports:
      - "3322:3322"
  
  opa:
    image: openpolicyagent/opa:latest
    command:
      - "run"
      - "--server"
      - "--addr=0.0.0.0:8181"
      - "/policies"
    ports:
      - "8181:8181"
    volumes:
      - ./config/opa_policies:/policies
  
  ouroboros-app:
    build: .
    depends_on:
      - redis
      - postgres
      - immudb
      - opa
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/ouroboros
      - REDIS_URL=redis://redis:6379
      - IMMUDB_HOST=immudb
      - OPA_URL=http://opa:8181
    ports:
      - "8000:8000"
```

---

## CRITICAL DEPENDENCIES

### Infrastructure Requirements

```yaml
minimum_requirements:
  cpu: "8 cores"
  memory: "32 GB RAM"
  gpu: "NVIDIA RTX 4090 or similar (24GB VRAM)"
  storage: "500 GB SSD"
  
  network:
    bandwidth: "1 Gbps"
    latency: "<10ms to cloud services"
  
  external_services:
    - "GitHub API access"
    - "Google Workspace API access"
    - "AWS Secrets Manager (optional)"
    - "PagerDuty API (optional)"
    - "Slack Webhook (optional)"

model_files:
  total_size: "12.5 GB"
  location: "/models"
  files:
    - "whiterabbitneo-7b-v1.5a-q4_k_m.gguf (4.08 GB)"
    - "deepseek-r1-distill-qwen-7b-q4_k_m.gguf (4.8 GB)"
    - "phi-3.5-mini-instruct-q6_k.gguf (3.2 GB)"
```

---

**End of Orchestrator Configuration**
