.PHONY: build install uninstall deploy wheels update_version build_package

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
	@echo "Building Python package..."
	@echo "Cleaning up old packages..."
	@rm -f dist/*.tar.gz
	@$(PYTHON) setup.py sdist bdist_wheel
	@echo "Moving wheel to puree/wheels..."
	@mv dist/puree_ui-*.whl puree/wheels/ 2>/dev/null || true
	@echo "Cleaning up build artifacts..."
	@rm -rf build *.egg-info
	@echo "Package built successfully!"

deploy:
	@$(TIMEOUT)
	make uninstall
	@$(TIMEOUT)
	make install

update_version:
ifeq ($(OS),Windows_NT)
	@if not defined VERSION (echo Error: VERSION argument required. Usage: make update_version VERSION=0.0.3 && exit /b 1)
	@$(PYTHON) dist/update_version.py $(VERSION)
else
	@if [ -z "$(VERSION)" ]; then echo "Error: VERSION argument required. Usage: make update_version VERSION=0.0.3"; exit 1; fi
	@$(PYTHON) dist/update_version.py $(VERSION)
endif