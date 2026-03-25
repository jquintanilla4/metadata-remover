#!/bin/bash
set -e

APP_NAME="Metadata Remover"
BINARY_NAME="metadata-remover"
BUNDLE_ID="com.metadata-remover.app"
VERSION="1.0.0"

DIST_DIR="dist"
APP_DIR="$DIST_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"

# Check that the PyInstaller binary exists
if [ ! -f "$DIST_DIR/$BINARY_NAME" ]; then
    echo "Error: $DIST_DIR/$BINARY_NAME not found. Run 'make build' first."
    exit 1
fi

echo "Creating $APP_NAME.app bundle..."

# Clean any existing .app bundle
rm -rf "$APP_DIR"

# Create directory structure
mkdir -p "$MACOS_DIR"

# Copy the binary
cp "$DIST_DIR/$BINARY_NAME" "$MACOS_DIR/$BINARY_NAME"

# Create the launcher script
cat > "$MACOS_DIR/launcher" << 'LAUNCHER'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
BINARY="$DIR/metadata-remover"

# Strip quarantine flag from the binary (handles "downloaded from internet" block)
xattr -cr "$BINARY" 2>/dev/null

# Ensure common tool paths are available (macOS .app bundles don't inherit shell PATH)
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# pywebview opens its own native window — no terminal needed
exec "$BINARY"
LAUNCHER
chmod +x "$MACOS_DIR/launcher"

# Create Info.plist
cat > "$CONTENTS_DIR/Info.plist" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleVersion</key>
    <string>$VERSION</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>
PLIST

echo "Built: $APP_DIR"
echo "To distribute, zip it: zip -r \"$DIST_DIR/$APP_NAME.zip\" \"$APP_DIR\""
