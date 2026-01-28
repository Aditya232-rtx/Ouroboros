"""Integrations module for external services"""
from src.integrations.github_api import github_client, GitHubClient
from src.integrations.google_workspace_mcp import google_workspace_mcp, GoogleWorkspaceMCP
from src.integrations.opa_client import opa_client, OPAClient
from src.integrations.immudb_client import immudb_client, ImmudbClient

__all__ = [
    "github_client",
    "GitHubClient",
    "google_workspace_mcp",
    "GoogleWorkspaceMCP",
    "opa_client",
    "OPAClient",
    "immudb_client",
    "ImmudbClient"
]
