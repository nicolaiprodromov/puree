import sys
import re

def update_version(version):
    manifest_path = 'blender_manifest.toml'
    init_path = '__init__.py'
    setup_path = 'setup.py'
    pyproject_path = 'pyproject.toml'
    
    # Update blender_manifest.toml
    with open(manifest_path, 'r') as f:
        manifest_content = f.read()
    
    manifest_content = re.sub(
        r'^version\s*=\s*"[^"]*"',
        f'version    = "{version}"',
        manifest_content,
        flags=re.MULTILINE
    )
    
    # Update puree_ui wheel filename
    manifest_content = re.sub(
        r'"\./wheels/puree_ui-[^"]*-py3-none-any\.whl"',
        f'"./wheels/puree_ui-{version}-py3-none-any.whl"',
        manifest_content
    )
    
    with open(manifest_path, 'w') as f:
        f.write(manifest_content)
    
    # Update __init__.py
    with open(init_path, 'r') as f:
        init_content = f.read()
    
    version_tuple = '(' + ', '.join(version.split('.')) + ')'
    init_content = re.sub(
        r'"version"\s*:\s*\([^)]*\)',
        f'"version"    : {version_tuple}',
        init_content
    )
    
    with open(init_path, 'w') as f:
        f.write(init_content)
    
    # Update setup.py
    with open(setup_path, 'r') as f:
        setup_content = f.read()
    
    setup_content = re.sub(
        r'version\s*=\s*"[^"]*"',
        f'version                       = "{version}"',
        setup_content
    )
    
    with open(setup_path, 'w') as f:
        f.write(setup_content)
    
    # Update pyproject.toml
    with open(pyproject_path, 'r') as f:
        pyproject_content = f.read()
    
    pyproject_content = re.sub(
        r'^version\s*=\s*"[^"]*"',
        f'version = "{version}"',
        pyproject_content,
        flags=re.MULTILINE
    )
    
    with open(pyproject_path, 'w') as f:
        f.write(pyproject_content)
    
    print(f"Version updated to {version} in all files")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Error: VERSION argument required")
        sys.exit(1)
    
    update_version(sys.argv[1])
