# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python 2.7 web application and PDF generation system for the Hubbard Hall Tune Jam — a traditional music session in Cambridge, NY. The site manages a database of fiddle tunes (Irish, Scottish, Quebecois, New England, locally-written) with recordings, chord charts, and melody reminders. Live at http://music.cambridgeny.net

## Python Environment

This is a Python 2.7 project. Always use the virtualenv Python, never the system Python:
- **Dev (macOS)**: `../bin/python2.7` (relative to `src/`, i.e. `music/bin/python2.7`)
- **Production (Linux)**: `/home/maint/music/bin/python2.7`

## Running the Application

**Development server** (from `src/` directory):
```
../bin/python2.7 website/tunejam.py
```
Runs Flask on `0.0.0.0:60080` with debug/reload enabled.

**Production**: Apache CGI via `website/tunejam.cgi` — uses the production virtualenv Python.

**Deploying to production** (run as `maint` on server, from `src/`):
```
./deploy.sh
```
Does `git pull` then calls `website/fixperms.py` to fix permissions on data directories that apache needs to write to. Uses sudo when run as a regular user (interactive deploy); runs directly when already root (cron). **When adding new data directories** to the application, update the `DATA_DIRS` array in `website/fixperms.py` (the single source of truth).

**Regenerate cached PDF books**:
```
python website/crontask.py          # regenerate stale books
python website/crontask.py --force  # force regenerate all
```

**Generate books directly** (opens PDFs on macOS):
```
python allbook.py      # all tunes book
python flipbook.py     # practice flip book
python sessbook.py     # session-specific book
python setsheets.py --book <name>         # small format
python setsheets.py --book --large <name> # large format
python setsheets.py --book --ring <name>  # ring binding format
```

## Architecture

All source code is under `src/`.

### Core Modules

- **`utils.py`** (~1900 lines) — Central library containing all data models and PDF generation:
  - `CTune` — Reads a `.spec` file from `db/`, generates sheet music via ABC notation → PostScript → PDF pipeline
  - `CTuneSet` — Groups tunes into sets; generates chord charts and melody reminder sheets (small and large formats)
  - `CBook` / `CSetBook` / `CEvent` — PDF book generators with caching; pages are collections of `CTuneSet` objects
  - `CSheetPage` — Individual page rendering using reportlab
  - `ABCToPostscript()` — Converts ABC notation to PostScript using external `abcm2ps` binary

- **`website/tunejam.py`** (~2300 lines) — Flask app with all routes and HTML generation. Key routes: `/` home, `/index` tune browsing, `/sets` interactive set builder, `/events` shareable event pages, `/print` PDF books, `/tune/<name>` individual tunes, `/sheet/{view|print|abc}/<tunes>` sheet music.

- **`website/html.py`** — Custom HTML generation library (legacy, from 1999-2002). Used throughout instead of templates. Classes like `CH`, `CParagraph`, `CText`, `CList`, `CItem`, `CTable`, etc.

- **`setsheets.py`** — CLI entry point for generating tune set PDFs and books.

### Tune Database

Tunes are stored as flat `.spec` files in `src/db/` (~240 files). Format:
```
T:Title
C:type (reel, jig, slip, waltz, etc.)
O:Origin
A:Author
H:History line (repeatable)
U:URL link (repeatable)
K:Key
L:Unit note length
M:Meter
--
|ABC notation for melody (first measures of each part)|
--
|Chord chart using bar notation|
```

Tune types are defined in `kSections` in `utils.py`: reel, jig, slip, rag, march, waltz, polka, polska, hornpipe, strathspey, rant, slide, other, air, incomplete.

### External Dependencies

- **reportlab** — PDF generation (fonts: Trebuchet MS)
- **PIL/Pillow** — Image processing
- **Flask** — Web framework
- **abcm2ps** — ABC notation → PostScript converter (binary in `../bin/abcm2ps`)
- **ghostscript** — PostScript processing

Platform binaries and source tarballs are in `src/platform/`.

### File Layout

- `src/db/*.spec` — Tune database files
- `src/tunes/*.abc` — Full ABC notation files for locally-written tunes
- `src/recordings/*.mp3` — Tune recordings (~200 files)
- `src/images/` — Web UI images
- `src/website/cache/` — Generated PDF cache (tuneset/, tune/, book/ subdirs)
- `src/website/saved-sets/` — User-saved tune sets
- `src/website/events/` — Event data with `archive/` subdir
- `src/website/js/` — jQuery UI 1.13.2

## Key Patterns

- **Caching**: PDF generation results are cached in `website/cache/`. `kUseCache` flag in `utils.py` controls this. Cache staleness is checked against source file modification times.
- **Platform paths**: Code branches on `sys.platform == 'darwin'` for macOS dev vs Linux production (font paths, Python paths, host binding).
- **HTML generation**: All HTML is built programmatically via `html.py` classes — there are no template files.
- **Constants prefix**: Module-level constants use `k` prefix (e.g., `kDatabaseDir`, `kFontSize`, `kSections`).
- **Wing IDE integration**: `scripts/abc.py` provides ABC notation formatting for Wing Pro IDE. The `wingdbstub` import in `tunejam.py` enables Wing debugging.
- **Site activity notifications**: When adding new features that create, edit, delete, ban, or perform other notable admin-visible actions, always add a `LogNotification(category, message)` call (categories: `tune`, `event`, `user`, `admin`) so the action appears in the periodic admin digest email. See existing calls for format examples.
- **No print() in request-reachable code**: Under Apache CGI, stdout IS the HTTP response stream. Any `print()` in code reachable from a request handler (including `before_request`, route functions, and anything they call) will corrupt the HTTP response and cause Apache to return 500 (AH02429). Use `sys.stderr.write(msg + '\n')` for diagnostics — stderr goes to the Apache error log.
