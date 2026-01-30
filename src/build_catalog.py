"""Build PDF catalog from Reusable_Assets folder."""

import os
import sys
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

from local_client import LocalClient
from slides_renderer import SlidesRenderer
from pdf_generator import PDFGenerator


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def build_catalog(
    assets_path: str = "Reusable_Assets",
    output_pdf: str = "catalog.pdf",
    test_mode: bool = False,
    max_slides: int = 5
):
    """Build PDF catalog from presentations.

    Args:
        assets_path: Path to folder with presentations
        output_pdf: Output PDF file path
        test_mode: If True, process only first presentation with limited slides
        max_slides: Maximum slides to include in test mode
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
    total_slides_collected = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        for idx, file_info in enumerate(pptx_files, 1):
            # Test mode: stop when we have enough slides
            if test_mode and total_slides_collected >= max_slides:
                logger.info(f"🧪 TEST MODE: Collected {total_slides_collected} slides, stopping")
                break

            logger.info(f"[{idx}/{len(pptx_files)}] Processing: {file_info['name']}")

            try:
                # Copy file to temp
                temp_pptx = temp_path / f"{file_info['id']}.pptx"
                client.download_file(file_info['download_url'], str(temp_pptx))

                # Render slides and extract text
                render_result = renderer.render_presentation(
                    str(temp_pptx), file_info['id']
                )

                # Combine metadata
                slides = render_result["slides"]
                total_slides_collected += len(slides)

                presentation = {
                    "id": file_info["id"],
                    "name": file_info["name"],
                    "path": file_info["full_path"],
                    "slides": slides,
                    "slide_count": len(slides),
                    "text": render_result.get("text", ""),
                }

                presentations.append(presentation)

            except Exception as e:
                logger.error(f"Failed to process {file_info['name']}: {e}")

    # Generate PDF
    logger.info("Generating PDF...")
    pdf_path = pdf_gen.generate_catalog(presentations)

    # Cleanup temp slides
    if Path("temp_slides").exists():
        shutil.rmtree("temp_slides")

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info(f"✅ Build completed in {elapsed:.1f} seconds")
    logger.info(f"Presentations: {len(presentations)}")
    logger.info(f"Output: {pdf_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    build_catalog()
