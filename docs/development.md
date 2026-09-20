# Development

## Running the add-on from the repo

Anki's docs only offer symlinking on Mac and Linux. On Windows, use a
directory junction instead — it needs no admin rights (unlike a symlink) and,
unlike a `sys.path` shim (see below), it makes Anki treat `src/seaminerator`
itself as the add-on folder:

`mklink` is a `cmd.exe` builtin and `%APPDATA%` only expands under `cmd`, so
run this from **Command Prompt**:

```bat
mklink /J "%APPDATA%\Anki2\addons21\seaminerator" "C:\Users\<you>\Documents\workspace\personal\anki-sea-minerator\src\seaminerator"
```

From PowerShell, invoke it through `cmd` instead — `mklink` is not a
PowerShell command and the bare form fails with
`The term 'mklink' is not recognized`:

```powershell
cmd /c mklink /J "$env:APPDATA\Anki2\addons21\seaminerator" "C:\Users\<you>\Documents\workspace\personal\anki-sea-minerator\src\seaminerator"
```

Close Anki before creating the junction, and remove it (`rmdir` on the
junction, which deletes the link, not the target) before installing a built
`.ankiaddon` — `manifest.json` declares `"package": "seaminerator"`, so Anki
would target the same folder name.

This matters because `wizard.py` resolves the add-on's config with
`mw.addonManager.getConfig(__name__.split(".")[0])`, which reads
`addons21/<folder name>/config.json`. The junction target,
`src/seaminerator/`, already has the right shape for this: `manifest.json`
and `config.json` sit next to the package's own modules and `_vendor/`,
exactly like a real install. Naming the junction `seaminerator` (matching the
package name Anki would import) makes `__name__.split(".")[0]` and the
junction's folder name agree, so `getConfig` finds `config.json` and
`Tools → Add-ons → Sea Minerator → Config` opens it (`manifest.json` is what
add-on-manager needs to show that Config button at all).

Restart Anki. `Tools → Mine vocabulary…` appears. Restart after every code
change — Anki does not hot-reload add-ons.

Anki may write a `meta.json` into `src/seaminerator/` the first time you save
config from the UI (config edited through the dialog is stored there,
per-addon). That file is generated, not source — do not commit it.

### Alternative: `sys.path` shim (config unavailable)

An earlier version of this doc suggested a shim add-on that inserts the repo
on `sys.path`:

```python
# %APPDATA%\Anki2\addons21\seaminerator_dev\__init__.py
import sys

sys.path.insert(
    0, r"C:\Users\<you>\Documents\workspace\personal\anki-sea-minerator\src"
)
import seaminerator  # noqa: F401
```

**Do not use this for anything that needs an API key.** The shim's folder is
named `seaminerator_dev`, but the imported package's `__name__` is
`seaminerator`, so `getConfig("seaminerator")` looks for
`addons21/seaminerator/config.json` — a folder that does not exist under this
setup — and gets back `None`. The wizard always reports "No Gemini API key
configured", and there is no Config menu item to fix it (the shim has no
`manifest.json`), so **mining cannot run** under this setup. It is only
useful for exercising code paths that don't need config (e.g. checking that
the menu entry registers). Prefer the junction above.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

`anki` (pylib) is a dev dependency and is separate from `aqt` (the GUI), so the
collection tests run without Anki installed or running.
