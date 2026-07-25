#!/usr/bin/env bash
# Download and extract EnergyPlus 24.1.0 into third_party/EnergyPlus (Linux x86_64).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${ENERGYPLUS_VERSION:-24.1.0}"
TAG="${ENERGYPLUS_TAG:-24.1.0-9d7789a3ac}"
DEST="$ROOT/third_party/EnergyPlus"
CACHE="$ROOT/third_party"
mkdir -p "$CACHE"

if [[ -x "$DEST/energyplus" || -f "$DEST/energyplus" ]]; then
  echo "EnergyPlus already present at $DEST"
  "$DEST/energyplus" --version || true
  exit 0
fi

ARCHIVE="EnergyPlus-${TAG}-Linux-Ubuntu22.04-x86_64.tar.gz"
URL="https://github.com/NREL/EnergyPlus/releases/download/v${VERSION}/${ARCHIVE}"
TGZ="$CACHE/$ARCHIVE"

echo "Downloading $URL"
if command -v curl >/dev/null; then
  curl -L --fail -o "$TGZ" "$URL"
else
  wget -O "$TGZ" "$URL"
fi

echo "Extracting to $DEST"
rm -rf "$DEST"
mkdir -p "$ROOT/third_party"
tar -xzf "$TGZ" -C "$ROOT/third_party"
EXTRACTED="$(find "$ROOT/third_party" -maxdepth 1 -type d -name "EnergyPlus-${VERSION}*" | head -1)"
if [[ -z "$EXTRACTED" ]]; then
  echo "ERROR: could not find extracted EnergyPlus directory" >&2
  exit 1
fi
mv "$EXTRACTED" "$DEST"
echo "Installed EnergyPlus:"
"$DEST/energyplus" --version
echo
echo "Set:"
echo "  export ENERGYPLUS_HOME=$DEST"
echo "  export ENERGYPLUS_MODEL_PATH=$ROOT/building-models/sample-office/office_5zone.idf"
echo "  export ENERGYPLUS_WEATHER_PATH=$ROOT/building-models/weather/chicago.epw"
