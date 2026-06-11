#!/usr/bin/env python3
"""Debug script to test file selection logic in Red Agent."""

from pathlib import Path
import sys

def main():
    sandbox_path = '/tmp/ouroboros_sandbox/2026-01-30T17-45-56-674992'
    path_obj = Path(sandbox_path)
    
    if not path_obj.exists():
        print(f"Sandbox not found: {sandbox_path}")
        # Try to find latest sandbox
        parent = Path('/tmp/ouroboros_sandbox')
        if parent.exists():
            sandboxes = sorted(parent.iterdir(), key=lambda x: x.name, reverse=True)
            if sandboxes:
                sandbox_path = str(sandboxes[0])
                path_obj = Path(sandbox_path)
                print(f"Using latest sandbox: {sandbox_path}")
    
    # Same logic as in red_agent.py
    code_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.php', '.go', '.java', '.rb', '.sh', '.bash',
        '.c', '.cpp', '.h', '.hpp', '.cs', '.rs', '.swift', '.kt', '.scala', '.lua',
        '.pl', '.pm', '.r', '.m', '.mm', '.asm', '.s'
    }
    config_extensions = {
        '.yml', '.yaml', '.json', '.xml', '.toml', '.ini', '.cfg', '.conf', '.env',
        '.properties', '.gradle', '.sbt', '.pom'
    }
    web_extensions = {
        '.html', '.htm', '.css', '.scss', '.sass', '.less', '.vue', '.svelte'
    }
    infra_extensions = {
        '.tf', '.hcl', '.dockerfile', '.sql', '.graphql', '.proto'
    }
    special_files = {
        'Dockerfile', 'Makefile', 'Jenkinsfile', 'Vagrantfile', 'Procfile',
        'Gemfile', 'Rakefile', '.htaccess', '.env', '.gitignore', 'requirements.txt',
        'package.json', 'composer.json', 'Cargo.toml', 'go.mod', 'pom.xml'
    }

    all_extensions = code_extensions | config_extensions | web_extensions | infra_extensions

    skip_dirs = {
        'node_modules', 'venv', '.venv', 'vendor', 'dist', 'build', 'target',
        '__pycache__', '.git', '.svn', '.hg', 'scan_results', 'coverage',
        'bin', 'obj', '.next', '.nuxt', 'out', '.cache', 'tmp'
    }

    print(f"\n=== Scanning {sandbox_path} ===\n")
    
    target_files = []
    all_files = list(path_obj.rglob('*'))
    
    print(f"Total items found: {len(all_files)}")
    
    for p in all_files:
        if not p.is_file():
            continue
        
        # Get RELATIVE path to sandbox
        try:
            rel_path = p.relative_to(path_obj)
            rel_parts = rel_path.parts
        except ValueError:
            continue
        
        # Debug each file
        skip_reason = None
        for skip_dir in skip_dirs:
            if skip_dir in rel_parts:  # Check relative parts, not absolute
                skip_reason = f'in skip_dir: {skip_dir}'
                break
        
        suffix_match = p.suffix.lower() in all_extensions
        special_match = p.name in special_files
        matches = suffix_match or special_match
        
        print(f"  {rel_path}")
        print(f"    suffix='{p.suffix}', in_ext={suffix_match}, special={special_match}, skip={skip_reason}")
        
        if not skip_reason and matches:
            target_files.append(p)
            print(f"    ✅ INCLUDED")
        else:
            print(f"    ❌ EXCLUDED")

    print(f"\n=== RESULT ===")
    print(f"Total files to scan: {len(target_files)}")
    print(f"Files: {[str(f.relative_to(path_obj)) for f in target_files]}")

if __name__ == "__main__":
    main()
