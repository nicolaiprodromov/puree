import sys
import re

def update_version(version):
    manifest_path = 'blender_manifest.toml'
    init_path = '__init__.py'
    
    with open(manifest_path, 'r') as f:
        manifest_content = f.read()
    
    manifest_content = re.sub(
        r'^version\s*=\s*"[^"]*"',
        f'version    = "{version}"',
        manifest_content,
        flags=re.MULTILINE
    )
    
    with open(manifest_path, 'w') as f:
        f.write(manifest_content)
    
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
    
    print(f"Version updated to {version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Error: VERSION argument required")
        sys.exit(1)
    
    update_version(sys.argv[1])
