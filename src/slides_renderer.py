"""PowerPoint slides renderer using LibreOffice headless."""

import os
import logging
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict

from pptx import Presentation


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlidesRenderer:
    """Renderer for converting PPTX slides to PNG images."""

    def __init__(self, output_dir: str):
        """Initialize slides renderer.

        Args:
            output_dir: Directory to store rendered slides
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def find_libreoffice(self) -> str:
        """Find LibreOffice executable path.

        Returns:
            Path to soffice executable

        Raises:
            RuntimeError: If LibreOffice not found
        """
        # Common paths for different platforms
        paths = [
            "soffice",  # In PATH
            "/usr/bin/soffice",  # Linux
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",  # macOS
            "C:\\Program Files\\LibreOffice\\program\\soffice.exe",  # Windows
            "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",  # Windows 32-bit
        ]

        for path in paths:
            if shutil.which(path) or os.path.exists(path):
                logger.info(f"Found LibreOffice at: {path}")
                return path

        raise RuntimeError(
            "LibreOffice not found. Please install LibreOffice:\n"
            "  macOS: brew install libreoffice\n"
            "  Ubuntu: sudo apt-get install libreoffice\n"
            "  Windows: Download from https://www.libreoffice.org/"
        )

    def render_pptx(self, pptx_path: str, presentation_id: str) -> List[str]:
        """Render PPTX slides to PNG images.

        Args:
            pptx_path: Path to PPTX file
            presentation_id: Unique ID for this presentation

        Returns:
            List of paths to rendered PNG files

        Raises:
            subprocess.CalledProcessError: If conversion fails
        """
        logger.info(f"Rendering: {pptx_path}")

        # Create output directory for this presentation
        presentation_dir = self.output_dir / presentation_id
        presentation_dir.mkdir(parents=True, exist_ok=True)

        # Create temporary directory for LibreOffice output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Find LibreOffice
            soffice = self.find_libreoffice()

            # Convert PPTX to PNG using LibreOffice headless
            # LibreOffice will create one PNG per slide
            cmd = [
                soffice,
                "--headless",
                "--convert-to",
                "png",
                "--outdir",
                str(temp_path),
                pptx_path,
            ]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes timeout
                    check=True,
                )
                logger.debug(f"LibreOffice output: {result.stdout}")

            except subprocess.CalledProcessError as e:
                logger.error(f"LibreOffice conversion failed: {e.stderr}")
                raise
            except subprocess.TimeoutExpired:
                logger.error("LibreOffice conversion timed out (5 minutes)")
                raise

            # LibreOffice creates files named like: presentation.png, presentation-1.png, etc.
            # Find all generated PNG files
            temp_files = sorted(temp_path.glob("*.png"))

            if not temp_files:
                logger.warning(f"No PNG files generated for {pptx_path}")
                return []

            # Move and rename files to presentation directory
            output_files = []
            for idx, temp_file in enumerate(temp_files, start=1):
                output_file = presentation_dir / f"slide_{idx:03d}.png"
                shutil.move(str(temp_file), str(output_file))
                output_files.append(str(output_file))
                logger.debug(f"Created: {output_file}")

            logger.info(f"Rendered {len(output_files)} slides for {presentation_id}")
            return output_files

    def extract_text(self, pptx_path: str) -> str:
        """Extract all text from PPTX file.

        Args:
            pptx_path: Path to PPTX file

        Returns:
            Extracted text as string
        """
        try:
            prs = Presentation(pptx_path)
            text_parts = []

            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text = shape.text.strip()
                        if text:
                            text_parts.append(text)

            extracted_text = " ".join(text_parts)
            logger.debug(f"Extracted {len(extracted_text)} characters from {Path(pptx_path).name}")
            return extracted_text

        except Exception as e:
            logger.warning(f"Failed to extract text from {pptx_path}: {e}")
            return ""

    def render_presentation(
        self, pptx_path: str, presentation_id: str
    ) -> dict:
        """Render presentation and return metadata.

        Args:
            pptx_path: Path to PPTX file
            presentation_id: Unique ID for this presentation

        Returns:
            Dictionary with slide paths and metadata
        """
        try:
            slide_paths = self.render_pptx(pptx_path, presentation_id)

            # Extract text from presentation
            text_content = self.extract_text(pptx_path)

            # Generate relative paths for HTML
            relative_paths = [
                f"assets/{presentation_id}/{Path(p).name}"
                for p in slide_paths
            ]

            return {
                "success": True,
                "slide_count": len(slide_paths),
                "slides": relative_paths,
                "text": text_content,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Failed to render {pptx_path}: {e}")
            return {
                "success": False,
                "slide_count": 0,
                "slides": [],
                "error": str(e),
            }


def main():
    """Test the renderer."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python slides_renderer.py <path-to-pptx>")
        sys.exit(1)

    pptx_path = sys.argv[1]
    if not os.path.exists(pptx_path):
        print(f"Error: File not found: {pptx_path}")
        sys.exit(1)

    # Create renderer
    renderer = SlidesRenderer("./output")

    # Render presentation
    presentation_id = Path(pptx_path).stem
    result = renderer.render_presentation(pptx_path, presentation_id)

    if result["success"]:
        print(f"\nSuccess! Rendered {result['slide_count']} slides:")
        for slide in result["slides"][:5]:  # Show first 5
            print(f"  - {slide}")
    else:
        print(f"\nError: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
