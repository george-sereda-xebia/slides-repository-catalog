#!/bin/bash
# Build catalog from Reusable_Assets folder

set -e

echo "🚀 Building Slides Repository Catalog..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Set local mode
export SOURCE_MODE=local
export ROOT_FOLDER_PATH=""

# Run builder
python3 src/build_catalog.py

echo ""
echo "✅ Build complete!"
echo ""
echo "To view catalog:"
echo "  cd site && python3 -m http.server 8000"
echo "  Open: http://localhost:8000"
