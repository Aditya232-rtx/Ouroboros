#!/usr/bin/env python3
"""
Comprehensive test script for the Ouroboros scan workflow.
Tests the complete flow: scan creation -> status polling -> results retrieval.
"""

import requests
import json
import time
from datetime import datetime
from typing import Optional

BASE_URL = "http://localhost:8000"
TEST_REPO_URL = "https://github.com/samoylenko/vulnerable-app-nodejs-express.git"

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}\n")

def print_success(message: str):
    """Print success message."""
    print(f"✅ {message}")

def print_error(message: str):
    """Print error message."""
    print(f"❌ {message}")

def print_info(message: str):
    """Print info message."""
    print(f"ℹ️  {message}")

def create_scan(repo_url: str = TEST_REPO_URL) -> Optional[str]:
    """
    Create a new security scan.
    
    Returns:
        scan_id if successful, None otherwise
    """
    print_section("Creating Security Scan")
    
    scan_request = {
        "repo_url": repo_url,
        "branch": "main",
        "scan_profile": "standard",
        "auto_fix": True,
        "create_pr": False  # Set to False for testing to avoid creating PRs
    }
    
    print_info(f"Repository: {repo_url}")
    print_info(f"Profile: {scan_request['scan_profile']}")
    print_info(f"Auto-fix: {scan_request['auto_fix']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/scan",
            json=scan_request,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200 or response.status_code == 201:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            scan_id = data.get("scan_id")
            print_success(f"Scan created successfully! ID: {scan_id}")
            return scan_id
        else:
            error_data = response.json()
            print_error(f"Failed to create scan: {error_data.get('detail', 'Unknown error')}")
            print(f"Response: {json.dumps(error_data, indent=2)}")
            return None
            
    except Exception as e:
        print_error(f"Exception during scan creation: {str(e)}")
        return None

def poll_scan_status(scan_id: str, max_polls: int = 60, poll_interval: int = 5):
    """
    Poll scan status until completion or timeout.
    
    Args:
        scan_id: The scan ID to poll
        max_polls: Maximum number of polling attempts
        poll_interval: Seconds between polls
    """
    print_section(f"Polling Scan Status: {scan_id}")
    
    for attempt in range(max_polls):
        try:
            response = requests.get(f"{BASE_URL}/status/{scan_id}")
            
            if response.status_code == 404:
                print_error(f"Scan not found: {scan_id}")
                return None
            elif response.status_code != 200:
                print_error(f"Error fetching status: {response.status_code}")
                return None
            
            data = response.json()
            status = data.get("status")
            progress = data.get("progress_percent", 0)
            phase = data.get("current_phase", "unknown")
            vulns = data.get("vulnerabilities_found", 0)
            
            # Print status update
            status_symbol = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌"
            }.get(status, "❓")
            
            print(f"[{attempt + 1}/{max_polls}] {status_symbol} Status: {status.upper()} | "
                  f"Progress: {progress}% | Phase: {phase} | Vulns: {vulns}")
            
            # Check if completed
            if status == "completed":
                print_success("Scan completed successfully!")
                return data
            elif status == "failed":
                error_msg = data.get("error_message", "Unknown error")
                print_error(f"Scan failed: {error_msg}")
                return data
            
            # Wait before next poll
            if attempt < max_polls - 1:
                time.sleep(poll_interval)
                
        except Exception as e:
            print_error(f"Exception during polling: {str(e)}")
            time.sleep(poll_interval)
    
    print_error(f"Timeout: Scan did not complete within {max_polls * poll_interval} seconds")
    return None

def get_scan_details(scan_id: str):
    """Get detailed scan results including vulnerabilities and fixes."""
    print_section(f"Fetching Detailed Results: {scan_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/status/{scan_id}/detail")
        
        if response.status_code != 200:
            print_error(f"Failed to fetch details: {response.status_code}")
            return None
        
        data = response.json()
        
        # Print summary
        print_info(f"Status: {data.get('status')}")
        print_info(f"Progress: {data.get('progress_percent')}%")
        print_info(f"Phase: {data.get('current_phase')}")
        print_info(f"Vulnerabilities Found: {data.get('vulnerabilities_found', 0)}")
        print_info(f"Fixes Applied: {data.get('fixes_applied', 0)}")
        
        # Print vulnerabilities
        vulnerabilities = data.get("vulnerabilities", [])
        if vulnerabilities:
            print(f"\n📋 Vulnerabilities ({len(vulnerabilities)}):")
            for i, vuln in enumerate(vulnerabilities[:5], 1):  # Show first 5
                print(f"  {i}. [{vuln.get('severity', 'UNKNOWN').upper()}] {vuln.get('type', 'Unknown')}")
                print(f"     File: {vuln.get('file', 'N/A')}:{vuln.get('line', 0)}")
                print(f"     {vuln.get('description', '')[:100]}...")
        
        # Print fixes
        fixes = data.get("fixes", [])
        if fixes:
            print(f"\n🔧 Fixes ({len(fixes)}):")
            for i, fix in enumerate(fixes[:5], 1):  # Show first 5
                print(f"  {i}. {fix.get('file', 'N/A')} - {fix.get('status', 'unknown')}")
                print(f"     Lines changed: {fix.get('lines_changed', 0)}")
        
        # PR URL
        pr_url = data.get("pr_url")
        if pr_url:
            print(f"\n🔗 Pull Request: {pr_url}")
        
        return data
        
    except Exception as e:
        print_error(f"Exception fetching details: {str(e)}")
        return None

def get_scan_logs(scan_id: str):
    """Get scan execution logs."""
    print_section(f"Fetching Scan Logs: {scan_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/status/{scan_id}/logs")
        
        if response.status_code != 200:
            print_error(f"Failed to fetch logs: {response.status_code}")
            return None
        
        logs = response.json()
        
        if logs:
            print(f"📝 Recent Logs ({len(logs)} entries):")
            for log in logs[-10:]:  # Show last 10 logs
                level = log.get("level", "info").upper()
                source = log.get("source", "system")
                message = log.get("message", "")
                timestamp = log.get("timestamp", "")
                
                level_symbol = {
                    "INFO": "ℹ️",
                    "DEBUG": "🔍",
                    "WARNING": "⚠️",
                    "ERROR": "❌",
                    "SUCCESS": "✅"
                }.get(level, "•")
                
                print(f"  {level_symbol} [{timestamp}] [{source}] {message}")
        else:
            print_info("No logs available")
        
        return logs
        
    except Exception as e:
        print_error(f"Exception fetching logs: {str(e)}")
        return None

def main():
    """Run the complete scan workflow test."""
    print_section("Ouroboros Scan Workflow Test")
    print(f"API Base URL: {BASE_URL}")
    print(f"Test Repository: {TEST_REPO_URL}")
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Step 1: Create scan
    scan_id = create_scan(TEST_REPO_URL)
    
    if not scan_id:
        print_error("Failed to create scan. Exiting.")
        return
    
    # Step 2: Poll status
    final_status = poll_scan_status(scan_id, max_polls=60, poll_interval=5)
    
    if not final_status:
        print_error("Failed to get final status. Exiting.")
        return
    
    # Step 3: Get detailed results
    details = get_scan_details(scan_id)
    
    # Step 4: Get logs
    logs = get_scan_logs(scan_id)
    
    # Summary
    print_section("Test Summary")
    print(f"Scan ID: {scan_id}")
    print(f"Final Status: {final_status.get('status', 'unknown')}")
    print(f"Vulnerabilities: {details.get('vulnerabilities_found', 0) if details else 'N/A'}")
    print(f"Fixes: {details.get('fixes_applied', 0) if details else 'N/A'}")
    print(f"Completed at: {datetime.now().isoformat()}")
    
    if final_status and final_status.get("status") == "completed":
        print_success("✨ Scan workflow test PASSED!")
    else:
        print_error("⚠️  Scan workflow test completed with issues")

if __name__ == "__main__":
    main()
