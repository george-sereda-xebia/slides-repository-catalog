"""PDF catalog generator that merges native presentation PDFs."""

import io
import logging
from collections import OrderedDict
from pathlib import Path
from typing import List, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from pypdf import PdfReader, PdfWriter


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFGenerator:
    """Generate PDF catalog by merging native presentation PDFs."""

    def __init__(self, output_path: str = "catalog.pdf"):
        self.output_path = output_path
        # Defaults — overridden once we know the slide dimensions
        self.page_width, self.page_height = A4

    def _detect_slide_dimensions(self, presentations: List[Dict]) -> None:
        """Read the first available presentation PDF and adopt its page size."""
        for p in presentations:
            pdf_path = p.get("pdf_path")
            if pdf_path and Path(pdf_path).exists():
                try:
                    reader = PdfReader(pdf_path)
                    if reader.pages:
                        box = reader.pages[0].mediabox
                        self.page_width = float(box.width)
                        self.page_height = float(box.height)
                        logger.info(f"Slide dimensions: {self.page_width:.0f} x {self.page_height:.0f} pt")
                        return
                except Exception as e:
                    logger.warning(f"Could not read dimensions from {pdf_path}: {e}")
        logger.info("No slide PDFs found for dimension detection, using A4")

    def generate_catalog(self, presentations: List[Dict]) -> str:
        """Generate PDF catalog by merging title page, separator pages, and presentation PDFs.

        Args:
            presentations: List of dicts with keys: name, path, pdf_path, slide_count, text

        Returns:
            Path to generated PDF
        """
        logger.info(f"Generating PDF catalog: {self.output_path}")

        # Match page width to the actual slide dimensions
        self._detect_slide_dimensions(presentations)

        writer = PdfWriter()

        # Add title page
        title_pdf = self._generate_title_page_pdf(presentations)
        title_reader = PdfReader(title_pdf)
        for page in title_reader.pages:
            writer.add_page(page)

        # Add each presentation with a separator page
        for idx, presentation in enumerate(presentations, 1):
            pdf_path = presentation.get("pdf_path")
            if not pdf_path or not Path(pdf_path).exists():
                logger.warning(f"Skipping {presentation['name']}: PDF not found")
                continue

            # Add separator page
            separator_pdf = self._generate_separator_page_pdf(presentation, idx, len(presentations))
            separator_reader = PdfReader(separator_pdf)
            for page in separator_reader.pages:
                writer.add_page(page)

            # Add presentation PDF pages, scaling to target width
            try:
                pres_reader = PdfReader(pdf_path)
                for page in pres_reader.pages:
                    pw = float(page.mediabox.width)
                    if abs(pw - self.page_width) > 1:
                        scale = self.page_width / pw
                        page.scale_by(scale)
                    writer.add_page(page)
                logger.info(f"Added {len(pres_reader.pages)} pages from {presentation['name']}")
            except Exception as e:
                logger.error(f"Failed to read PDF {pdf_path}: {e}")

        # Write output
        with open(self.output_path, "wb") as f:
            writer.write(f)

        logger.info(f"PDF generated: {self.output_path}")
        return self.output_path

    def _generate_title_page_pdf(self, presentations: List[Dict]) -> io.BytesIO:
        """Generate a title page with table of contents.

        Args:
            presentations: List of presentation metadata

        Returns:
            BytesIO containing the title page PDF
        """
        page_size = (self.page_width, self.page_height)

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=page_size)

        # Header bar
        c.setFillColor(HexColor("#821C84"))
        c.rect(0, self.page_height - 80, self.page_width, 80, fill=True, stroke=False)

        # Title
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(self.page_width / 2, self.page_height - 55, "Slides Catalog")

        # Summary stats
        total_presentations = len(presentations)
        total_slides = sum(p.get("slide_count", 0) for p in presentations)

        c.setFillColor(HexColor("#333333"))
        c.setFont("Helvetica", 14)
        y = self.page_height - 120
        c.drawCentredString(self.page_width / 2, y, f"{total_presentations} presentations  |  {total_slides} slides total")

        # Table of contents
        y -= 50
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(HexColor("#333333"))
        c.drawString(50, y, "Table of Contents")

        y -= 10
        c.setStrokeColor(HexColor("#821C84"))
        c.setLineWidth(2)
        c.line(50, y, self.page_width - 50, y)

        y -= 30

        # Group presentations by folder
        grouped = OrderedDict()
        for idx, p in enumerate(presentations):
            folder = str(Path(p.get("path", "")).parent)
            if folder == ".":
                folder = "Other"
            grouped.setdefault(folder, []).append((idx, p))

        global_idx = 0
        for folder, items in grouped.items():
            # Check space for folder header + at least one entry
            if y < 100:
                c.showPage()
                c.setPageSize(page_size)
                y = self.page_height - 60

            # Folder section header
            c.setFillColor(HexColor("#821C84"))
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, folder)

            # Thin line under folder header
            y -= 6
            c.setStrokeColor(HexColor("#DDDDDD"))
            c.setLineWidth(0.5)
            c.line(50, y, self.page_width - 50, y)
            y -= 16

            for _, p in items:
                global_idx += 1
                if y < 60:
                    c.showPage()
                    c.setPageSize(page_size)
                    y = self.page_height - 60

                name = p["name"]
                slide_count = p.get("slide_count", 0)

                # Number and name
                c.setFillColor(HexColor("#666666"))
                c.setFont("Helvetica", 9)
                c.drawString(60, y, f"{global_idx}.")
                c.setFillColor(HexColor("#333333"))
                c.setFont("Helvetica", 10)
                c.drawString(80, y, name)

                # Slide count on the right
                c.setFont("Helvetica", 9)
                c.setFillColor(HexColor("#999999"))
                c.drawRightString(self.page_width - 50, y, f"{slide_count} slides")

                y -= 18

            y -= 10  # Extra space between folder groups

        c.save()
        buf.seek(0)
        return buf

    def _generate_separator_page_pdf(self, presentation: Dict, index: int, total: int) -> io.BytesIO:
        """Generate a compact separator strip before each presentation.

        Uses a short custom page height (same A4 width) so it doesn't waste a full page.

        Args:
            presentation: Presentation metadata dict
            index: 1-based index of this presentation
            total: Total number of presentations

        Returns:
            BytesIO containing the separator page PDF
        """
        name = presentation["name"]
        if len(name) > 70:
            name = name[:67] + "..."
        full_path = presentation.get("path", "")
        folder = str(Path(full_path).parent) if full_path else ""
        if folder == ".":
            folder = ""
        slide_count = presentation.get("slide_count", 0)

        # Compact page: same width as slides, short height with padding
        strip_height = 58
        if folder:
            strip_height = 78

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(self.page_width, strip_height))

        # Purple background for the whole strip
        c.setFillColor(HexColor("#821C84"))
        c.rect(0, 0, self.page_width, strip_height, fill=True, stroke=False)

        # Top row: folder name (bold, prominent) + index/slides
        top_y = strip_height - 22
        if folder:
            c.setFillColor(HexColor("#FFFFFF"))
            c.setFont("Helvetica-Bold", 11)
            c.drawString(15, top_y, folder)

            c.setFont("Helvetica", 8)
            c.setFillColor(HexColor("#E0C0E0"))
            c.drawRightString(self.page_width - 15, top_y, f"{index} / {total}  |  {slide_count} slides")

            # Bottom row: presentation name
            c.setFillColor(HexColor("#FFFFFF"))
            c.setFont("Helvetica", 11)
            c.drawString(15, top_y - 20, name)
        else:
            # No folder — single row with name
            c.setFillColor(HexColor("#FFFFFF"))
            c.setFont("Helvetica-Bold", 12)
            c.drawString(15, top_y, name)

            c.setFont("Helvetica", 8)
            c.setFillColor(HexColor("#E0C0E0"))
            c.drawRightString(self.page_width - 15, top_y, f"{index} / {total}  |  {slide_count} slides")

        c.save()
        buf.seek(0)
        return buf


def main():
    """Test PDF generator."""
    generator = PDFGenerator("test_catalog.pdf")
    test_presentations = [
        {
            "name": "Test Presentation.pptx",
            "path": "folder/Test Presentation.pptx",
            "pdf_path": None,
            "slide_count": 10,
            "text": "Sample text",
        }
    ]
    generator.generate_catalog(test_presentations)


if __name__ == "__main__":
    main()
