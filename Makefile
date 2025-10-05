.PHONY: build install uninstall deploy

build:
	@cd dist && build

install:
	@cd dist && python install.py install

uninstall:
	@cd dist && python install.py uninstall

deploy:
# 	black .
	@cd dist && build
	timeout /t 2 /nobreak
	@cd dist && python install.py