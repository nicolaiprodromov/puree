.PHONY: build install uninstall deploy wheels

ifeq ($(OS),Windows_NT)
PYTHON := python
TIMEOUT := timeout /t 1 /nobreak
BUILD := build.bat
else
PYTHON := python3
TIMEOUT := sleep 1
BUILD := ./build.sh
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