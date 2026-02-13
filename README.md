# Slides Repository Catalog

Generates a single searchable PDF catalog from a folder of `.pptx` presentations.
Slides are converted to native PDF pages (not images), so **Cmd+F / Ctrl+F works on actual slide content**.

## Quick Start

```bash
# 1. Clone and setup
git clone <repo-url> && cd slides-repository-catalog
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Add presentations
mkdir -p input
cp /path/to/your/*.pptx input/      # flat or nested folders, both work

# 3. Build
./build.sh
open CATALOG.pdf
```

## Requirements

- Python 3.11+
- LibreOffice (used headless for PPTX → PDF conversion)

```bash
# macOS
brew install libreoffice

# Ubuntu
sudo apt-get install libreoffice
```

## Output

`CATALOG.pdf` contains:
- Title page with table of contents grouped by folder
- Compact separator strip before each presentation
- Native searchable slides at consistent width

## Project Structure

```
├── input/                  # Your .pptx files go here (gitignored)
├── src/
│   ├── build_catalog.py    # Main pipeline
│   ├── local_client.py     # File discovery
│   ├── slides_renderer.py  # PPTX → PDF via LibreOffice
│   └── pdf_generator.py    # Merges PDFs into catalog
├── build.sh                # One-command build
└── requirements.txt
```
