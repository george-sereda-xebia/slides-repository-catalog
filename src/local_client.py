"""Local filesystem client for presentations access."""

import os
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timezone


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalClient:
    """Client for local filesystem operations."""

    # Default local assets folder
    DEFAULT_ASSETS_FOLDER = "Reusable_Assets"

    def __init__(self, root_path: str = None):
        """Initialize local filesystem client.

        Args:
            root_path: Root path to assets folder (optional, defaults to Reusable_Assets)
        """
        if root_path is None:
            # Use default relative to current working directory
            root_path = self.DEFAULT_ASSETS_FOLDER

        self.root_path = Path(root_path).resolve()

        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")

        if not self.root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {self.root_path}")

        logger.info(f"Local client initialized with root: {self.root_path}")

    def authenticate(self):
        """No-op for local client (compatibility with GraphClient interface)."""
        logger.info("Local mode - no authentication needed")

    def get_site_id(self, site_path: str) -> str:
        """Return local path (compatibility with GraphClient interface).

        Args:
            site_path: Not used in local mode

        Returns:
            String representation of root path
        """
        return str(self.root_path)

    def get_drive_id(self, site_id: str) -> str:
        """Return local path (compatibility with GraphClient interface).

        Args:
            site_id: Not used in local mode

        Returns:
            String representation of root path
        """
        return str(self.root_path)

    def find_pptx_files(
        self, drive_id: str = None, root_folder_path: str = None
    ) -> List[Dict]:
        """Recursively find all .pptx files in local folder tree.

        Args:
            drive_id: Not used in local mode (compatibility)
            root_folder_path: Subfolder path relative to root (optional)

        Returns:
            List of .pptx file metadata dictionaries
        """
        pptx_files = []

        # Determine search path
        if root_folder_path:
            search_path = self.root_path / root_folder_path
        else:
            search_path = self.root_path

        if not search_path.exists():
            logger.warning(f"Search path does not exist: {search_path}")
            return []

        logger.info(f"Starting recursive search in: {search_path}")

        # Recursively find all .pptx files
        for pptx_file in search_path.rglob("*.pptx"):
            # Skip temporary/hidden files
            if pptx_file.name.startswith("~") or pptx_file.name.startswith("."):
                logger.debug(f"Skipping temporary file: {pptx_file}")
                continue

            # Get file stats
            stat = pptx_file.stat()

            # Calculate relative path from root
            try:
                relative_path = pptx_file.parent.relative_to(self.root_path)
                folder_path = str(relative_path) if str(relative_path) != "." else ""
            except ValueError:
                folder_path = ""

            # Build file info (matching GraphClient structure)
            file_info = {
                "id": self._generate_file_id(pptx_file),
                "name": pptx_file.name,
                "path": folder_path,
                "full_path": f"{folder_path}/{pptx_file.name}" if folder_path else pptx_file.name,
                "web_url": f"file://{pptx_file.resolve()}",  # Local file URL
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "size": stat.st_size,
                "download_url": str(pptx_file.resolve()),  # Local path for "download"
                "local_path": str(pptx_file.resolve()),  # Additional field for local mode
            }

            pptx_files.append(file_info)
            logger.info(f"Found: {file_info['full_path']}")

        logger.info(f"Total .pptx files found: {len(pptx_files)}")
        return pptx_files

    def download_file(self, download_url: str, output_path: str) -> None:
        """Copy file from local filesystem.

        Args:
            download_url: Local file path (from file metadata)
            output_path: Destination path
        """
        source_path = Path(download_url)

        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Create output directory
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Copy file
        import shutil
        shutil.copy2(source_path, output_path)

        logger.info(f"Copied: {source_path.name} -> {output_path}")

    def _generate_file_id(self, file_path: Path) -> str:
        """Generate unique file ID from path.

        Args:
            file_path: Path to file

        Returns:
            Unique identifier based on relative path
        """
        try:
            relative = file_path.relative_to(self.root_path)
            # Use relative path as ID (replace separators with underscores)
            file_id = str(relative).replace("/", "_").replace("\\", "_").replace(".pptx", "")
            return file_id
        except ValueError:
            # Fallback to filename without extension
            return file_path.stem


def main():
    """Test the local client."""
    # Initialize client
    client = LocalClient()

    # Authenticate (no-op)
    client.authenticate()

    # Get "site" and "drive" IDs (returns root path)
    site_id = client.get_site_id("")
    drive_id = client.get_drive_id(site_id)

    print(f"Root path: {drive_id}")

    # Find all .pptx files
    pptx_files = client.find_pptx_files(drive_id, "")

    print(f"\nFound {len(pptx_files)} presentations:")
    for file in pptx_files[:10]:  # Show first 10
        print(f"  - {file['full_path']} ({file['size']:,} bytes)")


if __name__ == "__main__":
    main()
