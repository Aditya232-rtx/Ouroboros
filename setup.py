"""
setup.py — Fallback for ``pip install .`` without Poetry.

This lets users install Ouroboros SDK with just:
    pip install .
    pip install ouroboros_sdk-*.whl
    pip install ouroboros_sdk-*.tar.gz

Poetry users can continue using ``poetry install``.
"""

from setuptools import setup, find_packages
from pathlib import Path

long_description = ""
readme = Path("README.md")
if readme.exists():
    long_description = readme.read_text(encoding="utf-8")

setup(
    name="ouroboros-sdk",
    version="1.1.0",
    description="Production Security Automation: ANY Git repo → Fixes + PRs + Docs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Ouroboros Team",
    author_email="team@ouroboros.ai",
    license="Apache-2.0",
    url="https://github.com/Aditya232-rtx/Ouroboros",
    python_requires=">=3.11",
    # Bundle ALL packages needed for the full pipeline
    packages=find_packages(include=["ouroboros", "ouroboros.*", "src", "src.*", "config", "config.*"]),
    # Include Jinja2 templates + example config
    package_data={
        "": ["templates/*.j2", "config.example.yaml"],
    },
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "ouroboros=ouroboros.cli:cli",
        ],
    },
    install_requires=[
        # ── Core framework ──
        "langgraph>=1.0.0",
        "langchain>=1.0.0",
        "langchain-core>=1.0.0",
        "langchain-community>=0.4.0",
        "ollama>=0.6.0",
        # ── Scanning ──
        "semgrep>=1.45.0",
        # ── GitHub ──
        "PyGithub>=2.3.0",
        "gitpython>=3.1.40",
        # ── Templating & CLI ──
        "Jinja2>=3.1.2",
        "click>=8.1.7",
        "PyYAML>=6.0.1",
        "rich>=13.0.0",
        # ── Data & storage ──
        "redis>=5.0.1",
        "psycopg2-binary>=2.9.9",
        "SQLAlchemy>=2.0.0",
        # ── PDF / reporting ──
        "reportlab>=4.0.8",
        # ── Infrastructure ──
        "docker>=7.0.0",
        # ── Pydantic ──
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "python-dotenv>=1.0.0",
        # ── Resilience ──
        "tenacity>=9.0.0",
        # ── Security / crypto ──
        "cryptography>=42.0.0",
        "python-jose>=3.5.0",
        "passlib>=1.7.4",
        "argon2-cffi>=21.0.0",
        # ── HTTP ──
        "requests>=2.31.0",
        "httpx>=0.24.0",
        # ── Web framework ──
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "python-multipart>=0.0.6",
        # ── Monitoring ──
        "prometheus-client>=0.17.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
)
