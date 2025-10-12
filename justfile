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

release VERSION:
    @echo "Updating version to {{VERSION}}..."
    just update_version {{VERSION}}
    @echo "Committing version bump..."
    git add blender_manifest.toml __init__.py
    git commit -m "Bump version to {{VERSION}}"
    @echo "Creating and pushing tag v{{VERSION}}..."
    git tag v{{VERSION}}
    git push origin master
    git push origin v{{VERSION}}
    @echo "Release v{{VERSION}} triggered! Check GitHub Actions for build status."
