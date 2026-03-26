# Created by XWZ
# ◕‿◕ Distributed for free at:
# https://github.com/nicolaiprodromov/puree
# ╔═════════════════════════════════╗
# ║  ██   ██  ██      ██  ████████  ║
# ║   ██ ██   ██  ██  ██       ██   ║
# ║    ███    ██  ██  ██     ██     ║
# ║   ██ ██   ██  ██  ██   ██       ║
# ║  ██   ██   ████████   ████████  ║
# ╚═════════════════════════════════╝
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

python := if os() == "windows" { "python" } else { "python3" }
build_core_cmd := if os() == "windows" { "./build.bat" } else { "./build.sh" }
timeout_cmd := if os() == "windows" { "timeout /t 1 /nobreak" } else { "sleep 1" }

# ── Core build tasks ─────────────────────────────────────────────────

build_core:
    @cd puree/puree_core; {{build_core_cmd}}

build_package:
    @cd dist; {{python}} build_package.py

build:
    #!/usr/bin/env bash
    set -euo pipefail
    BLENDER=$(which blender 2>/dev/null || true)
    if [ -z "$BLENDER" ]; then
        echo "Error: 'blender' not found on PATH"
        exit 1
    fi
    ADDON_DIR="$(pwd)"
    ADDON_NAME=$(grep '^name' blender_manifest.toml | cut -d'=' -f2 | tr -d ' "' | tr ' ' '_')
    VERSION=$(grep '^version' blender_manifest.toml | cut -d'=' -f2 | tr -d ' "')
    mkdir -p "$ADDON_DIR/dist"
    rm -f "$ADDON_DIR/dist"/*.zip
    OUTPUT="$ADDON_DIR/dist/${ADDON_NAME}_${VERSION}.zip"
    echo "Building $ADDON_NAME v$VERSION..."
    "$BLENDER" --background --command extension build --source-dir "$ADDON_DIR" --output-filepath "$OUTPUT"
    if [ -f "$OUTPUT" ]; then
        echo "Build successful: $OUTPUT"
    else
        echo "Build failed!"
        exit 1
    fi

wheels:
    @pip download --only-binary=:all: --python-version 3.13 --dest wheels puree-ui
    @{{python}} dist/update_wheels.py

# ── Development workflow ─────────────────────────────────────────────

blender_version := "5.1"
ext_dir := env("HOME") / ".config/blender" / blender_version / "extensions/user_default"
site_packages := env("HOME") / ".config/blender" / blender_version / "extensions/.local/lib/python3.13/site-packages"

# Symlink source into Blender extensions (replaces installed copy)
link:
    #!/usr/bin/env bash
    set -euo pipefail
    EXT_DIR="{{ext_dir}}/xwz_puree_ui"
    SITE_PUREE="{{site_packages}}/puree"
    SRC="$(pwd)"
    # Ensure wheel dependencies are installed BEFORE creating symlinks
    DEPS_INSTALLED=true
    for pkg in moderngl glcontext stretchable yaml attrs; do
        if ! ls "{{site_packages}}" 2>/dev/null | grep -qi "$pkg"; then
            DEPS_INSTALLED=false
            break
        fi
    done
    if [ "$DEPS_INSTALLED" = false ]; then
        echo "Installing wheel dependencies..."
        just install-deps
    fi
    # Extension dir: remove installed copy (or stale symlink), create symlink
    if [ -L "$EXT_DIR" ]; then
        echo "Symlink already exists, updating..."
        rm "$EXT_DIR"
    elif [ -d "$EXT_DIR" ]; then
        echo "Removing installed extension copy..."
        rm -rf "$EXT_DIR"
    fi
    ln -s "$SRC" "$EXT_DIR"
    echo "✓ Linked extension: $EXT_DIR → $SRC"
    # Site-packages puree: remove wheel-installed copy, symlink source
    if [ -L "$SITE_PUREE" ]; then
        rm "$SITE_PUREE"
    elif [ -d "$SITE_PUREE" ]; then
        echo "Removing wheel-installed puree from site-packages..."
        rm -rf "$SITE_PUREE"
        rm -rf "{{site_packages}}/puree_ui-"*.dist-info
    fi
    ln -s "$SRC/puree" "$SITE_PUREE"
    echo "✓ Linked package:   $SITE_PUREE → $SRC/puree"
    echo ""
    echo "Dev mode active. Use 'just reload' after code changes."

# Remove dev symlinks
unlink:
    #!/usr/bin/env bash
    set -euo pipefail
    EXT_DIR="{{ext_dir}}/xwz_puree_ui"
    SITE_PUREE="{{site_packages}}/puree"
    if [ -L "$EXT_DIR" ]; then
        rm "$EXT_DIR"
        echo "✓ Removed extension symlink"
    else
        echo "No extension symlink found"
    fi
    if [ -L "$SITE_PUREE" ]; then
        rm "$SITE_PUREE"
        echo "✓ Removed site-packages symlink"
    else
        echo "No site-packages symlink found"
    fi
    echo "Dev mode deactivated."

# Reload the addon in a running Blender instance
reload:
    @{{python}} dist/dev_reload.py

# Live-follow the Puree log file (requires Blender running with addon loaded)
tail:
    #!/usr/bin/env bash
    set -euo pipefail
    LOG="logs/puree.log"
    if [ ! -f "$LOG" ]; then
        echo "No log file at $LOG — is Blender running with Puree loaded?"
        exit 1
    fi
    echo "Tailing: $(realpath "$LOG")"
    echo "─────────────────────────────────────────"
    tail -f "$LOG"

# Print last N lines of the Puree log (default 50)
logs N="50":
    #!/usr/bin/env bash
    set -euo pipefail
    LOG="logs/puree.log"
    if [ ! -f "$LOG" ]; then
        echo "No log file at $LOG — is Blender running with Puree loaded?"
        exit 1
    fi
    tail -n {{N}} "$LOG"

# Delete all log files
clear-logs:
    #!/usr/bin/env bash
    set -euo pipefail
    rm -f logs/puree.log logs/puree.log.*
    echo "✓ Logs cleared"

# Install wheel dependencies into Blender's extension site-packages
install-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    SITE="{{site_packages}}"
    BLENDER_PY=$(find /snap/blender/*/5.*/python/bin/python3.* -type f -executable 2>/dev/null | sort -V | tail -1)
    if [ -z "$BLENDER_PY" ]; then
        BLENDER_PY=$(which python3)
        echo "Warning: Blender's Python not found, falling back to system python3"
    fi
    echo "Installing wheel dependencies to $SITE (using $BLENDER_PY)"
    for whl in wheels/*.whl; do
        base=$(basename "$whl")
        if [[ "$base" == puree_ui-* ]]; then
            echo "  skip $base (using source symlink)"
            continue
        fi
        "$BLENDER_PY" -m pip install --target "$SITE" --no-deps --force-reinstall --quiet "$whl" 2>/dev/null || true
        echo "  ✓ $base"
    done

# Link + reload (quick dev cycle)
deploy:
    just link
    just reload

# ── Venv (for testing CLI locally) ───────────────────────────────────

# Create venv and install puree CLI in editable mode
venv:
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -d .venv ]; then
        {{python}} -m venv .venv
        echo "✓ Created .venv"
    fi
    .venv/bin/pip install --upgrade pip --quiet
    .venv/bin/pip install --editable . --quiet
    echo "✓ Installed puree CLI in .venv"
    echo "  Activate: source .venv/bin/activate"
    echo "  Try:      puree --version"

# Install = create venv + install CLI (alias for venv)
install: venv

# ── Release workflow ─────────────────────────────────────────────────

bump VERSION:
    @{{python}} dist/update_version.py {{VERSION}}
    just build_package
    just build

release VERSION:
    @echo "Updating version to {{VERSION}}..."
    just bump {{VERSION}}
    @echo "Committing version bump..."
    git add blender_manifest.toml __init__.py setup.py pyproject.toml
    git commit -m "Bump version to {{VERSION}}"
    git push origin master
    @echo "Building and releasing v{{VERSION}}..."
    @cd dist; {{python}} release.py {{VERSION}}
    @echo "Release v{{VERSION}} completed!"
