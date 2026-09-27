#!/usr/bin/env bash
set -euo pipefail

# The zip holds the *contents* of the add-on folder (no leading directory
# component): __init__.py and manifest.json must sit at the archive root.
# AnkiWeb rejects archives containing __pycache__.

cd "$(dirname "$0")/.."

SRC="src/seaminerator"
OUT="dist/sea-minerator.ankiaddon"

[ -d "$SRC/_vendor" ] || { echo "run scripts/vendor.sh first"; exit 1; }

find "$SRC" -name "__pycache__" -type d -exec rm -rf {} +
mkdir -p dist
rm -f "$OUT"

if command -v zip >/dev/null 2>&1; then
    ( cd "$SRC" && zip -r "../../$OUT" . -x '*.pyc' )
else
    # `zip` isn't available on every dev machine (notably plain Git Bash on
    # Windows). Fall back to Python's stdlib zipfile module, which produces
    # an equivalent archive: contents of $SRC at the archive root, no *.pyc,
    # no __pycache__ (already removed above).
    echo "zip not found on PATH; building the archive with Python's zipfile module"

    PY=""
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "" >/dev/null 2>&1; then
            PY="$candidate"
            break
        fi
    done
    [ -n "$PY" ] || { echo "no working python interpreter found"; exit 1; }

    "$PY" - "$SRC" "$OUT" <<'PYEOF'
import os
import sys
import zipfile

src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if name.endswith(".pyc"):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, src)
            zf.write(full, rel)
PYEOF
fi

echo "Built $OUT"
if command -v unzip >/dev/null 2>&1; then
    unzip -l "$OUT" | head -20
else
    "${PY:-python}" -m zipfile -l "$OUT" | head -20
fi
