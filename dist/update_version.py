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
import sys
import re

def update_version(version):
    manifest_path   = 'blender_manifest.toml'
    init_path       = '__init__.py'
    setup_path      = 'setup.py'
    pyproject_path  = 'pyproject.toml'
    cargo_toml_path = 'puree/puree_core/Cargo.toml'
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest_content = f.read()
    
    manifest_content = re.sub(
        r'^version\s*=\s*"[^"]*"',
        f'version    = "{version}"',
        manifest_content,
        flags=re.MULTILINE
    )
    
    manifest_content = re.sub(
        r'"\./wheels/puree_ui-[^"]*-py3-none-any\.whl"',
        f'"./wheels/puree_ui-{version}-py3-none-any.whl"',
        manifest_content
    )
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(manifest_content)
    
    with open(init_path, 'r', encoding='utf-8') as f:
        init_content = f.read()
    
    version_tuple = '(' + ', '.join(version.split('.')) + ')'
    init_content = re.sub(
        r'"version"\s*:\s*\([^)]*\)',
        f'"version"    : {version_tuple}',
        init_content
    )
    
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    with open(setup_path, 'r', encoding='utf-8') as f:
        setup_content = f.read()
    
    setup_content = re.sub(
        r'version\s*=\s*"[^"]*"',
        f'version                       = "{version}"',
        setup_content
    )
    
    with open(setup_path, 'w', encoding='utf-8') as f:
        f.write(setup_content)
    
    with open(pyproject_path, 'r', encoding='utf-8') as f:
        pyproject_content = f.read()
    
    pyproject_content = re.sub(
        r'^version\s*=\s*"[^"]*"',
        f'version = "{version}"',
        pyproject_content,
        flags=re.MULTILINE
    )
    
    with open(pyproject_path, 'w', encoding='utf-8') as f:
        f.write(pyproject_content)
    
    with open(cargo_toml_path, 'r', encoding='utf-8') as f:
        cargo_content = f.read()
    
    cargo_content = re.sub(
        r'^version\s*=\s*"[^"]*"',
        f'version = "{version}"',
        cargo_content,
        flags=re.MULTILINE
    )
    
    with open(cargo_toml_path, 'w', encoding='utf-8') as f:
        f.write(cargo_content)
    
    print(f"Version updated to {version} in all files")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Error: VERSION argument required")
        sys.exit(1)
    
    update_version(sys.argv[1])
