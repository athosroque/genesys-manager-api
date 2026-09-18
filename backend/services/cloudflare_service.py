import httpx
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

class CloudflareAPIError(Exception):
    """Exception raised for errors in the Cloudflare API."""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []


class CloudflareService:
    def __init__(self):
        self.api_token = settings.CLOUDFLARE_API_TOKEN
        self.account_id = settings.CLOUDFLARE_ACCOUNT_ID
        self.zone_id = settings.CLOUDFLARE_ZONE_ID
        self.base_url = "https://api.cloudflare.com/client/v4"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Base method for making requests to the Cloudflare API."""
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=self.headers, **kwargs)
            
            data = response.json()
            if not response.is_success or not data.get("success", False):
                errors = data.get("errors", [])
                error_msg = errors[0].get("message") if errors else f"HTTP {response.status_code}"
                logger.error(f"Cloudflare API Error ({method} {endpoint}): {error_msg}")
                raise CloudflareAPIError(f"Cloudflare API request failed: {error_msg}", errors)
            
            return data.get("result")

    async def verify_token(self) -> Dict[str, Any]:
        """Verifies if the current API token is valid."""
        return await self._request("GET", "/user/tokens/verify")

    async def list_tunnels(self) -> List[Dict[str, Any]]:
        """Lists all Zero Trust Tunnels in the account."""
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID is not configured.")
        
        endpoint = f"/accounts/{self.account_id}/cfd_tunnel"
        return await self._request("GET", endpoint)

    async def get_tunnel_details(self, tunnel_id: str) -> Dict[str, Any]:
        """Gets details of a specific tunnel."""
        if not self.account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID is not configured.")
        
        endpoint = f"/accounts/{self.account_id}/cfd_tunnel/{tunnel_id}"
        return await self._request("GET", endpoint)

    async def list_dns_records(self, type: Optional[str] = None, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists DNS records for the configured zone."""
        if not self.zone_id:
            raise ValueError("CLOUDFLARE_ZONE_ID is not configured.")
        
        endpoint = f"/zones/{self.zone_id}/dns_records"
        params = {}
        if type: params["type"] = type
        if name: params["name"] = name
            
        return await self._request("GET", endpoint, params=params)

cloudflare_service = CloudflareService()
