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
build_cmd := if os() == "windows" { "./build" } else { "./build.sh" }
build_core_cmd := if os() == "windows" { "./build.bat" } else { "./build.sh" }
timeout_cmd := if os() == "windows" { "timeout /t 1 /nobreak" } else { "sleep 1" }

build_core:
    @cd puree/puree_core; {{build_core_cmd}}

build_package:
    @cd dist; {{python}} build_package.py

build:
    @cd dist; {{build_cmd}}

install:
    @cd dist; {{python}} install.py install

uninstall:
    @cd dist; {{python}} install.py uninstall

wheels:
    @pip download --only-binary=:all: --python-version 3.13 --dest wheels puree-ui
    @{{python}} dist/update_wheels.py

deploy:
    just build_core
    @{{timeout_cmd}}
    just build_package
    @{{timeout_cmd}}
    just build
    @{{timeout_cmd}}
    just install

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

# ── Development workflow ─────────────────────────────────────────────
# Symlink source into Blender's extensions dir so code changes are
# picked up instantly without build/zip/install cycles.
# Usage:
#   just dev-link          # first time setup
#   just dev-reload        # after making code changes

blender_version := "5.1"
ext_dir := env("HOME") / ".config/blender" / blender_version / "extensions/user_default"
site_packages := env("HOME") / ".config/blender" / blender_version / "extensions/.local/lib/python3.13/site-packages"

# Reload the addon in a running Blender (requires MCP server on port 9876)
dev-reload:
    @{{python}} dist/dev_reload.py

# Link source into Blender extensions (replaces installed copy)
dev-link:
    #!/usr/bin/env bash
    set -euo pipefail
    EXT_DIR="{{ext_dir}}/xwz_puree_ui"
    SITE_PUREE="{{site_packages}}/puree"
    SRC="$(pwd)"
    # Ensure wheel dependencies are installed BEFORE creating symlinks
    # (pip --force-reinstall can overwrite the symlink)
    DEPS_INSTALLED=true
    for pkg in moderngl glcontext stretchable yaml attrs; do
        if ! ls "{{site_packages}}" 2>/dev/null | grep -qi "$pkg"; then
            DEPS_INSTALLED=false
            break
        fi
    done
    if [ "$DEPS_INSTALLED" = false ]; then
        echo "Installing wheel dependencies..."
        just dev-install-deps
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
    echo "Dev mode active. Use 'just dev-reload' after code changes."

# Remove dev symlinks
dev-unlink:
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
    echo "Dev mode deactivated. Use 'just install' for normal extension install."

# Install wheel dependencies into Blender's extension site-packages
dev-install-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    SITE="{{site_packages}}"
    # Use Blender's own Python so manylinux wheels are accepted
    BLENDER_PY=$(find /snap/blender/*/5.*/python/bin/python3.* -type f -executable 2>/dev/null | sort -V | tail -1)
    if [ -z "$BLENDER_PY" ]; then
        BLENDER_PY=$(which python3)
        echo "Warning: Blender's Python not found, falling back to system python3"
    fi
    echo "Installing wheel dependencies to $SITE (using $BLENDER_PY)"
    for whl in wheels/*.whl; do
        base=$(basename "$whl")
        # Skip the puree_ui wheel (we use the source symlink instead)
        if [[ "$base" == puree_ui-* ]]; then
            echo "  skip $base (using source symlink)"
            continue
        fi
        "$BLENDER_PY" -m pip install --target "$SITE" --no-deps --force-reinstall --quiet "$whl" 2>/dev/null || true
        echo "  ✓ $base"
    done
