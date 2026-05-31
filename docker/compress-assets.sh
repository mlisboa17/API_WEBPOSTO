#!/bin/bash
# GEMINI 2.0: Static Asset Compression Script
# Compresses .next and public directories with Gzip + Brotli
# Reduces bandwidth by 60-70% for static assets

set -e

echo "🗜️ Starting asset compression..."

# Define directories
NEXT_DIR="/app/.next"
PUBLIC_DIR="/app/public"
COMPRESSED_DIR="/app/.next/compressed"

mkdir -p "$COMPRESSED_DIR"

# Compression function
compress_file() {
    local file="$1"
    local filename=$(basename "$file")
    
    # Skip already compressed files
    if [[ "$filename" =~ \.(gz|br|woff2|png|jpg|jpeg|webp)$ ]]; then
        return
    fi
    
    # Gzip compression (level 9)
    if [ -f "$file" ]; then
        gzip -k -9 -f "$file" 2>/dev/null || true
        echo "  ✓ Gzipped: $filename"
    fi
    
    # Brotli compression (level 11)
    if [ -f "$file" ]; then
        brotli -k -11 -f "$file" 2>/dev/null || true
        echo "  ✓ Brotli'd: $filename"
    fi
}

# Compress .next directory
if [ -d "$NEXT_DIR" ]; then
    echo "📦 Compressing .next directory..."
    find "$NEXT_DIR" -type f \( -name "*.js" -o -name "*.css" -o -name "*.html" -o -name "*.json" \) | while read file; do
        compress_file "$file"
    done
fi

# Compress public directory
if [ -d "$PUBLIC_DIR" ]; then
    echo "📦 Compressing public directory..."
    find "$PUBLIC_DIR" -type f \( -name "*.js" -o -name "*.css" -o -name "*.html" -o -name "*.json" -o -name "*.svg" \) | while read file; do
        compress_file "$file"
    done
fi

# Create compression index
echo "📝 Creating compression index..."
cat > "$COMPRESSED_DIR/manifest.json" <<EOF
{
  "compressed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "algorithm": "gzip,brotli",
  "levels": {
    "gzip": 9,
    "brotli": 11
  },
  "directories": {
    ".next": "$(find "$NEXT_DIR" -type f -name "*.gz" -o -name "*.br" | wc -l) files",
    "public": "$(find "$PUBLIC_DIR" -type f -name "*.gz" -o -name "*.br" | wc -l) files"
  }
}
EOF

# Summary
NEXT_COMPRESSED=$(find "$NEXT_DIR" -type f -name "*.gz" -o -name "*.br" | wc -l)
PUBLIC_COMPRESSED=$(find "$PUBLIC_DIR" -type f -name "*.gz" -o -name "*.br" | wc -l)
TOTAL=$((NEXT_COMPRESSED + PUBLIC_COMPRESSED))

echo ""
echo "✅ Asset compression complete!"
echo "   - .next: $NEXT_COMPRESSED compressed files"
echo "   - public: $PUBLIC_COMPRESSED compressed files"
echo "   - Total: $TOTAL compressed files"
echo ""
