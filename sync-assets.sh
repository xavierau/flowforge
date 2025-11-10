#!/bin/bash

# Sync shared assets to marketing and frontend projects
# Run this after updating logos in shared-assets/

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 Syncing shared assets...${NC}"
echo ""

# Check if shared-assets directory exists
if [ ! -d "shared-assets/logos" ]; then
    echo "❌ Error: shared-assets/logos directory not found"
    echo "   Please create it and add your logo files first"
    exit 1
fi

# Create destination directories if they don't exist
mkdir -p marketing/public/images
mkdir -p frontend/public

# Count files to sync
LOGO_COUNT=$(find shared-assets/logos -type f | wc -l | tr -d ' ')

if [ "$LOGO_COUNT" -eq 0 ]; then
    echo "⚠️  Warning: No logo files found in shared-assets/logos"
    echo "   Add your logo files (logo.svg, logo.png, favicon.png, etc.) and run again"
    exit 0
fi

echo "Found $LOGO_COUNT file(s) to sync"
echo ""

# Sync to marketing site
echo "📁 Syncing to marketing/public/images/..."
cp -v shared-assets/logos/* marketing/public/images/ 2>/dev/null || echo "   (No files copied)"
echo ""

# Sync to frontend
echo "📁 Syncing to frontend/public/..."
cp -v shared-assets/logos/* frontend/public/ 2>/dev/null || echo "   (No files copied)"
echo ""

# Create favicon.ico from favicon.png if it exists
if [ -f "shared-assets/logos/favicon.png" ]; then
    echo "🎨 Converting favicon.png to favicon.ico..."

    # Check if ImageMagick is installed
    if command -v convert &> /dev/null; then
        convert shared-assets/logos/favicon.png -define icon:auto-resize=16,32,48,64,256 frontend/public/favicon.ico
        echo "   ✅ Created frontend/public/favicon.ico"
    else
        echo "   ⚠️  ImageMagick not installed. Skipping .ico conversion"
        echo "   Install with: brew install imagemagick (macOS)"
    fi
    echo ""
fi

echo -e "${GREEN}✅ Asset sync complete!${NC}"
echo ""
echo "📝 Next steps:"
echo "   1. Restart dev servers to see changes"
echo "   2. Update config files if needed:"
echo "      - marketing/src/config/config.json"
echo "      - frontend/src/config (if applicable)"
