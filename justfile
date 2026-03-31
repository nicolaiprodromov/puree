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
    mkdir -p "$ADDON_DIR/dist/out"
    rm -f "$ADDON_DIR/dist/out"/*.zip
    OUTPUT="$ADDON_DIR/dist/out/${ADDON_NAME}_${VERSION}.zip"
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

# Refresh puree_ui wheel in a target project folder (fixes stale wheels after engine changes)
# Usage: just refresh /path/to/my-addon
refresh TARGET:
    #!/usr/bin/env bash
    set -euo pipefail
    TARGET="{{TARGET}}"
    SRC_WHEELS="$(pwd)/wheels"
    DST_WHEELS="$TARGET/wheels"

    # Validate source
    SRC_WHL=$(ls "$SRC_WHEELS"/puree_ui-*.whl 2>/dev/null | head -1)
    if [ -z "$SRC_WHL" ]; then
        echo "Error: No puree_ui wheel in $SRC_WHEELS"
        echo "       Run 'just build_package' first."
        exit 1
    fi

    # Validate target
    if [ ! -f "$TARGET/blender_manifest.toml" ]; then
        echo "Error: No blender_manifest.toml in $TARGET"
        echo "       Is this a Puree project?"
        exit 1
    fi
    if [ ! -d "$DST_WHEELS" ]; then
        echo "Error: No wheels/ directory in $TARGET"
        exit 1
    fi

    # Replace the puree_ui wheel
    rm -f "$DST_WHEELS"/puree_ui-*.whl
    cp "$SRC_WHL" "$DST_WHEELS/"
    echo "✓ Copied $(basename "$SRC_WHL") → $DST_WHEELS/"

    # Update blender_manifest.toml wheels list
    {{python}} << PYEOF
    import re, pathlib
    proj = pathlib.Path('$TARGET')
    manifest = proj / 'blender_manifest.toml'
    wheels_dir = proj / 'wheels'
    whl_files = sorted(['./wheels/' + f.name for f in wheels_dir.glob('*.whl')])
    lines = '\n'.join(f'  "{w}",' for w in whl_files)
    new_block = f'wheels = [\n{lines}\n]'
    content = manifest.read_text()
    content = re.sub(r'wheels\s*=\s*\[.*?\]', new_block, content, flags=re.DOTALL)
    manifest.write_text(content)
    PYEOF
    echo "✓ Updated blender_manifest.toml wheels list"

    # If project is linked to Blender, re-extract the wheel into site-packages
    SITE="{{site_packages}}"
    ADDON_ID=$(grep '^id' "$TARGET/blender_manifest.toml" | cut -d'=' -f2 | tr -d ' "')
    EXT_LINK="{{ext_dir}}/$ADDON_ID"
    if [ -L "$EXT_LINK" ]; then
        echo "  Project is linked — refreshing site-packages..."
        {{python}} << PYEOF
    import zipfile, pathlib, shutil
    whl = pathlib.Path('$SRC_WHL')
    site = pathlib.Path('$SITE')
    site.mkdir(parents=True, exist_ok=True)
    for old in site.glob('puree_ui-*'):
        if old.is_dir():
            shutil.rmtree(old)
        else:
            old.unlink()
    puree_pkg = site / 'puree'
    if puree_pkg.is_dir() and not puree_pkg.is_symlink():
        shutil.rmtree(puree_pkg)
    with zipfile.ZipFile(whl, 'r') as zf:
        zf.extractall(site)
    print(f'  ✓ Extracted {whl.name} into site-packages')
    PYEOF
    fi
    echo "Done!"

# Run all CI checks locally
ci:
    #!/usr/bin/env bash
    set -euo pipefail
    VENV=".venv"
    if [ ! -d "$VENV" ]; then
        echo "Error: .venv not found. Run 'just venv' first."
        exit 1
    fi
    RUFF="$VENV/bin/ruff"
    if [ ! -f "$RUFF" ]; then
        echo "Installing ruff into .venv..."
        "$VENV/bin/pip" install ruff --quiet
    fi
    TARGETS="puree/ __init__.py tests/ dist/ setup.py"
    echo "── Python format ──"
    "$RUFF" format --check $TARGETS
    echo "── Python lint ──"
    "$RUFF" check $TARGETS
    echo "── Rust checks ──"
    pushd puree/puree_core > /dev/null
    cargo build --release
    cargo clippy -- -D warnings
    cargo test
    cargo fmt -- --check
    popd > /dev/null
    echo "✓ All checks passed"

# Auto-fix all safe Python + Rust issues
fix:
    #!/usr/bin/env bash
    set -euo pipefail
    VENV=".venv"
    if [ ! -d "$VENV" ]; then
        echo "Error: .venv not found. Run 'just venv' first."
        exit 1
    fi
    RUFF="$VENV/bin/ruff"
    if [ ! -f "$RUFF" ]; then
        echo "Installing ruff into .venv..."
        "$VENV/bin/pip" install ruff --quiet
    fi
    TARGETS="puree/ __init__.py tests/ dist/ setup.py"
    echo "── Python lint fix ──"
    "$RUFF" check --fix $TARGETS || true
    echo "── Python format ──"
    "$RUFF" format $TARGETS
    echo "── Rust format ──"
    find puree/puree_core/src -name '*.rs' -exec rustfmt {} +
    echo ""
    echo "── Remaining issues (manual fix needed) ──"
    "$RUFF" check $TARGETS || true
    echo ""
    echo "✓ Safe fixes applied. Review any remaining issues above."

# Link + reload (quick dev cycle)
deploy:
    just link
    just reload

# ── Code formatting ──────────────────────────────────────────────────

# Strip comments and format all Python + Rust code (requires .venv with ruff)
format:
    #!/usr/bin/env bash
    set -euo pipefail
    VENV=".venv"
    if [ ! -d "$VENV" ]; then
        echo "Error: .venv not found. Run 'just venv' first."
        exit 1
    fi
    RUFF="$VENV/bin/ruff"
    if [ ! -f "$RUFF" ]; then
        echo "Installing ruff into .venv..."
        "$VENV/bin/pip" install ruff --quiet
    fi
    echo "── Stripping Python comments ──"
    {{python}} dist/format_python.py puree/ __init__.py tests/ dist/ setup.py
    echo "── Formatting Python (ruff) ──"
    "$RUFF" format puree/ __init__.py tests/ dist/ setup.py 2>/dev/null || true
    echo "── Stripping Rust comments ──"
    {{python}} dist/format_rust.py puree/puree_core/src/
    echo "── Formatting Rust (rustfmt) ──"
    find puree/puree_core/src -name '*.rs' -exec rustfmt {} +
    echo "✓ Format complete"

# ── Venv (for testing CLI locally) ───────────────────────────────────

# Create venv and install puree CLI in editable mode
# Optionally pass a path: just venv /path/to/my/venv
venv VENV_PATH=".venv":
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -d "{{VENV_PATH}}" ]; then
        {{python}} -m venv "{{VENV_PATH}}"
        echo "✓ Created {{VENV_PATH}}"
    fi
    "{{VENV_PATH}}/bin/pip" install --upgrade pip --quiet
    "{{VENV_PATH}}/bin/pip" install --editable . --quiet
    echo "✓ Installed puree CLI in {{VENV_PATH}}"
    echo "  Activate: source {{VENV_PATH}}/bin/activate"
    echo "  Try:      puree --version"

# Install = rebuild wheel + create venv + install CLI
# Rebuilds the wheel first so wheels/ is always fresh for `puree init`
# Optionally pass a path: just install /path/to/my/venv
install VENV_PATH=".venv": build_package (venv VENV_PATH)

# ── Release workflow ─────────────────────────────────────────────────

bump VERSION:
    @{{python}} dist/update_version.py {{VERSION}}
    just build_package
    just build

release VERSION:
    @echo "Releasing v{{VERSION}}..."
    just bump {{VERSION}}
    git add blender_manifest.toml __init__.py setup.py pyproject.toml
    git commit -m "Release v{{VERSION}}"
    git tag v{{VERSION}}
    git push origin master --tags
    @echo "✓ Pushed v{{VERSION}} — GitHub Actions will build and publish"
