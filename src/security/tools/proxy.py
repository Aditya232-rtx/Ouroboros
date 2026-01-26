#!/usr/bin/env python3
"""
Proxy Manager - Interact with Caido/Burp via GraphQL/API
Ported from Strix for Ouroboros Red Agent.
"""

import os
import time
import base64
import requests
import logging
from typing import Dict, Any, List, Optional
try:
    from gql import Client, gql
    from gql.transport.requests import RequestsHTTPTransport
except ImportError:
    Client = Any
    gql = Any
    RequestsHTTPTransport = Any

logger = logging.getLogger(__name__)

CAIDO_PORT = 8080 # Default Caido port

class ProxyManager:
    """Manages interaction with interception proxies (Caido)"""
    
    def __init__(self, auth_token: str | None = None):
        if not Client:
             self.available = False
             logger.warning("GQL not installed. Proxy features disabled.")
             return

        host = "127.0.0.1"
        self.base_url = f"http://{host}:{CAIDO_PORT}/graphql"
        self.proxies = {
            "http": f"http://{host}:{CAIDO_PORT}",
            "https": f"http://{host}:{CAIDO_PORT}",
        }
        self.auth_token = auth_token or os.getenv("CAIDO_API_TOKEN", "default_token")
        self.available = True
        
    def _get_client(self) -> Client:
        if not self.available: return None
        transport = RequestsHTTPTransport(
            url=self.base_url, headers={"Authorization": f"Bearer {self.auth_token}"}
        )
        return Client(transport=transport, fetch_schema_from_transport=False)

    def send_through_proxy(self, method: str, url: str, headers: Dict = None, body: str = None) -> Dict:
        """Send a request through the configured proxy"""
        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=body,
                proxies=self.proxies,
                verify=False,
                timeout=10
            )
            return {
                "status": resp.status_code,
                "length": len(resp.content),
                "time": resp.elapsed.total_seconds()
            }
        except Exception as e:
            return {"error": str(e)}

    def list_requests(self, limit: int = 10) -> List[Dict]:
        """List captured requests from Caido"""
        if not self.available: return []
        
        query = gql("""
            query GetRequests($limit: Int) {
                requestsByOffset(limit: $limit, offset: 0, order: {by: CREATED_AT, ordering: DESC}) {
                    edges {
                        node {
                            id method host path query createdAt 
                            response { statusCode length }
                        }
                    }
                }
            }
        """)
        
        try:
            result = self._get_client().execute(query, variable_values={"limit": limit})
            data = result.get("requestsByOffset", {})
            return [edge["node"] for edge in data.get("edges", [])]
        except Exception as e:
            logger.error(f"Failed to list requests: {e}")
            return []

    def get_latest_traffic(self) -> str:
        """Get a summary of latest traffic for analysis"""
        reqs = self.list_requests(5)
        summary = "Latest Proxy Traffic:\n"
        for r in reqs:
            summary += f"- {r['method']} {r['host']}{r['path']} ({r.get('response', {}).get('statusCode')})\n"
        return summary
