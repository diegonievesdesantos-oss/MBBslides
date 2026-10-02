# Installing and running MBBslides on Windows, macOS and Linux

The engine is pure Python (3.10 or later). Three parts have different requirements:

| part | needs | works natively on |
|---|---|---|
| build a deck (`cpe build`), reasoning (`cpe reason …`), deck update (`cpe deck …`), brand ingestion and fidelity | Python + `pip install` | Windows, macOS, Linux |
| render and visual QA (`cpe render`, `cpe run`, `cpe qa`) | LibreOffice (Impress) | Windows, macOS, Linux |
| recorded evals and benchmarks (`cpe eval --record`, `cpe robustness --record`) | the pinned Docker image (`scripts/cpe-docker`) | Linux, macOS (Docker Desktop), Windows (Docker Desktop + WSL 2) |

Renders depend on the fonts and the LibreOffice version, so a render on your laptop is good for
working but is not comparable with a recorded benchmark. Recorded numbers always come from the
Docker image.

## Windows (PowerShell)

```powershell
git clone https://github.com/diegonievesdesantos-oss/MBBslides; cd MBBslides
py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
cpe --help
cpe build examples\alvora\deck.json -o out\alvora.pptx
```

- **Rendering:** install LibreOffice from libreoffice.org (default path
  `C:\Program Files\LibreOffice`). The engine finds `soffice.exe` there, or on `PATH`.
- **Without installing the package:** run `.\scripts\cpe.ps1 <command>` in PowerShell, or
  `scripts\cpe.cmd <command>` in cmd.exe.
- **Recorded evals:** use Docker Desktop with WSL 2, then run `scripts/cpe-docker` from a WSL shell.
- **Encoding:** the CLI writes every file as UTF-8, whatever the code page. If a console prints `?`
  instead of `→` or `€`, run `chcp 65001` or set `PYTHONUTF8=1`. The wrappers set it for you.
- If activating the venv is blocked, run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

## macOS

```bash
git clone https://github.com/diegonievesdesantos-oss/MBBslides && cd MBBslides
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
brew install --cask libreoffice          # for rendering; found in /Applications or ~/Applications
cpe build examples/alvora/deck.json -o out/alvora.pptx
```

Arial and the other Office fonts ship with macOS (`/System/Library/Fonts/Supplemental`), so text is
measured with the real fonts. For the metric-compatible open fonts used in CI, run
`brew install --cask font-liberation font-carlito font-caladea`.

## Linux (Debian / Ubuntu)

```bash
git clone https://github.com/diegonievesdesantos-oss/MBBslides && cd MBBslides
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
sudo apt-get install -y libreoffice-impress fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea
cpe build examples/alvora/deck.json -o out/alvora.pptx
```

`scripts/cpe <command>` runs the engine from a checkout without installing it.

## Checking an installation

```bash
python -m pytest -q tests/test_v17.py tests/test_v18.py tests/test_ingest.py   # no LibreOffice needed
python -m pytest -q                                                             # everything; render tests skip without LibreOffice
```

The `Portability` workflow (`.github/workflows/portability.yml`) runs these steps on every push:
install, `cpe --help`, a deck build, a deck ingest, and the reasoning tests. It runs on
Windows 2022, macOS 14 and Ubuntu 24.04, with Python 3.10 and 3.12.

## Agents on any OS

Claude Code (or any agent) runs the same commands on all three systems. Each agent playbook step
is a `cpe` command plus files in a work folder. No step uses a shell feature, and every path the
engine records is OS-independent: file names and forward-slash relative paths.
