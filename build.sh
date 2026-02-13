#!/bin/bash
# Build PDF catalog from input/ folder

set -e

echo "Building PDF Catalog..."
echo ""

# Pre-flight: check input/ directory exists
if [ ! -d "input" ]; then
    echo "ERROR: input/ directory not found."
    echo "Create it and add your .pptx files:"
    echo "  mkdir -p input"
    echo "  cp /path/to/*.pptx input/"
    exit 1
fi

# Kill stale LibreOffice processes to avoid profile locking
pkill -f soffice 2>/dev/null || true
sleep 1

# Activate virtual environment
source venv/bin/activate

# Run builder
python3 src/build_catalog.py

echo ""
echo "PDF generated: CATALOG.pdf"
echo ""
echo "Open with:"
echo "  open CATALOG.pdf    # macOS"
echo "  xdg-open CATALOG.pdf # Linux"
