"""
Ouroboros SDK v2.0.0
Production Security Automation Platform

Install:  pip install ouroboros-sdk
Setup:    ouroboros init
Scan:     ouroboros scan --repo https://github.com/owner/repo

Python API:
    from ouroboros import Ouroboros
    ouro = Ouroboros()
    result = await ouro.scan("https://github.com/owner/repo")
"""
__version__ = "2.0.0"

from .core import Ouroboros
from .cli import cli

__all__ = ["Ouroboros", "cli", "__version__"]
