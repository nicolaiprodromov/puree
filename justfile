set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

python := if os() == "windows" { "python" } else { "python3" }
build_cmd := if os() == "windows" { "./build" } else { "./build.sh" }
timeout_cmd := if os() == "windows" { "timeout /t 1 /nobreak" } else { "sleep 1" }

build:
    @cd dist; {{build_cmd}}

install:
    @cd dist; {{python}} install.py install

uninstall:
    @cd dist; {{python}} install.py uninstall

wheels:
    @cd puree/wheels; {{python}} download_wheels.py

deploy:
    just wheels
    just build
    @{{timeout_cmd}}
    just uninstall
    @{{timeout_cmd}}
    just install

update_version VERSION:
    @{{python}} dist/update_version.py {{VERSION}}
