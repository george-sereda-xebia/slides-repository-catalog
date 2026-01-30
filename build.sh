#!/bin/bash
# Build PDF catalog from Reusable_Assets folder

set -e

echo "📄 Building PDF Catalog..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Run builder
python3 src/build_catalog.py

echo ""
echo "✅ PDF generated: catalog.pdf"
echo ""
echo "Open with:"
echo "  open catalog.pdf    # macOS"
echo "  xdg-open catalog.pdf # Linux"
