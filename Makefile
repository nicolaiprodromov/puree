.PHONY: build install uninstall deploy wheels build_package bump release

ifeq ($(OS),Windows_NT)
PYTHON := python
TIMEOUT := timeout /t 1 /nobreak
BUILD := build.bat
SED := powershell -Command "(Get-Content
else
PYTHON := python3
TIMEOUT := sleep 1
BUILD := ./build.sh
SED := sed -i
endif

build:
	@cd dist && $(BUILD)

install:
	@cd dist && $(PYTHON) install.py install

uninstall:
	@cd dist && $(PYTHON) install.py uninstall

wheels:
	@cd puree/wheels && $(PYTHON) download_wheels.py

build_package:
	@cd dist && $(PYTHON) build_package.py

deploy:
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