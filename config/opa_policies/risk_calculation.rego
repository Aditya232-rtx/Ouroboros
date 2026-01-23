# Ouroboros AI - OPA Risk Calculation Policy
# Calculates risk scores for vulnerabilities based on CVSS, environment, and exploit ease

package governance.risk_calculation

import future.keywords.if

# Environment multipliers
environment_multipliers := {
    "dev": 1.0,
    "staging": 2.0,
    "production": 5.0
}

# Calculate risk score
risk_score := score if {
    cvss := input.vulnerability.cvss
    env := input.environment
    multiplier := environment_multipliers[env]
    score := cvss * 10 * multiplier
}

# Determine autonomy level based on risk score
autonomy_level := level if {
    risk_score < 20
    level := "auto_approve"  # V1: NOT USED, all require PR
}

autonomy_level := level if {
    risk_score >= 20
    risk_score < 50
    level := "suggest"
}

autonomy_level := level if {
    risk_score >= 50
    risk_score < 80
    level := "require"
}

autonomy_level := level if {
    risk_score >= 80
    level := "escalate"
}

# Required approvers based on risk
required_approvers := approvers if {
    risk_score < 50
    approvers := ["on_call_engineer"]
}

required_approvers := approvers if {
    risk_score >= 50
    risk_score < 80
    approvers := ["security_team"]
}

required_approvers := approvers if {
    risk_score >= 80
    approvers := ["security_team", "ciso"]
}

# Rationale for decision
rationale := reason if {
    cvss := input.vulnerability.cvss
    severity := input.vulnerability.severity
    env := input.environment
    reason := sprintf("CVSS %.1f %s vulnerability in %s environment", [cvss, severity, env])
}
