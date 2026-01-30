# Slides Repository Catalog

PDF catalog generator for presentations in the `Reusable_Assets/` folder. Renders slide thumbnails and embeds hidden text for full-text search.

## Quick Start

```bash
./build.sh
```

Output: `catalog.pdf` with thumbnails of all slides.

## How It Works

1. Scans `Reusable_Assets/` recursively for `.pptx` files
2. Converts each slide to PNG via LibreOffice
3. Extracts text content from presentations
4. Generates a PDF with:
   - Slide thumbnails (2 per page)
   - File names and paths
   - Hidden searchable text (Ctrl+F / Cmd+F)

## Search

The PDF contains invisible text layer for each presentation:
- File name
- File path
- All text from slides

Use **Ctrl+F** (Cmd+F on Mac) to search across all content.

## Requirements

- Python 3.11+
- LibreOffice (for slide rendering)

```bash
# macOS
brew install libreoffice

# Ubuntu
sudo apt-get install libreoffice
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Project Structure

```
.
├── Reusable_Assets/         # Presentations folder
├── catalog.pdf              # Generated PDF catalog
├── src/
│   ├── build_catalog.py     # Main build script
│   ├── local_client.py      # File scanner
│   ├── slides_renderer.py   # PPTX → PNG + text extraction
│   └── pdf_generator.py     # PDF generator
└── build.sh                 # Build script
```

## Manual Run

```bash
source venv/bin/activate
python3 src/build_catalog.py
```
