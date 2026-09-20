# Development

## Running the add-on from the repo

Anki's docs only offer symlinking on Mac and Linux. On Windows, use a shim
add-on that inserts this repo on `sys.path`.

Create `%APPDATA%\Anki2\addons21\seaminerator_dev\__init__.py`:

```python
import sys

sys.path.insert(
    0, r"C:\Users\<you>\Documents\workspace\personal\anki-sea-minerator\src"
)
import seaminerator  # noqa: F401
```

Restart Anki. `Tools → Mine vocabulary…` appears. Restart after every code
change — Anki does not hot-reload add-ons.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

`anki` (pylib) is a dev dependency and is separate from `aqt` (the GUI), so the
collection tests run without Anki installed or running.
