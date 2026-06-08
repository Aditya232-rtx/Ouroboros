"""Integrations module for external services"""
from src.integrations.github_api import github_client, GitHubClient
from src.integrations.google_workspace_mcp import google_workspace_client, GoogleWorkspaceClient

__all__ = [
    "github_client",
    "GitHubClient",
    "google_workspace_client",
    "GoogleWorkspaceClient"
]
