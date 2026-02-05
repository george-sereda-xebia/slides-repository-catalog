"""PDF catalog generator with thumbnails and searchable text."""

import os
import logging
from pathlib import Path
from typing import List, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from PIL import Image


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generate PDF catalog with slide thumbnails."""

    def __init__(self, output_path: str = "catalog.pdf"):
        """Initialize PDF generator.

        Args:
            output_path: Output PDF file path
        """
        self.output_path = output_path
        self.page_width, self.page_height = A4

    def generate_catalog(self, presentations: List[Dict]) -> str:
        """Generate PDF catalog from presentations.

        Args:
            presentations: List of presentation metadata

        Returns:
            Path to generated PDF
        """
        logger.info(f"Generating PDF catalog: {self.output_path}")

        c = canvas.Canvas(self.output_path, pagesize=A4)

        # Generate title page
        self._generate_title_page(c, presentations)
        c.showPage()

        # Collect all slides from all presentations
        all_slides = []
        for presentation in presentations:
            for slide_path in presentation.get('slides', []):
                all_slides.append({
                    'path': slide_path,
                    'presentation_name': presentation['name'],
                    'presentation_path': presentation['path'],
                    'text': presentation.get('text', ''),
                })

        # Generate pages with 2 slides each
        logger.info(f"Generating pages for {len(all_slides)} total slides")
        self._generate_slides_pages(c, all_slides)

        # Save PDF
        c.save()
        logger.info(f"✅ PDF generated: {self.output_path}")
        return self.output_path

    def _generate_title_page(self, c: canvas.Canvas, presentations: List[Dict]):
        """Generate title page with summary."""
        # Title
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(self.page_width / 2, self.page_height - 100, "Slides Catalog")

        # Summary
        c.setFont("Helvetica", 14)
        total_presentations = len(presentations)
        total_slides = sum(p.get('slide_count', 0) for p in presentations)

        y = self.page_height - 180
        c.drawCentredString(self.page_width / 2, y, f"{total_presentations} presentations")
        c.drawCentredString(self.page_width / 2, y - 25, f"{total_slides} slides total")

        # Invisible text for search (catalog metadata)
        c.setFillColor(HexColor("#FFFFFF"))  # White text (invisible)
        c.setFont("Helvetica", 1)
        search_text = f"Slides Repository Catalog. Total: {total_presentations} presentations, {total_slides} slides."
        c.drawString(10, 10, search_text)

    def _generate_slides_pages(self, c: canvas.Canvas, all_slides: List[Dict]):
        """Generate pages with 2 slides each, regardless of presentation.

        Args:
            c: ReportLab canvas
            all_slides: List of slide dictionaries with 'path', 'presentation_name', 'presentation_path'
        """
        slides_per_page = 2
        total_pages = (len(all_slides) + slides_per_page - 1) // slides_per_page

        for page_idx in range(total_pages):
            start_idx = page_idx * slides_per_page
            end_idx = min(start_idx + slides_per_page, len(all_slides))
            page_slides = all_slides[start_idx:end_idx]

            # Simple header
            c.setFillColor(HexColor("#821C84"))
            c.rect(0, self.page_height - 40, self.page_width, 40, fill=True, stroke=False)
            c.setFillColor(HexColor("#FFFFFF"))
            c.setFont("Helvetica-Bold", 14)
            c.drawString(20, self.page_height - 25, f"Slides Catalog - Page {page_idx + 1}/{total_pages}")

            # Add slides
            self._add_slides_with_info(c, page_slides, start_idx)

            # Add invisible searchable text for slides on this page
            self._add_hidden_text(c, page_slides)

            c.showPage()

    def _add_slides_with_info(self, c: canvas.Canvas, slides: List[Dict], start_idx: int):
        """Add slides with presentation info above each slide.

        Args:
            c: ReportLab canvas
            slides: List of slide dictionaries (max 2)
            start_idx: Starting index for numbering
        """
        slide_width = 480
        slide_height = 270  # 16:9 aspect ratio
        margin_x = (self.page_width - slide_width) / 2
        start_y = self.page_height - 60
        spacing = 15
        text_height = 24  # Space for 2 lines of text above slide

        for idx, slide_info in enumerate(slides):
            slide_path = slide_info['path']
            if not os.path.exists(slide_path):
                logger.warning(f"Slide not found: {slide_path}")
                continue

            y = start_y - idx * (slide_height + spacing + text_height + 10)

            try:
                # Draw slide info ABOVE the slide
                c.setFillColor(HexColor("#333333"))
                c.setFont("Helvetica-Bold", 9)
                c.drawString(margin_x, y, f"Slide {start_idx + idx + 1}: {slide_info['presentation_name'][:60]}")
                c.setFont("Helvetica", 8)
                c.setFillColor(HexColor("#666666"))
                c.drawString(margin_x, y - 12, f"📁 {slide_info['presentation_path'][:80]}")

                # Draw border below text
                slide_y = y - text_height
                c.setStrokeColor(HexColor("#CCCCCC"))
                c.setLineWidth(1)
                c.rect(margin_x - 2, slide_y - slide_height - 2, slide_width + 4, slide_height + 4,
                       fill=False, stroke=True)

                # Draw image
                c.drawImage(
                    slide_path,
                    margin_x, slide_y - slide_height,
                    width=slide_width,
                    height=slide_height,
                    preserveAspectRatio=True
                )

            except Exception as e:
                logger.error(f"Failed to add slide {slide_path}: {e}")

    def _add_hidden_text(self, c: canvas.Canvas, slides: List[Dict]):
        """Add invisible searchable text for Ctrl+F search.

        Args:
            c: ReportLab canvas
            slides: List of slide dictionaries on this page
        """
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica", 1)

        # Collect unique texts (avoid duplicating if both slides are from the same presentation)
        seen = set()
        y_pos = 10
        for slide_info in slides:
            text = slide_info.get('text', '')
            name = slide_info.get('presentation_name', '')
            key = name
            if key in seen or not text:
                continue
            seen.add(key)

            searchable = f"FILE: {name} PATH: {slide_info.get('presentation_path', '')} CONTENT: {text}"
            max_chars = 500
            for i in range(0, len(searchable), max_chars):
                chunk = searchable[i:i + max_chars]
                c.drawString(10, y_pos, chunk)
                y_pos += 2


def main():
    """Test PDF generator."""
    from local_client import LocalClient
    from slides_renderer import SlidesRenderer

    # Initialize components
    client = LocalClient("Reusable_Assets")
    renderer = SlidesRenderer("output")

    # Discover presentations
    presentations = client.find_pptx_files()
    logger.info(f"Found {len(presentations)} presentations")

    # Process first presentation as test
    if presentations:
        test_file = presentations[0]
        logger.info(f"Testing with: {test_file['name']}")

        # Render slides
        result = renderer.render_presentation(test_file['download_url'], test_file['id'])

        # Add metadata
        test_file.update(result)

        # Generate PDF
        generator = PDFGenerator("test_catalog.pdf")
        generator.generate_catalog([test_file])


if __name__ == "__main__":
    main()
