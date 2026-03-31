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
.PHONY: build build_core build_package wheels link unlink reload tail logs clear-logs refresh deploy format install install-deps venv bump release ci

BLENDER_VERSION := 5.1
ADDON_DIR       := $(CURDIR)
ADDON_ID        := xwz_puree_ui

ifeq ($(OS),Windows_NT)
PYTHON       := python
BUILD_CORE   := build.bat
EXT_DIR      := $(APPDATA)/Blender Foundation/Blender/$(BLENDER_VERSION)/extensions/user_default
SITE_PACKAGES:= $(APPDATA)/Blender Foundation/Blender/$(BLENDER_VERSION)/extensions/.local/lib/python3.13/site-packages
VENV_PYTHON  := .venv\Scripts\python.exe
VENV_PIP     := .venv\Scripts\pip.exe
else
PYTHON       := python3
BUILD_CORE   := ./build.sh
EXT_DIR      := $(HOME)/.config/blender/$(BLENDER_VERSION)/extensions/user_default
SITE_PACKAGES:= $(HOME)/.config/blender/$(BLENDER_VERSION)/extensions/.local/lib/python3.13/site-packages
VENV_PYTHON  := .venv/bin/python
VENV_PIP     := .venv/bin/pip
endif

# ── Core build tasks ─────────────────────────────────────────────────

build_core:
	@cd puree/puree_core && $(BUILD_CORE)

build_package:
	@cd dist && $(PYTHON) build_package.py

build:
	@BLENDER=$$(which blender 2>/dev/null); \
	if [ -z "$$BLENDER" ]; then echo "Error: 'blender' not found on PATH"; exit 1; fi; \
	ADDON_NAME=$$(grep '^name' blender_manifest.toml | cut -d'=' -f2 | tr -d ' "' | tr ' ' '_'); \
	VERSION=$$(grep '^version' blender_manifest.toml | cut -d'=' -f2 | tr -d ' "'); \
	mkdir -p "$(ADDON_DIR)/dist/out"; \
	rm -f "$(ADDON_DIR)/dist/out"/*.zip; \
	OUTPUT="$(ADDON_DIR)/dist/out/$${ADDON_NAME}_$${VERSION}.zip"; \
	echo "Building $$ADDON_NAME v$$VERSION..."; \
	"$$BLENDER" --background --command extension build --source-dir "$(ADDON_DIR)" --output-filepath "$$OUTPUT"; \
	if [ -f "$$OUTPUT" ]; then echo "Build successful: $$OUTPUT"; else echo "Build failed!"; exit 1; fi

wheels:
	@pip download --only-binary=:all: --python-version 3.13 --dest wheels puree-ui
	@$(PYTHON) dist/update_wheels.py

# ── Development workflow ─────────────────────────────────────────────

link:
	@EXT_LINK="$(EXT_DIR)/$(ADDON_ID)"; \
	SITE_PUREE="$(SITE_PACKAGES)/puree"; \
	if [ -L "$$EXT_LINK" ]; then \
		echo "Symlink already exists, updating..."; \
		rm "$$EXT_LINK"; \
	elif [ -d "$$EXT_LINK" ]; then \
		echo "Removing installed extension copy..."; \
		rm -rf "$$EXT_LINK"; \
	fi; \
	ln -s "$(ADDON_DIR)" "$$EXT_LINK"; \
	echo "✓ Linked extension: $$EXT_LINK → $(ADDON_DIR)"; \
	if [ -L "$$SITE_PUREE" ]; then \
		rm "$$SITE_PUREE"; \
	elif [ -d "$$SITE_PUREE" ]; then \
		echo "Removing wheel-installed puree from site-packages..."; \
		rm -rf "$$SITE_PUREE"; \
		rm -rf "$(SITE_PACKAGES)/puree_ui-"*.dist-info; \
	fi; \
	ln -s "$(ADDON_DIR)/puree" "$$SITE_PUREE"; \
	echo "✓ Linked package:   $$SITE_PUREE → $(ADDON_DIR)/puree"; \
	echo ""; \
	echo "Dev mode active. Use 'make reload' after code changes."

unlink:
	@EXT_LINK="$(EXT_DIR)/$(ADDON_ID)"; \
	SITE_PUREE="$(SITE_PACKAGES)/puree"; \
	if [ -L "$$EXT_LINK" ]; then \
		rm "$$EXT_LINK"; \
		echo "✓ Removed extension symlink"; \
	else \
		echo "No extension symlink found"; \
	fi; \
	if [ -L "$$SITE_PUREE" ]; then \
		rm "$$SITE_PUREE"; \
		echo "✓ Removed site-packages symlink"; \
	else \
		echo "No site-packages symlink found"; \
	fi; \
	echo "Dev mode deactivated."

reload:
	@$(PYTHON) dist/dev_reload.py

tail:
	@LOG="logs/puree.log"; \
	if [ ! -f "$$LOG" ]; then \
		echo "No log file at $$LOG — is Blender running with Puree loaded?"; \
		exit 1; \
	fi; \
	echo "Tailing: $$(realpath $$LOG)"; \
	echo "─────────────────────────────────────────"; \
	tail -f "$$LOG"

logs:
	@N=$${N:-50}; \
	LOG="logs/puree.log"; \
	if [ ! -f "$$LOG" ]; then \
		echo "No log file at $$LOG — is Blender running with Puree loaded?"; \
		exit 1; \
	fi; \
	tail -n $$N "$$LOG"

clear-logs:
	@rm -f logs/puree.log logs/puree.log.*
	@echo "✓ Logs cleared"

install-deps:
	@echo "Installing wheel dependencies to $(SITE_PACKAGES)"; \
	BLENDER_PY=$$(find /snap/blender/*/5.*/python/bin/python3.* -type f -executable 2>/dev/null | sort -V | tail -1); \
	if [ -z "$$BLENDER_PY" ]; then \
		BLENDER_PY=$$(which python3); \
		echo "Warning: Blender's Python not found, falling back to system python3"; \
	fi; \
	for whl in wheels/*.whl; do \
		base=$$(basename "$$whl"); \
		case "$$base" in puree_ui-*) echo "  skip $$base (using source symlink)"; continue;; esac; \
		"$$BLENDER_PY" -m pip install --target "$(SITE_PACKAGES)" --no-deps --force-reinstall --quiet "$$whl" 2>/dev/null || true; \
		echo "  ✓ $$base"; \
	done

refresh:
	@if [ -z "$(TARGET)" ]; then echo "Error: TARGET required. Usage: make refresh TARGET=/path/to/project"; exit 1; fi
	@SRC_WHL=$$(ls wheels/puree_ui-*.whl 2>/dev/null | head -1); \
	if [ -z "$$SRC_WHL" ]; then echo "Error: No puree_ui wheel in wheels/. Run 'make build_package' first."; exit 1; fi; \
	if [ ! -f "$(TARGET)/blender_manifest.toml" ]; then echo "Error: No blender_manifest.toml in $(TARGET)"; exit 1; fi; \
	if [ ! -d "$(TARGET)/wheels" ]; then echo "Error: No wheels/ directory in $(TARGET)"; exit 1; fi; \
	rm -f "$(TARGET)/wheels"/puree_ui-*.whl; \
	cp "$$SRC_WHL" "$(TARGET)/wheels/"; \
	echo "✓ Copied $$(basename $$SRC_WHL) → $(TARGET)/wheels/"; \
	$(PYTHON) -c "\
import re, pathlib; \
proj = pathlib.Path('$(TARGET)'); \
manifest = proj / 'blender_manifest.toml'; \
wheels_dir = proj / 'wheels'; \
whl_files = sorted(['./wheels/' + f.name for f in wheels_dir.glob('*.whl')]); \
lines = '\n'.join(f'  \"' + w + '\",' for w in whl_files); \
new_block = f'wheels = [\n{lines}\n]'; \
content = manifest.read_text(); \
content = re.sub(r'wheels\s*=\s*\[.*?\]', new_block, content, flags=re.DOTALL); \
manifest.write_text(content)"; \
	echo "✓ Updated blender_manifest.toml wheels list"; \
	ADDON_ID=$$(grep '^id' "$(TARGET)/blender_manifest.toml" | cut -d'=' -f2 | tr -d ' "'); \
	EXT_LINK="$(EXT_DIR)/$$ADDON_ID"; \
	if [ -L "$$EXT_LINK" ]; then \
		echo "  Project is linked — refreshing site-packages..."; \
		$(PYTHON) -c "\
import zipfile, pathlib, shutil; \
whl = pathlib.Path('$$SRC_WHL'); \
site = pathlib.Path('$(SITE_PACKAGES)'); \
site.mkdir(parents=True, exist_ok=True); \
[shutil.rmtree(old) if old.is_dir() else old.unlink() for old in site.glob('puree_ui-*')]; \
puree_pkg = site / 'puree'; \
shutil.rmtree(puree_pkg) if puree_pkg.is_dir() and not puree_pkg.is_symlink() else None; \
zipfile.ZipFile(whl, 'r').extractall(site); \
print(f'  ✓ Extracted {whl.name} into site-packages')"; \
	fi; \
	echo "Done!"

deploy: link reload

# ── Code formatting ──────────────────────────────────────────────────

format:
	@if [ ! -d .venv ]; then echo "Error: .venv not found. Run 'make venv' first."; exit 1; fi
	@if [ ! -f .venv/bin/ruff ]; then echo "Installing ruff into .venv..."; .venv/bin/pip install ruff --quiet; fi
	@echo "── Stripping Python comments ──"
	@$(PYTHON) dist/format_python.py puree/ __init__.py tests/ dist/ setup.py
	@echo "── Formatting Python (ruff) ──"
	@.venv/bin/ruff format puree/ __init__.py tests/ dist/ setup.py 2>/dev/null || true
	@echo "── Stripping Rust comments ──"
	@$(PYTHON) dist/format_rust.py puree/puree_core/src/
	@echo "── Formatting Rust (rustfmt) ──"
	@find puree/puree_core/src -name '*.rs' -exec rustfmt {} +
	@echo "✓ Format complete"

# ── Venv (for testing CLI locally) ───────────────────────────────────

venv:
	@if [ ! -d .venv ]; then \
		$(PYTHON) -m venv .venv; \
		echo "✓ Created .venv"; \
	fi
	@$(VENV_PIP) install --upgrade pip --quiet
	@$(VENV_PIP) install --editable . --quiet
	@echo "✓ Installed puree CLI in .venv"
	@echo "  Activate: source .venv/bin/activate"
	@echo "  Try:      puree --version"

install: build_package venv
# ── CI checks ────────────────────────────────────────────────────────

ci:
	@VENV=".venv"; \
	if [ ! -d "$$VENV" ]; then echo "Error: .venv not found. Run 'make venv' first."; exit 1; fi; \
	RUFF="$$VENV/bin/ruff"; \
	if [ ! -f "$$RUFF" ]; then echo "Installing ruff into .venv..."; "$$VENV/bin/pip" install ruff --quiet; fi; \
	echo "── Python lint ──"; \
	"$$RUFF" check puree/ __init__.py tests/ dist/ setup.py; \
	echo "── Python format ──"; \
	"$$RUFF" format --check puree/ __init__.py tests/ dist/ setup.py; \
	echo "── Rust checks ──"; \
	cd puree/puree_core && cargo build --release && cargo clippy -- -D warnings && cargo test && cargo fmt -- --check; \
	echo "✓ All checks passed"
# ── Release workflow ─────────────────────────────────────────────────

bump:
ifeq ($(OS),Windows_NT)
	@if not defined VERSION (echo Error: VERSION argument required. Usage: make bump VERSION=0.0.3 && exit /b 1)
else
	@if [ -z "$(VERSION)" ]; then echo "Error: VERSION argument required. Usage: make bump VERSION=0.0.3"; exit 1; fi
endif
	@$(PYTHON) dist/update_version.py $(VERSION)
	@$(MAKE) build_package
	@$(MAKE) build

release:
ifeq ($(OS),Windows_NT)
	@if not defined VERSION (echo Error: VERSION argument required. Usage: make release VERSION=0.0.3 && exit /b 1)
	@echo Releasing v$(VERSION)...
	@$(MAKE) bump VERSION=$(VERSION)
	@git add blender_manifest.toml __init__.py setup.py pyproject.toml
	@git commit -m "Release v$(VERSION)"
	@git tag v$(VERSION)
	@git push origin master --tags
	@echo Pushed v$(VERSION) -- GitHub Actions will build and publish
else
	@if [ -z "$(VERSION)" ]; then echo "Error: VERSION argument required. Usage: make release VERSION=0.0.3"; exit 1; fi
	@echo "Releasing v$(VERSION)..."
	@$(MAKE) bump VERSION=$(VERSION)
	@git add blender_manifest.toml __init__.py setup.py pyproject.toml
	@git commit -m "Release v$(VERSION)"
	@git tag v$(VERSION)
	@git push origin master --tags
	@echo "✓ Pushed v$(VERSION) — GitHub Actions will build and publish"
endif