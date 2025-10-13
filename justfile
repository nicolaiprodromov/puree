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

build_package:
    @cd dist; {{python}} build_package.py

deploy:
    just build_package
    @{{timeout_cmd}}
    just build
    @{{timeout_cmd}}
    just uninstall
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
