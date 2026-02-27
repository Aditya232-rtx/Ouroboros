"""
Ouroboros AI - Dataset Schema Standardizer
Task 1.1: Convert all vulnerability datasets into a unified JSONL schema
for fine-tuning the Qwen 2.5 Coder 3B Blue Team Patching Adapter.

Target schema (one JSON object per line):
{
  "messages": [
    {"role": "system",    "content": "You are a Blue Team patching agent..."},
    {"role": "user",      "content": "Vulnerability: <type>\\nCriticality: <level>\\nCode: <code>"},
    {"role": "assistant", "content": "<patched_code>"}
  ]
}

Supported sources:
  --sources synthetic juliet cvefixes patchdb vpp

Usage:
  python scripts/data_preparation/standardize_schema.py \\
      --sources synthetic juliet cvefixes patchdb vpp \\
      --output-dir data/splits \\
      --train-split 0.8 --val-split 0.1 --test-split 0.1
"""

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("standardize_schema")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a Blue Team patching agent. Analyze the vulnerability, its "
    "criticality, and provide the patched code."
)

CRITICALITY_MAP = {
    "critical": "Critical",
    "high": "High",
    "medium": "Medium",
    "moderate": "Medium",
    "low": "Low",
    "informational": "Low",
    "none": "Low",
    "unknown": "Medium",
}

CWE_TO_VULN_TYPE = {
    "89":  "SQL Injection",
    "79":  "Cross-Site Scripting (XSS)",
    "78":  "Command Injection",
    "22":  "Path Traversal",
    "918": "Server-Side Request Forgery (SSRF)",
    "502": "Insecure Deserialization",
    "639": "Insecure Direct Object Reference (IDOR)",
    "287": "Authentication Bypass",
    "327": "Cryptographic Failure",
    "250": "Execution with Unnecessary Privileges",
    "20":  "Improper Input Validation",
    "476": "NULL Pointer Dereference",
    "119": "Buffer Overflow",
    "416": "Use After Free",
    "190": "Integer Overflow",
    "362": "Race Condition",
    "732": "Insecure Permissions",
    "798": "Hardcoded Credentials",
}


def cwe_to_vuln_type(cwe_str: str) -> str:
    """Extract CWE number and return human-readable vulnerability type."""
    if not cwe_str:
        return "Security Vulnerability"
    match = re.search(r"(\d+)", str(cwe_str))
    if match:
        return CWE_TO_VULN_TYPE.get(match.group(1), f"CWE-{match.group(1)} Vulnerability")
    return "Security Vulnerability"


def normalize_criticality(severity: str) -> str:
    return CRITICALITY_MAP.get(str(severity).lower().strip(), "Medium")


def _code_hash(code: str) -> str:
    """Return first 8 chars of SHA-256 of the code string."""
    return hashlib.sha256(code.encode("utf-8", errors="ignore")).hexdigest()[:8]


def make_group_key(
    source: str,
    cve_id: Optional[str] = None,
    cwe_id: Optional[str] = None,
    code: str = "",
) -> str:
    """
    Build a stable group key for leak-free splitting.
    Priority: CVE-ID > source_CWE_hash > source_hash
    """
    cve = (cve_id or "").strip().upper()
    if cve and cve not in ("", "NA", "N/A", "UNKNOWN"):
        return cve
    cwe = re.sub(r"[^\d]", "", str(cwe_id or ""))
    h = _code_hash(code)
    if cwe:
        return f"{source}_CWE-{cwe}_{h}"
    return f"{source}_{h}"


def build_entry(
    vuln_type: str,
    criticality: str,
    vulnerable_code: str,
    patched_code: str,
    meta: Optional[Dict] = None,
) -> Dict:
    """Build one standardized JSONL entry, optionally with a _meta tracking field."""
    user_content = (
        f"Vulnerability: {vuln_type}\n"
        f"Criticality: {criticality}\n"
        f"Code: {vulnerable_code.strip()}"
    )
    entry: Dict[str, Any] = {
        "messages": [
            {"role": "system",    "content": SYSTEM_PROMPT},
            {"role": "user",      "content": user_content},
            {"role": "assistant", "content": patched_code.strip()},
        ]
    }
    if meta:
        entry["_meta"] = meta
    return entry


# ─────────────────────────────────────────────────────────────────────────────
# BASE CONVERTER
# ─────────────────────────────────────────────────────────────────────────────

class BaseConverter(ABC):
    name: str = "base"

    def __init__(self, raw_dir: Path, processed_dir: Path):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.logger = logging.getLogger(f"converter.{self.name}")

    @abstractmethod
    def convert(self) -> Generator[Dict, None, None]:
        """Yield standardized JSONL entries."""

    def run(self) -> Path:
        """Convert source and write per-source processed JSONL. Returns output path."""
        out_path = self.processed_dir / f"{self.name}.jsonl"
        count = 0
        skipped = 0
        with out_path.open("w", encoding="utf-8") as f:
            for entry in self.convert():
                if SchemaValidator.is_valid(entry):
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    count += 1
                else:
                    skipped += 1
        self.logger.info(f"Wrote {count} entries ({skipped} skipped) → {out_path}")
        return out_path


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHETIC CONVERTER  (always available — no raw data required)
# ─────────────────────────────────────────────────────────────────────────────

class SyntheticConverter(BaseConverter):
    """
    Generates synthetic training pairs from the vulnerability patterns defined
    in blue_agent.py's fix_templates. Produces multi-language variants for each
    vulnerability type so the model learns diverse patching patterns.
    """
    name = "synthetic"

    # (vuln_type, criticality, language, vulnerable_code, patched_code)
    SAMPLES: List[Tuple[str, str, str, str, str]] = [
        # ── SQL Injection ────────────────────────────────────────────────────
        ("SQL Injection", "High", "Python",
         """def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    return cursor.fetchone()""",
         """def get_user(user_id):
    # FIX: Use parameterized query to prevent SQL injection
    query = "SELECT * FROM users WHERE id = %s"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()"""),

        ("SQL Injection", "High", "JavaScript",
         """async function getUser(userId) {
    const result = await client.query(
        `SELECT * FROM users WHERE id = ${userId}`
    );
    return result.rows[0];
}""",
         """async function getUser(userId) {
    // FIX: Parameterized query prevents SQL injection
    const result = await client.query(
        'SELECT * FROM users WHERE id = $1',
        [userId]
    );
    return result.rows[0];
}"""),

        ("SQL Injection", "Critical", "Java",
         """public User getUser(String userId) throws SQLException {
    String query = "SELECT * FROM users WHERE id = '" + userId + "'";
    ResultSet rs = stmt.executeQuery(query);
    return mapToUser(rs);
}""",
         """public User getUser(String userId) throws SQLException {
    // FIX: PreparedStatement prevents SQL injection
    String query = "SELECT * FROM users WHERE id = ?";
    PreparedStatement ps = conn.prepareStatement(query);
    ps.setString(1, userId);
    ResultSet rs = ps.executeQuery();
    return mapToUser(rs);
}"""),

        # ── XSS ─────────────────────────────────────────────────────────────
        ("Cross-Site Scripting (XSS)", "High", "JavaScript",
         """function showMessage(userInput) {
    document.getElementById('output').innerHTML = userInput;
}""",
         """function showMessage(userInput) {
    // FIX: Use textContent to prevent XSS — never use innerHTML with user input
    document.getElementById('output').textContent = userInput;
}"""),

        ("Cross-Site Scripting (XSS)", "High", "Python",
         """@app.route('/greet')
def greet():
    name = request.args.get('name', '')
    return f'<h1>Hello, {name}!</h1>'""",
         """import html

@app.route('/greet')
def greet():
    name = request.args.get('name', '')
    # FIX: Escape HTML special characters to prevent XSS
    safe_name = html.escape(name)
    return f'<h1>Hello, {safe_name}!</h1>'"""),

        # ── Command Injection ────────────────────────────────────────────────
        ("Command Injection", "Critical", "Python",
         """import os

def ping_host(host):
    result = os.system(f"ping -c 1 {host}")
    return result""",
         """import subprocess
import shlex

def ping_host(host):
    # FIX: Use subprocess with list args — never shell=True with user input
    result = subprocess.run(
        ["ping", "-c", "1", host],
        capture_output=True, text=True, timeout=5
    )
    return result.returncode"""),

        ("Command Injection", "Critical", "Python",
         """import subprocess

def convert_file(filename):
    cmd = f"convert {filename} output.png"
    subprocess.run(cmd, shell=True)""",
         """import subprocess
from pathlib import Path

def convert_file(filename):
    # FIX: List-form args + shell=False + validated filename
    safe_name = Path(filename).name  # strip path traversal
    subprocess.run(
        ["convert", safe_name, "output.png"],
        shell=False, check=True
    )"""),

        # ── Path Traversal ───────────────────────────────────────────────────
        ("Path Traversal", "High", "Python",
         """import os

BASE_DIR = "/var/www/files"

def read_file(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, 'r') as f:
        return f.read()""",
         """import os
from pathlib import Path

BASE_DIR = Path("/var/www/files").resolve()

def read_file(filename):
    # FIX: Resolve the full path and verify it stays within BASE_DIR
    requested = (BASE_DIR / filename).resolve()
    if not str(requested).startswith(str(BASE_DIR)):
        raise ValueError("Path traversal detected")
    with open(requested, 'r') as f:
        return f.read()"""),

        # ── SSRF ─────────────────────────────────────────────────────────────
        ("Server-Side Request Forgery (SSRF)", "High", "Python",
         """import requests

def fetch_url(url):
    response = requests.get(url)
    return response.text""",
         """import ipaddress
import re
import requests
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"https", "http"}
BLOCKED_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
]

def fetch_url(url):
    # FIX: Validate URL scheme and block private/internal IP ranges (SSRF)
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Blocked scheme: {parsed.scheme}")
    try:
        addr = ipaddress.ip_address(parsed.hostname)
        for blocked in BLOCKED_RANGES:
            if addr in blocked:
                raise ValueError(f"Blocked internal address: {addr}")
    except ValueError as e:
        if "does not appear to be" not in str(e):
            raise
    response = requests.get(url, timeout=5, allow_redirects=False)
    return response.text"""),

        # ── Insecure Deserialization ─────────────────────────────────────────
        ("Insecure Deserialization", "Critical", "Python",
         """import pickle

def load_session(session_data: bytes):
    return pickle.loads(session_data)""",
         """import json

def load_session(session_data: bytes):
    # FIX: Use JSON instead of pickle — pickle can execute arbitrary code
    return json.loads(session_data.decode('utf-8'))"""),

        # ── Authentication Bypass ────────────────────────────────────────────
        ("Authentication Bypass", "Critical", "Python",
         """import hashlib

def check_password(input_password: str, stored_hash: str) -> bool:
    input_hash = hashlib.md5(input_password.encode()).hexdigest()
    return input_hash == stored_hash""",
         """import argon2
from argon2 import PasswordHasher

ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

def check_password(input_password: str, stored_hash: str) -> bool:
    # FIX: Use Argon2 (memory-hard) instead of MD5 (broken, fast-hashable)
    try:
        return ph.verify(stored_hash, input_password)
    except argon2.exceptions.VerifyMismatchError:
        return False"""),

        # ── Cryptographic Failure ────────────────────────────────────────────
        ("Cryptographic Failure", "High", "Python",
         """from Crypto.Cipher import DES
import hashlib

def encrypt_data(data: str, key: str) -> bytes:
    cipher = DES.new(key[:8].encode(), DES.MODE_ECB)
    return cipher.encrypt(data.encode().ljust(8))""",
         """from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_data(data: str, key: bytes) -> bytes:
    # FIX: Use AES-256-GCM (authenticated encryption) instead of DES-ECB (broken)
    # key must be 32 bytes (256-bit)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit random nonce
    ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
    return nonce + ciphertext  # prepend nonce for decryption"""),

        # ── Hardcoded Credentials ────────────────────────────────────────────
        ("Hardcoded Credentials", "Critical", "Python",
         """import psycopg2

def get_db():
    conn = psycopg2.connect(
        host="localhost",
        database="appdb",
        user="admin",
        password="SuperSecret123!"
    )
    return conn""",
         """import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db():
    # FIX: Read credentials from environment variables — never hardcode secrets
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn"""),

        # ── IDOR ─────────────────────────────────────────────────────────────
        ("Insecure Direct Object Reference (IDOR)", "High", "Python",
         """@app.route('/api/document/<int:doc_id>')
def get_document(doc_id):
    doc = db.query(Document).filter_by(id=doc_id).first()
    return jsonify(doc.to_dict())""",
         """@app.route('/api/document/<int:doc_id>')
@login_required
def get_document(doc_id):
    # FIX: Verify the requesting user owns the document (IDOR prevention)
    doc = db.query(Document).filter_by(
        id=doc_id, owner_id=current_user.id
    ).first()
    if not doc:
        abort(403)  # Forbidden — not 404, to avoid information disclosure
    return jsonify(doc.to_dict())"""),

        # ── Security Misconfiguration ────────────────────────────────────────
        ("Security Misconfiguration", "Medium", "Python",
         """from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow all origins
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'dev'""",
         """import os
from flask import Flask
from flask_cors import CORS

app = Flask(__name__)

# FIX: Restrict CORS to known origins, disable debug in production
allowed_origins = os.getenv("ALLOWED_ORIGINS", "https://app.example.com").split(",")
CORS(app, origins=allowed_origins, supports_credentials=True)

app.config['DEBUG'] = os.getenv("FLASK_DEBUG", "false").lower() == "true"
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")  # Must be set in env
assert app.config['SECRET_KEY'], "SECRET_KEY environment variable not set!" """),

        # ── Dockerfile: Root User ────────────────────────────────────────────
        ("Execution with Unnecessary Privileges", "High", "Dockerfile",
         """FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]""",
         """FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .

# FIX: Run as non-root user to limit privilege scope (CWE-250)
RUN chown -R node:node /app
USER node

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \\
    CMD wget -qO- http://localhost:3000/health || exit 1

EXPOSE 3000
CMD ["node", "server.js"]"""),

        # ── NULL Pointer Dereference ─────────────────────────────────────────
        ("NULL Pointer Dereference", "Medium", "C",
         """#include <stdlib.h>
#include <string.h>

int process_data(const char *input) {
    char *buffer = malloc(strlen(input) + 1);
    strcpy(buffer, input);
    return buffer[0];
}""",
         """#include <stdlib.h>
#include <string.h>

int process_data(const char *input) {
    if (input == NULL) return -1;  // FIX: Guard against NULL input
    char *buffer = malloc(strlen(input) + 1);
    if (buffer == NULL) return -1; // FIX: Check malloc return value
    strcpy(buffer, input);
    int result = (unsigned char)buffer[0];
    free(buffer);                  // FIX: Release allocated memory
    return result;
}"""),

        # ── Buffer Overflow ──────────────────────────────────────────────────
        ("Buffer Overflow", "Critical", "C",
         """#include <string.h>

void copy_username(const char *input) {
    char buffer[64];
    strcpy(buffer, input);  // No bounds check
}""",
         """#include <string.h>
#include <stdio.h>

void copy_username(const char *input) {
    if (input == NULL) return;
    char buffer[64];
    // FIX: Use strncpy with explicit size limit then null-terminate
    strncpy(buffer, input, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\\0';
}"""),

        # ── Race Condition ───────────────────────────────────────────────────
        ("Race Condition", "Medium", "Python",
         """import threading

counter = 0

def increment():
    global counter
    counter += 1""",
         """import threading

counter = 0
_lock = threading.Lock()

def increment():
    global counter
    # FIX: Use a lock to prevent data race on shared counter
    with _lock:
        counter += 1"""),

        # ── Integer Overflow ─────────────────────────────────────────────────
        ("Integer Overflow", "Medium", "Python",
         """def allocate_buffer(size: int) -> bytearray:
    # Calculate buffer with header
    total = size + 1024
    return bytearray(total)""",
         """import sys

def allocate_buffer(size: int) -> bytearray:
    # FIX: Validate size before arithmetic to prevent integer overflow / OOM
    MAX_SIZE = 100 * 1024 * 1024  # 100 MB limit
    if size < 0 or size > MAX_SIZE:
        raise ValueError(f"Invalid buffer size: {size}")
    total = size + 1024
    return bytearray(total)"""),
    ]

    def convert(self) -> Generator[Dict, None, None]:
        self.logger.info(f"Generating {len(self.SAMPLES)} synthetic training samples")
        for vuln_type, criticality, language, vuln_code, patch_code in self.SAMPLES:
            user_content = (
                f"Vulnerability: {vuln_type}\n"
                f"Language: {language}\n"
                f"Criticality: {criticality}\n"
                f"Code:\n{vuln_code.strip()}"
            )
            slug = re.sub(r"[^a-z0-9]", "_", vuln_type.lower())[:30]
            group_key = make_group_key("synthetic", code=vuln_code, cwe_id=slug)
            yield {
                "messages": [
                    {"role": "system",    "content": SYSTEM_PROMPT},
                    {"role": "user",      "content": user_content},
                    {"role": "assistant", "content": patch_code.strip()},
                ],
                "_meta": {
                    "source":    "synthetic",
                    "cve_id":    None,
                    "cwe_id":    None,
                    "group_key": group_key,
                },
            }


# ─────────────────────────────────────────────────────────────────────────────
# JULIET CONVERTER  (NSA Juliet Test Suite)
# ─────────────────────────────────────────────────────────────────────────────

class JulietConverter(BaseConverter):
    """
    Reads NSA Juliet Test Suite.
    Expected directory structure:
        data/raw/juliet/
            CWE89_SQL_Injection/
                CWE89_bad.c   ← vulnerable
                CWE89_good.c  ← patched
            CWE79_XSS/
                ...
    Each CWE directory may contain _bad (vulnerable) and _good (patched) files.
    """
    name = "juliet"
    BAD_SUFFIX  = "_bad"
    GOOD_SUFFIX = "_good"
    EXTENSIONS  = {".c", ".cpp", ".java", ".py"}

    def convert(self) -> Generator[Dict, None, None]:
        juliet_dir = self.raw_dir / "juliet"
        if not juliet_dir.exists():
            self.logger.warning(f"Juliet directory not found: {juliet_dir}")
            return

        count = 0
        for cwe_dir in sorted(juliet_dir.iterdir()):
            if not cwe_dir.is_dir():
                continue

            # Extract CWE from directory name, e.g. CWE89_SQL_Injection
            cwe_match = re.match(r"CWE(\d+)", cwe_dir.name, re.IGNORECASE)
            cwe_num = cwe_match.group(1) if cwe_match else None
            vuln_type = cwe_to_vuln_type(cwe_num) if cwe_num else cwe_dir.name

            # Pair bad/good files by base name
            bad_files: Dict[str, Path] = {}
            good_files: Dict[str, Path] = {}

            for f in cwe_dir.rglob("*"):
                if f.suffix not in self.EXTENSIONS:
                    continue
                stem = f.stem
                if self.BAD_SUFFIX in stem:
                    base = stem.replace(self.BAD_SUFFIX, "")
                    bad_files[base] = f
                elif self.GOOD_SUFFIX in stem:
                    base = stem.replace(self.GOOD_SUFFIX, "")
                    good_files[base] = f

            for base, bad_path in bad_files.items():
                if base not in good_files:
                    continue
                try:
                    vuln_code  = bad_path.read_text(errors="ignore")[:4000]
                    patch_code = good_files[base].read_text(errors="ignore")[:4000]
                    group_key  = make_group_key("juliet", cwe_id=cwe_num, code=vuln_code)
                    yield build_entry(
                        vuln_type, "High", vuln_code, patch_code,
                        meta={"source": "juliet", "cve_id": None,
                              "cwe_id": f"CWE-{cwe_num}" if cwe_num else None,
                              "group_key": group_key},
                    )
                    count += 1
                except Exception as e:
                    self.logger.warning(f"Error reading {bad_path}: {e}")

        self.logger.info(f"Juliet: produced {count} pairs")


# ─────────────────────────────────────────────────────────────────────────────
# CVEFIXES CONVERTER
# ─────────────────────────────────────────────────────────────────────────────

class CVEfixesConverter(BaseConverter):
    """
    Reads the CVEfixes dataset (https://github.com/secureIT-project/CVEfixes).
    Supports two input formats:
      1. SQLite database: CVEfixes.db  (preferred)
      2. CSV files: commits.csv + file_change.csv
    """
    name = "cvefixes"

    def convert(self) -> Generator[Dict, None, None]:
        cvefixes_dir = self.raw_dir / "cvefixes"
        if not cvefixes_dir.exists():
            self.logger.warning(f"CVEfixes directory not found: {cvefixes_dir}")
            return

        # Try SQLite first
        db_files = list(cvefixes_dir.glob("*.db"))
        if db_files:
            yield from self._from_sqlite(db_files[0])
        else:
            yield from self._from_csv(cvefixes_dir)

    def _from_sqlite(self, db_path: Path) -> Generator[Dict, None, None]:
        self.logger.info(f"Reading CVEfixes SQLite: {db_path}")
        count = 0
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Query: join CVE, commits, file_change tables
            query = """
                SELECT
                    c.cve_id,
                    c.cvss_v3 AS cvss,
                    c.cwe_id,
                    fc.code_before,
                    fc.code_after
                FROM cve c
                JOIN fixes f       ON c.cve_id = f.cve_id
                JOIN commits cm    ON f.hash = cm.hash
                JOIN file_change fc ON cm.hash = fc.hash
                WHERE fc.code_before IS NOT NULL
                  AND fc.code_after  IS NOT NULL
                  AND LENGTH(fc.code_before) > 20
                  AND LENGTH(fc.code_after)  > 20
                LIMIT 50000
            """
            try:
                cur.execute(query)
            except sqlite3.OperationalError:
                # Schema may vary — try simpler query
                cur.execute("""
                    SELECT code_before, code_after, 'unknown' AS cwe_id,
                           5.0 AS cvss, 'CVE-UNKNOWN' AS cve_id
                    FROM file_change
                    WHERE code_before IS NOT NULL AND code_after IS NOT NULL
                    LIMIT 50000
                """)

            for row in cur:
                cwe  = row["cwe_id"] or "unknown"
                cve  = row["cve_id"] or None
                cvss = float(row["cvss"] or 5.0)
                criticality = self._cvss_to_criticality(cvss)
                vuln_type   = cwe_to_vuln_type(cwe)
                vuln_code   = str(row["code_before"])[:4000]
                patch_code  = str(row["code_after"])[:4000]
                group_key   = make_group_key("cvefixes", cve_id=cve, cwe_id=cwe, code=vuln_code)
                yield build_entry(
                    vuln_type, criticality, vuln_code, patch_code,
                    meta={"source": "cvefixes", "cve_id": cve,
                          "cwe_id": cwe, "group_key": group_key},
                )
                count += 1

            conn.close()
        except Exception as e:
            self.logger.error(f"CVEfixes SQLite error: {e}")
        self.logger.info(f"CVEfixes (SQLite): produced {count} entries")

    def _from_csv(self, cvefixes_dir: Path) -> Generator[Dict, None, None]:
        import csv
        self.logger.info(f"Reading CVEfixes CSV files in {cvefixes_dir}")
        count = 0

        file_change_csv = cvefixes_dir / "file_change.csv"
        if not file_change_csv.exists():
            self.logger.warning("No CVEfixes.db or file_change.csv found — skipping")
            return

        try:
            with file_change_csv.open(encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    code_before = row.get("code_before", "")
                    code_after  = row.get("code_after", "")
                    if not code_before or not code_after:
                        continue
                    cwe       = row.get("cwe_id", "unknown")
                    cve       = row.get("cve_id") or None
                    vuln_type = cwe_to_vuln_type(cwe)
                    group_key = make_group_key("cvefixes", cve_id=cve, cwe_id=cwe, code=code_before)
                    yield build_entry(
                        vuln_type, "Medium", code_before[:4000], code_after[:4000],
                        meta={"source": "cvefixes", "cve_id": cve,
                              "cwe_id": cwe, "group_key": group_key},
                    )
                    count += 1
        except Exception as e:
            self.logger.error(f"CVEfixes CSV error: {e}")
        self.logger.info(f"CVEfixes (CSV): produced {count} entries")

    @staticmethod
    def _cvss_to_criticality(cvss: float) -> str:
        if cvss >= 9.0: return "Critical"
        if cvss >= 7.0: return "High"
        if cvss >= 4.0: return "Medium"
        return "Low"



# ─────────────────────────────────────────────────────────────────────────────
# VPP CONVERTER (Vulnerability-Patch Pairs)
# ─────────────────────────────────────────────────────────────────────────────

class VPPConverter(BaseConverter):
    """
    Reads VPP (Vulnerability Patch Pairs) dataset.
    Expects JSON/JSONL files with function-level before/after pairs.
    Common field names: func_before / func_after, or vul / fix.
    """
    name = "vpp"

    def convert(self) -> Generator[Dict, None, None]:
        vpp_dir = self.raw_dir / "vpp"
        if not vpp_dir.exists():
            self.logger.warning(f"VPP directory not found: {vpp_dir}")
            return

        count = 0
        for json_file in sorted(vpp_dir.glob("**/*.json*")):
            self.logger.info(f"Reading VPP file: {json_file.name}")
            try:
                content = json_file.read_text(encoding="utf-8", errors="ignore")
                if json_file.suffix == ".jsonl":
                    records = [json.loads(l) for l in content.splitlines() if l.strip()]
                else:
                    data = json.loads(content)
                    records = data if isinstance(data, list) else [data]

                for record in records:
                    # Support multiple field naming conventions
                    vuln_code = (
                        record.get("func_before") or
                        record.get("vul") or
                        record.get("vulnerable") or
                        record.get("code_before") or ""
                    )
                    patch_code = (
                        record.get("func_after") or
                        record.get("fix") or
                        record.get("patched") or
                        record.get("code_after") or ""
                    )
                    if not vuln_code or not patch_code:
                        continue

                    cwe       = record.get("cwe") or record.get("cwe_id") or "unknown"
                    cve       = record.get("cve_id") or record.get("CVE_ID") or None
                    cvss      = float(record.get("cvss") or record.get("severity") or 5.0)
                    vuln_type   = cwe_to_vuln_type(str(cwe))
                    criticality = CVEfixesConverter._cvss_to_criticality(cvss)
                    group_key   = make_group_key("vpp", cve_id=cve, cwe_id=cwe, code=vuln_code)
                    yield build_entry(
                        vuln_type, criticality, vuln_code[:4000], patch_code[:4000],
                        meta={"source": "vpp", "cve_id": cve,
                              "cwe_id": str(cwe), "group_key": group_key},
                    )
                    count += 1

            except Exception as e:
                self.logger.warning(f"Error reading {json_file}: {e}")

        self.logger.info(f"VPP: produced {count} entries")


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA VALIDATOR
# ─────────────────────────────────────────────────────────────────────────────

class SchemaValidator:
    REQUIRED_ROLES = ["system", "user", "assistant"]

    @staticmethod
    def is_valid(entry: Dict) -> bool:
        """Return True if entry matches the target JSONL schema."""
        try:
            messages = entry.get("messages", [])
            if len(messages) != 3:
                return False
            for msg, expected_role in zip(messages, SchemaValidator.REQUIRED_ROLES):
                if msg.get("role") != expected_role:
                    return False
                if not msg.get("content", "").strip():
                    return False
            return True
        except Exception:
            return False

    @classmethod
    def validate_file(cls, path: Path) -> Dict[str, Any]:
        """Validate a JSONL file and return statistics."""
        total = valid = invalid = 0
        seen: set = set()
        duplicates = 0

        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    entry = json.loads(line)
                    if cls.is_valid(entry):
                        # Deduplicate on user content
                        user_content = entry["messages"][1]["content"]
                        if user_content in seen:
                            duplicates += 1
                        else:
                            seen.add(user_content)
                            valid += 1
                    else:
                        invalid += 1
                except json.JSONDecodeError:
                    invalid += 1

        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "duplicates": duplicates,
            "pass_rate": round(valid / total * 100, 1) if total else 0,
        }


# ─────────────────────────────────────────────────────────────────────────────
# MERGER & SPLITTER
# ─────────────────────────────────────────────────────────────────────────────

def merge_and_split(
    processed_paths: List[Path],
    output_dir: Path,
    train_split: float = 0.8,
    val_split: float   = 0.1,
    test_split: float  = 0.1,
    seed: int = 42,
) -> Dict[str, Path]:
    """
    Merge all processed JSONL files, deduplicate, then do GROUP-LEVEL splitting
    so that no CVE ID (or vulnerability pattern group) straddles two splits.
    The _meta field is stripped from final output files.
    """
    assert abs(train_split + val_split + test_split - 1.0) < 1e-6, \
        "Splits must sum to 1.0"

    # ── 1. Load & deduplicate (per user-content fingerprint) ─────────────────
    groups: Dict[str, List[Dict]] = {}   # group_key → list of entries
    seen_user_content: set = set()
    duplicates = 0
    no_meta = 0

    for path in processed_paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if not SchemaValidator.is_valid(entry):
                        continue
                    # Deduplicate on user content (exact-match)
                    key = entry["messages"][1]["content"]
                    if key in seen_user_content:
                        duplicates += 1
                        continue
                    seen_user_content.add(key)
                    # Group by group_key from _meta (fallback: hash of content)
                    meta = entry.get("_meta") or {}
                    group_key = meta.get("group_key") or _code_hash(key)
                    if not meta:
                        no_meta += 1
                    groups.setdefault(group_key, []).append(entry)
                except Exception:
                    pass

    total_entries = sum(len(v) for v in groups.values())
    logger.info(
        f"Loaded {total_entries:,} unique entries across {len(groups):,} groups "
        f"({duplicates} duplicates removed, {no_meta} entries lacked _meta)"
    )

    # ── 2. Shuffle groups (not entries) for reproducibility ──────────────────
    rng = random.Random(seed)
    group_keys = list(groups.keys())
    rng.shuffle(group_keys)

    # ── 3. Assign groups to splits by cumulative entry count ─────────────────
    n_train_target = int(total_entries * train_split)
    n_val_target   = int(total_entries * val_split)

    split_groups: Dict[str, List[str]] = {"train": [], "val": [], "test": []}
    cumulative = 0
    for gk in group_keys:
        n_g = len(groups[gk])
        if cumulative < n_train_target:
            split_groups["train"].append(gk)
        elif cumulative < n_train_target + n_val_target:
            split_groups["val"].append(gk)
        else:
            split_groups["test"].append(gk)
        cumulative += n_g

    # ── 4. Verify zero leakage ────────────────────────────────────────────────
    train_set = set(split_groups["train"])
    val_set   = set(split_groups["val"])
    test_set  = set(split_groups["test"])
    assert train_set.isdisjoint(val_set),  "LEAKAGE: train ∩ val is non-empty!"
    assert train_set.isdisjoint(test_set), "LEAKAGE: train ∩ test is non-empty!"
    assert val_set.isdisjoint(test_set),   "LEAKAGE: val ∩ test is non-empty!"
    logger.info("✅ Zero group leakage confirmed across all splits.")

    # ── 5. Write splits — strip _meta before writing ─────────────────────────
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths = {}
    for split_name, gkeys in split_groups.items():
        entries = [e for gk in gkeys for e in groups[gk]]
        # Shuffle entries within each split
        rng.shuffle(entries)
        out_path = output_dir / f"{split_name}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for entry in entries:
                # Strip _meta — invisible to the model
                clean = {k: v for k, v in entry.items() if k != "_meta"}
                f.write(json.dumps(clean, ensure_ascii=False) + "\n")
        logger.info(
            f"  {split_name:5s}: {len(entries):>6,} entries, "
            f"{len(gkeys):>5,} groups → {out_path}"
        )
        output_paths[split_name] = out_path

    return output_paths


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

CONVERTER_MAP = {
    "synthetic": SyntheticConverter,
    "juliet":    JulietConverter,
    "cvefixes":  CVEfixesConverter,
    "vpp":       VPPConverter,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ouroboros – Dataset Schema Standardizer (Task 1.1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--sources", nargs="+",
        choices=list(CONVERTER_MAP.keys()) + ["all"],
        default=["synthetic"],
        help="Data sources to convert (default: synthetic)",
    )
    parser.add_argument(
        "--raw-dir", type=Path, default=Path("data/raw"),
        help="Directory containing raw datasets (default: data/raw)",
    )
    parser.add_argument(
        "--processed-dir", type=Path, default=Path("data/processed"),
        help="Directory for per-source JSONL output (default: data/processed)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/splits"),
        help="Directory for final train/val/test splits (default: data/splits)",
    )
    parser.add_argument("--train-split", type=float, default=0.8)
    parser.add_argument("--val-split",   type=float, default=0.1)
    parser.add_argument("--test-split",  type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()

    # Expand "all"
    sources = list(CONVERTER_MAP.keys()) if "all" in args.sources else args.sources

    # Validate splits
    total_split = args.train_split + args.val_split + args.test_split
    if abs(total_split - 1.0) > 1e-6:
        raise ValueError(
            f"Splits must sum to 1.0, got {total_split:.3f}. "
            f"Check --train-split, --val-split, --test-split."
        )

    args.processed_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Sources     : {sources}")
    logger.info(f"Raw dir     : {args.raw_dir.resolve()}")
    logger.info(f"Processed   : {args.processed_dir.resolve()}")
    logger.info(f"Output      : {args.output_dir.resolve()}")
    logger.info(f"Splits      : train={args.train_split} val={args.val_split} test={args.test_split}")

    # Run each converter
    processed_paths = []
    for source_name in sources:
        cls = CONVERTER_MAP[source_name]
        converter = cls(raw_dir=args.raw_dir, processed_dir=args.processed_dir)
        out_path = converter.run()
        processed_paths.append(out_path)

    # Merge, deduplicate, split
    logger.info("Merging, deduplicating, and splitting…")
    split_paths = merge_and_split(
        processed_paths=processed_paths,
        output_dir=args.output_dir,
        train_split=args.train_split,
        val_split=args.val_split,
        test_split=args.test_split,
        seed=args.seed,
    )

    # Validate outputs
    logger.info("Validating output files…")
    for split_name, path in split_paths.items():
        stats = SchemaValidator.validate_file(path)
        logger.info(
            f"  {split_name:5s}: {stats['valid']:>6,} valid / {stats['total']:>6,} total "
            f"| pass rate: {stats['pass_rate']}% | duplicates: {stats['duplicates']}"
        )

    logger.info("✅ Schema standardization complete.")


if __name__ == "__main__":
    main()
