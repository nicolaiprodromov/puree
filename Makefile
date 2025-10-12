.PHONY: build install uninstall deploy wheels update_version

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

deploy:
	make wheels
	make build
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