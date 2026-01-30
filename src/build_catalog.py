"""Main catalog builder orchestrator."""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict

from jinja2 import Environment, FileSystemLoader

from graph_client import GraphClient
from local_client import LocalClient
from slides_renderer import SlidesRenderer


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CatalogBuilder:
    """Main orchestrator for building presentation catalog."""

    def __init__(
        self,
        source_mode: str = "sharepoint",
        tenant_id: str = None,
        client_id: str = None,
        client_secret: str = None,
        sharepoint_hostname: str = None,
        site_path: str = None,
        root_folder_path: str = None,
        local_assets_path: str = None,
        output_dir: str = "site",
    ):
        """Initialize catalog builder.

        Args:
            source_mode: Source mode ('sharepoint' or 'local')
            tenant_id: Azure AD tenant ID (for SharePoint mode)
            client_id: Application (client) ID (for SharePoint mode)
            client_secret: Client secret value (for SharePoint mode)
            sharepoint_hostname: SharePoint hostname (for SharePoint mode)
            site_path: SharePoint site path (for SharePoint mode)
            root_folder_path: Root folder path (for both modes)
            local_assets_path: Path to local assets folder (for local mode, defaults to Reusable_Assets)
            output_dir: Output directory for generated catalog
        """
        self.source_mode = source_mode.lower()
        self.root_folder_path = root_folder_path or ""
        self.output_dir = Path(output_dir)

        # Initialize client based on mode
        if self.source_mode == "local":
            logger.info("Initializing in LOCAL mode")
            self.client = LocalClient(local_assets_path)
            self.site_path = local_assets_path or "Reusable_Assets"
        elif self.source_mode == "sharepoint":
            logger.info("Initializing in SHAREPOINT mode")
            if not all([tenant_id, client_id, client_secret, sharepoint_hostname, site_path]):
                raise ValueError("SharePoint mode requires: tenant_id, client_id, client_secret, sharepoint_hostname, site_path")
            self.client = GraphClient(
                tenant_id, client_id, client_secret, sharepoint_hostname
            )
            self.site_path = site_path
        else:
            raise ValueError(f"Invalid source_mode: {source_mode}. Must be 'sharepoint' or 'local'")

        # Initialize renderer
        assets_dir = self.output_dir / "assets"
        self.renderer = SlidesRenderer(str(assets_dir))

    def clean_output_dir(self):
        """Clean output directory before build."""
        if self.output_dir.exists():
            logger.info(f"Cleaning output directory: {self.output_dir}")
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def discover_presentations(self) -> List[Dict]:
        """Discover all presentations from configured source.

        Returns:
            List of presentation metadata dictionaries
        """
        source_name = "local filesystem" if self.source_mode == "local" else "SharePoint"
        logger.info(f"Discovering presentations from {source_name}...")

        # Authenticate (no-op for local mode)
        self.client.authenticate()

        # Get site and drive IDs (returns path for local mode)
        site_id = self.client.get_site_id(self.site_path)
        drive_id = self.client.get_drive_id(site_id)

        # Find all .pptx files
        pptx_files = self.client.find_pptx_files(drive_id, self.root_folder_path)

        logger.info(f"Discovered {len(pptx_files)} presentations")
        return pptx_files

    def process_presentation(self, file_info: Dict, temp_dir: Path) -> Dict:
        """Download and render a single presentation.

        Args:
            file_info: File metadata from source (SharePoint or local)
            temp_dir: Temporary directory for downloads

        Returns:
            Processed presentation metadata
        """
        presentation_id = file_info["id"]
        name = file_info["name"]

        logger.info(f"Processing: {name}")

        try:
            # Download/copy PPTX to temp directory
            temp_pptx = temp_dir / f"{presentation_id}.pptx"
            self.client.download_file(
                file_info["download_url"], str(temp_pptx)
            )

            # Render slides
            render_result = self.renderer.render_presentation(
                str(temp_pptx), presentation_id
            )

            # Combine metadata
            result = {
                "id": presentation_id,
                "name": name,
                "path": file_info["path"],
                "web_url": file_info["web_url"],
                "modified": file_info["modified"],
                "size": file_info["size"],
                "slides": render_result["slides"],
                "slide_count": render_result["slide_count"],
                "text": render_result.get("text", ""),
                "error": render_result["error"],
            }

            logger.info(
                f"Processed: {name} ({render_result['slide_count']} slides)"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to process {name}: {e}")
            return {
                "id": presentation_id,
                "name": name,
                "path": file_info["path"],
                "web_url": file_info["web_url"],
                "modified": file_info["modified"],
                "size": file_info["size"],
                "slides": [],
                "slide_count": 0,
                "error": str(e),
            }

    def process_all_presentations(
        self, pptx_files: List[Dict]
    ) -> List[Dict]:
        """Process all presentations.

        Args:
            pptx_files: List of file metadata from SharePoint

        Returns:
            List of processed presentation metadata
        """
        logger.info(f"Processing {len(pptx_files)} presentations...")

        presentations = []

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            for idx, file_info in enumerate(pptx_files, start=1):
                logger.info(f"[{idx}/{len(pptx_files)}] Processing...")
                result = self.process_presentation(file_info, temp_path)
                presentations.append(result)

        # Filter out failed presentations
        successful = [p for p in presentations if p["slide_count"] > 0]
        failed = [p for p in presentations if p["slide_count"] == 0]

        logger.info(
            f"Processed: {len(successful)} successful, {len(failed)} failed"
        )

        return presentations

    def generate_html(self, presentations: List[Dict]):
        """Generate HTML catalog.

        Args:
            presentations: List of processed presentations
        """
        logger.info("Generating HTML catalog...")

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("index.html")

        # Prepare context
        context = {
            "presentations": presentations,
            "total_presentations": len(presentations),
            "total_slides": sum(p["slide_count"] for p in presentations),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "sharepoint_site": self.site_path,
            "root_folder": self.root_folder_path,
        }

        # Render template
        html = template.render(context)

        # Write to output
        output_file = self.output_dir / "index.html"
        output_file.write_text(html, encoding="utf-8")

        logger.info(f"Generated: {output_file}")

    def build(self):
        """Build complete catalog."""
        logger.info("=" * 60)
        logger.info("Starting catalog build")
        logger.info("=" * 60)

        start_time = datetime.now()

        try:
            # Clean output directory
            self.clean_output_dir()

            # Discover presentations
            pptx_files = self.discover_presentations()

            if not pptx_files:
                logger.warning("No presentations found!")
                logger.info("Creating empty catalog...")
                self.generate_html([])
                return

            # Process all presentations
            presentations = self.process_all_presentations(pptx_files)

            # Generate HTML
            self.generate_html(presentations)

            # Summary
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info("=" * 60)
            logger.info(f"Build completed in {elapsed:.1f} seconds")
            logger.info(f"Total presentations: {len(presentations)}")
            logger.info(
                f"Total slides: {sum(p['slide_count'] for p in presentations)}"
            )
            logger.info(f"Output: {self.output_dir / 'index.html'}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Build failed: {e}", exc_info=True)
            sys.exit(1)


def main():
    """Main entry point."""
    # Determine source mode
    source_mode = os.getenv("SOURCE_MODE", "sharepoint").lower()

    logger.info(f"Source mode: {source_mode.upper()}")

    if source_mode == "local":
        # Local mode configuration
        local_assets_path = os.getenv("LOCAL_ASSETS_PATH", "Reusable_Assets")
        root_folder_path = os.getenv("ROOT_FOLDER_PATH", "")

        logger.info(f"Local assets path: {local_assets_path}")
        logger.info(f"Root folder filter: {root_folder_path or '(none - all folders)'}")

        # Create builder for local mode
        builder = CatalogBuilder(
            source_mode="local",
            local_assets_path=local_assets_path,
            root_folder_path=root_folder_path,
        )

    elif source_mode == "sharepoint":
        # SharePoint mode configuration
        tenant_id = os.getenv("TENANT_ID")
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")
        sharepoint_hostname = os.getenv("SHAREPOINT_HOSTNAME")
        site_path = os.getenv("SITE_PATH")
        root_folder_path = os.getenv("ROOT_FOLDER_PATH")

        # Validate configuration
        missing = []
        config = {
            "TENANT_ID": tenant_id,
            "CLIENT_ID": client_id,
            "CLIENT_SECRET": client_secret,
            "SHAREPOINT_HOSTNAME": sharepoint_hostname,
            "SITE_PATH": site_path,
            "ROOT_FOLDER_PATH": root_folder_path,
        }

        for key, value in config.items():
            if not value:
                missing.append(key)

        if missing:
            logger.error(f"Missing required environment variables for SharePoint mode: {', '.join(missing)}")
            logger.error("Please set all required variables:")
            for key in missing:
                logger.error(f"  export {key}='...'")
            logger.error("\nOr switch to local mode:")
            logger.error("  export SOURCE_MODE='local'")
            sys.exit(1)

        # Create builder for SharePoint mode
        builder = CatalogBuilder(
            source_mode="sharepoint",
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            sharepoint_hostname=sharepoint_hostname,
            site_path=site_path,
            root_folder_path=root_folder_path,
        )

    else:
        logger.error(f"Invalid SOURCE_MODE: {source_mode}")
        logger.error("Valid values: 'sharepoint' or 'local'")
        sys.exit(1)

    # Build catalog
    builder.build()


if __name__ == "__main__":
    main()
