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
.PHONY: build install uninstall deploy wheels build_package bump release build_rust

ifeq ($(OS),Windows_NT)
PYTHON := python
TIMEOUT := timeout /t 1 /nobreak
BUILD := build.bat
BUILD_CORE := build.bat
SED := powershell -Command "(Get-Content
else
PYTHON := python3
TIMEOUT := sleep 1
BUILD := ./build.sh
BUILD_CORE := ./build.sh
SED := sed -i
endif

build_core:
	@cd puree/puree_core && $(BUILD_CORE)

build_package:
	@cd dist && $(PYTHON) build_package.py

build:
	@cd dist && $(BUILD)

install:
	@cd dist && $(PYTHON) install.py install

uninstall:
	@cd dist && $(PYTHON) install.py uninstall

wheels:
	@pip download --only-binary=:all: --python-version 3.11 --dest wheels puree-ui
	@$(PYTHON) dist/update_wheels.py


deploy:
	make build_core
	@$(TIMEOUT)
	make build_package
	@$(TIMEOUT)
	make build
	@$(TIMEOUT)
	make uninstall
	@$(TIMEOUT)
	make install

bump:
ifeq ($(OS),Windows_NT)
	@if not defined VERSION (echo Error: VERSION argument required. Usage: make bump VERSION=0.0.3 && exit /b 1)
	@$(PYTHON) dist/update_version.py $(VERSION)
	@make build_package
	@cd dist && $(BUILD)
else
	@if [ -z "$(VERSION)" ]; then echo "Error: VERSION argument required. Usage: make bump VERSION=0.0.3"; exit 1; fi
	@$(PYTHON) dist/update_version.py $(VERSION)
	@make build_package
	@cd dist && $(BUILD)
endif

release:
ifeq ($(OS),Windows_NT)
	@if not defined VERSION (echo Error: VERSION argument required. Usage: make release VERSION=0.0.3 && exit /b 1)
	@echo Updating version to $(VERSION)...
	@make bump VERSION=$(VERSION)
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
	@make bump VERSION=$(VERSION)
	@echo "Committing version bump..."
	@git add blender_manifest.toml __init__.py setup.py pyproject.toml
	@git commit -m "Bump version to $(VERSION)"
	@git push origin master
	@echo "Building and releasing v$(VERSION)..."
	@cd dist && $(PYTHON) release.py $(VERSION)
	@echo "Release v$(VERSION) completed!"
endif