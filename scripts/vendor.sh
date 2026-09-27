#!/usr/bin/env bash
set -euo pipefail

# Only httpx and its transitive dependencies may be vendored here, and only
# because they are pure Python. No package with C extensions (compiled
# .so/.pyd/.dll) belongs in _vendor/: the add-on ships as a single
# platform-independent .ankiaddon, and a compiled artifact would break that
# on any platform/architecture it wasn't built for. After running this
# script, always confirm with:
#   find src/seaminerator/_vendor \( -name "*.so" -o -name "*.pyd" -o -name "*.dll" \) -print
# If that prints anything, do not ship it — stop and reconsider the dependency.

cd "$(dirname "$0")/.."

VENDOR="src/seaminerator/_vendor"

rm -rf "$VENDOR"
mkdir -p "$VENDOR"
pip install httpx --target "$VENDOR" --no-compile

find "$VENDOR" -name "*.dist-info" -type d -exec rm -rf {} +
find "$VENDOR" -name "__pycache__" -type d -exec rm -rf {} +
find "$VENDOR" -name "bin" -maxdepth 2 -type d -exec rm -rf {} +

# Test suites and command-line entry points are never imported by the
# add-on, but they would ship in the .ankiaddon. httpx imports `_main` inside
# a try/except ImportError, so removing it is safe.
rm -rf "$VENDOR/certifi/tests"
find "$VENDOR" -name "__main__.py" -type f -delete
rm -f "$VENDOR/idna/cli.py" "$VENDOR/httpx/_main.py"

echo "Vendored into $VENDOR:"
ls -1 "$VENDOR"
