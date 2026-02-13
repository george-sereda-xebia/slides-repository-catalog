"""Build PDF catalog from input folder."""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from local_client import LocalClient
from slides_renderer import SlidesRenderer
from pdf_generator import PDFGenerator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def build_catalog(
    assets_path: str = "input",
    output_pdf: str = "CATALOG.pdf",
):
    """Build PDF catalog from presentations.

    Args:
        assets_path: Path to folder with presentations
        output_pdf: Output PDF file path
    """
    logger.info("=" * 60)
    logger.info("Building PDF Catalog")
    logger.info("=" * 60)

    start_time = datetime.now()

    # Initialize components
    client = LocalClient(assets_path)
    renderer = SlidesRenderer("temp_slides")
    pdf_gen = PDFGenerator(output_pdf)

    # Discover presentations
    logger.info("Discovering presentations...")
    pptx_files = client.find_pptx_files()

    logger.info(f"Found {len(pptx_files)} presentations")

    if not pptx_files:
        logger.warning("No presentations found!")
        sys.exit(1)

    # Process presentations
    presentations = []

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for idx, file_info in enumerate(pptx_files, 1):
            logger.info(f"[{idx}/{len(pptx_files)}] Processing: {file_info['name']}")

            try:
                # Copy file to temp
                temp_pptx = temp_path / f"{file_info['id']}.pptx"
                client.download_file(file_info['download_url'], str(temp_pptx))

                # Convert to PDF and extract metadata
                render_result = renderer.render_presentation(
                    str(temp_pptx), file_info['id']
                )

                if not render_result["success"]:
                    logger.warning(f"Skipping {file_info['name']}: {render_result['error']}")
                    continue

                presentation = {
                    "id": file_info["id"],
                    "name": file_info["name"],
                    "path": file_info["full_path"],
                    "pdf_path": render_result["pdf_path"],
                    "slide_count": render_result["slide_count"],
                    "text": render_result.get("text", ""),
                }

                presentations.append(presentation)

            except Exception as e:
                logger.error(f"Failed to process {file_info['name']}: {e}")
                continue

    if not presentations:
        logger.error("No presentations were successfully processed!")
        sys.exit(1)

    # Generate merged PDF catalog
    logger.info("Generating PDF catalog...")
    pdf_path = pdf_gen.generate_catalog(presentations)

    # Cleanup temp slides
    if Path("temp_slides").exists():
        shutil.rmtree("temp_slides")

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    total_slides = sum(p["slide_count"] for p in presentations)
    logger.info("=" * 60)
    logger.info(f"Build completed in {elapsed:.1f} seconds")
    logger.info(f"Presentations: {len(presentations)}")
    logger.info(f"Total slides: {total_slides}")
    logger.info(f"Output: {pdf_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    build_catalog()
