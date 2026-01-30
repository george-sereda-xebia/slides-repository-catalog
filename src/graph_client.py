"""Microsoft Graph API client for SharePoint access."""

import os
import logging
from typing import Dict, List, Optional
from urllib.parse import quote

import msal
import requests


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphClient:
    """Client for Microsoft Graph API operations."""

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        sharepoint_hostname: str,
    ):
        """Initialize Graph API client.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Application (client) ID
            client_secret: Client secret value
            sharepoint_hostname: SharePoint hostname (e.g., xebiagroup.sharepoint.com)
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.sharepoint_hostname = sharepoint_hostname
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.access_token: Optional[str] = None

    def authenticate(self) -> str:
        """Authenticate using client credentials flow.

        Returns:
            Access token

        Raises:
            Exception: If authentication fails
        """
        authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=authority,
            client_credential=self.client_secret,
        )

        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )

        if "access_token" not in result:
            error = result.get("error")
            error_desc = result.get("error_description")
            raise Exception(f"Authentication failed: {error} - {error_desc}")

        self.access_token = result["access_token"]
        logger.info("Successfully authenticated with Microsoft Graph API")
        return self.access_token

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authorization.

        Returns:
            Headers dictionary
        """
        if not self.access_token:
            self.authenticate()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    def get_site_id(self, site_path: str) -> str:
        """Get SharePoint site ID from site path.

        Args:
            site_path: Site path (e.g., /sites/allxsd)

        Returns:
            Site ID
        """
        # Remove leading slash if present
        site_path = site_path.lstrip("/")

        url = f"{self.base_url}/sites/{self.sharepoint_hostname}:/{site_path}"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()

        site_id = response.json()["id"]
        logger.info(f"Found site ID: {site_id}")
        return site_id

    def get_drive_id(self, site_id: str) -> str:
        """Get default document library drive ID for site.

        Args:
            site_id: SharePoint site ID

        Returns:
            Drive ID
        """
        url = f"{self.base_url}/sites/{site_id}/drive"
        response = requests.get(url, headers=self._get_headers())
        response.raise_for_status()

        drive_id = response.json()["id"]
        logger.info(f"Found drive ID: {drive_id}")
        return drive_id

    def list_folder_contents(
        self, drive_id: str, folder_path: str
    ) -> List[Dict]:
        """List contents of a folder in SharePoint.

        Args:
            drive_id: Drive ID
            folder_path: Folder path relative to drive root

        Returns:
            List of items (files and folders)
        """
        # Encode path for URL
        encoded_path = quote(folder_path)
        url = f"{self.base_url}/drives/{drive_id}/root:/{encoded_path}:/children"

        items = []
        while url:
            response = requests.get(url, headers=self._get_headers())
            response.raise_for_status()

            data = response.json()
            items.extend(data.get("value", []))

            # Handle pagination
            url = data.get("@odata.nextLink")

        logger.info(f"Found {len(items)} items in {folder_path}")
        return items

    def find_pptx_files(
        self, drive_id: str, root_folder_path: str
    ) -> List[Dict]:
        """Recursively find all .pptx files in folder tree.

        Args:
            drive_id: Drive ID
            root_folder_path: Root folder path to start search

        Returns:
            List of .pptx file metadata dictionaries
        """
        pptx_files = []

        def traverse_folder(folder_path: str):
            try:
                items = self.list_folder_contents(drive_id, folder_path)

                for item in items:
                    # Check if it's a folder
                    if "folder" in item:
                        # Recursively traverse subfolder
                        subfolder_path = f"{folder_path}/{item['name']}"
                        traverse_folder(subfolder_path)

                    # Check if it's a .pptx file
                    elif "file" in item:
                        name = item["name"]
                        if name.lower().endswith(".pptx"):
                            file_info = {
                                "id": item["id"],
                                "name": name,
                                "path": folder_path,
                                "full_path": f"{folder_path}/{name}",
                                "web_url": item.get("webUrl", ""),
                                "modified": item.get("lastModifiedDateTime", ""),
                                "size": item.get("size", 0),
                                "download_url": item.get("@microsoft.graph.downloadUrl", ""),
                            }
                            pptx_files.append(file_info)
                            logger.info(f"Found: {file_info['full_path']}")

            except Exception as e:
                logger.error(f"Error traversing {folder_path}: {e}")

        logger.info(f"Starting recursive search in: {root_folder_path}")
        traverse_folder(root_folder_path)
        logger.info(f"Total .pptx files found: {len(pptx_files)}")

        return pptx_files

    def download_file(self, download_url: str, output_path: str) -> None:
        """Download file from SharePoint.

        Args:
            download_url: Download URL from file metadata
            output_path: Local path to save file
        """
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Downloaded: {output_path}")


def main():
    """Test the Graph client."""
    # Load credentials from environment
    tenant_id = os.getenv("TENANT_ID")
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    sharepoint_hostname = os.getenv("SHAREPOINT_HOSTNAME")
    site_path = os.getenv("SITE_PATH")
    root_folder_path = os.getenv("ROOT_FOLDER_PATH")

    if not all([tenant_id, client_id, client_secret, sharepoint_hostname, site_path, root_folder_path]):
        raise ValueError("Missing required environment variables")

    # Initialize client
    client = GraphClient(tenant_id, client_id, client_secret, sharepoint_hostname)

    # Authenticate
    client.authenticate()

    # Get site and drive IDs
    site_id = client.get_site_id(site_path)
    drive_id = client.get_drive_id(site_id)

    # Find all .pptx files
    pptx_files = client.find_pptx_files(drive_id, root_folder_path)

    print(f"\nFound {len(pptx_files)} presentations:")
    for file in pptx_files[:5]:  # Show first 5
        print(f"  - {file['full_path']}")


if __name__ == "__main__":
    main()
