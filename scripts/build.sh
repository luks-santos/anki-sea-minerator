#!/usr/bin/env bash
set -euo pipefail

# The zip holds the *contents* of the add-on folder (no leading directory
# component): __init__.py and manifest.json must sit at the archive root.
# AnkiWeb rejects archives containing __pycache__.
#
# Anki saves the user's settings, API keys included, to meta.json in the
# add-on folder, and keeps user_files/ for an add-on's own data. With the
# development junction (docs/development.md), src/seaminerator *is* that
# folder, so both are always left out: a package must never carry them.
#
# SRC and OUT can be overridden, e.g. to build a test copy.

cd "$(dirname "$0")/.."

SRC="${SRC:-src/seaminerator}"
OUT="${OUT:-dist/sea-minerator.ankiaddon}"

[ -d "$SRC/_vendor" ] || { echo "run scripts/vendor.sh first"; exit 1; }

find "$SRC" -name "__pycache__" -type d -exec rm -rf {} +
mkdir -p "$(dirname "$OUT")"
OUT="$(cd "$(dirname "$OUT")" && pwd)/$(basename "$OUT")"
rm -f "$OUT"

PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if command -v zip >/dev/null 2>&1; then
    ( cd "$SRC" && zip -qr "$OUT" . -x '*.pyc' 'meta.json' 'user_files/' 'user_files/*' )
else
    # `zip` isn't available on every dev machine (notably plain Git Bash on
    # Windows). Fall back to Python's stdlib zipfile module, which produces
    # an equivalent archive: contents of $SRC at the archive root, no *.pyc,
    # no __pycache__ (already removed above), no meta.json or user_files/.
    echo "zip not found on PATH; building the archive with Python's zipfile module"
    [ -n "$PY" ] || { echo "no working python interpreter found"; exit 1; }

    "$PY" - "$SRC" "$OUT" <<'PYEOF'
import os
import sys
import zipfile

src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src):
        at_root = os.path.samefile(root, src)
        dirs[:] = [
            d for d in dirs if d != "__pycache__" and not (at_root and d == "user_files")
        ]
        for name in files:
            if name.endswith(".pyc") or (at_root and name == "meta.json"):
                continue
            full = os.path.join(root, name)
            rel = os.path.relpath(full, src)
            zf.write(full, rel)
PYEOF
fi

if command -v unzip >/dev/null 2>&1; then
    listing="$(unzip -Z1 "$OUT")"
else
    listing="$("$PY" -c 'import sys, zipfile; print("\n".join(zipfile.ZipFile(sys.argv[1]).namelist()))' "$OUT")"
fi
if grep -qE '^(meta\.json|user_files/)|__pycache__|\.pyc$' <<<"$listing"; then
    rm -f "$OUT"
    echo "refusing to ship: the archive holds settings or compiled files"
    exit 1
fi

echo "Built $OUT ($(grep -c . <<<"$listing") files)"
