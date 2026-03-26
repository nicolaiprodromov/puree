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
.PHONY: build build_core build_package wheels link unlink reload tail logs clear-logs deploy install install-deps venv bump release

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
	mkdir -p "$(ADDON_DIR)/dist"; \
	rm -f "$(ADDON_DIR)/dist"/*.zip; \
	OUTPUT="$(ADDON_DIR)/dist/$${ADDON_NAME}_$${VERSION}.zip"; \
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

deploy: link reload

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

install: venv

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
	@echo Updating version to $(VERSION)...
	@$(MAKE) bump VERSION=$(VERSION)
	@echo Committing version bump...
	@git add blender_manifest.toml __init__.py setup.py pyproject.toml
	@git commit -m "Bump version to $(VERSION)"
	@git push origin master
	@echo Building and releasing v$(VERSION)...
	@cd dist && $(PYTHON) release.py $(VERSION)
	@echo Release v$(VERSION) completed!
else
	@if [ -z "$(VERSION)" ]; then echo "Error: VERSION argument required. Usage: make release VERSION=0.0.3"; exit 1; fi
	@echo "Updating version to $(VERSION)..."
	@$(MAKE) bump VERSION=$(VERSION)
	@echo "Committing version bump..."
	@git add blender_manifest.toml __init__.py setup.py pyproject.toml
	@git commit -m "Bump version to $(VERSION)"
	@git push origin master
	@echo "Building and releasing v$(VERSION)..."
	@cd dist && $(PYTHON) release.py $(VERSION)
	@echo "Release v$(VERSION) completed!"
endif