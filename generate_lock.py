#!/usr/bin/env python3
"""
Generate Pipfile.lock with SHA256 hashes from local wheel files.
This script computes hashes for all wheels in src/wheels/ directory.
"""

import hashlib
import json
import os
from pathlib import Path


def compute_sha256(filepath):
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # Read file in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def parse_wheel_name(wheel_name):
    """
    Parse wheel filename to extract package name and version.
    Format: {distribution}-{version}(-{build})?-{python}-{abi}-{platform}.whl
    """
    parts = wheel_name.replace('.whl', '').split('-')
    
    # Handle packages with underscores or hyphens in name
    if len(parts) >= 5:
        name = parts[0]
        version = parts[1]
        return name.lower().replace('_', '-'), version
    return None, None


def main():
    wheels_dir = Path(__file__).parent / "src" / "wheels"
    
    if not wheels_dir.exists():
        print(f"Error: {wheels_dir} does not exist")
        return
    
    # Collect all wheels
    packages = {}
    
    for wheel_file in wheels_dir.glob("*.whl"):
        package_name, version = parse_wheel_name(wheel_file.name)
        
        if not package_name or not version:
            print(f"Warning: Could not parse {wheel_file.name}")
            continue
        
        # Compute hash
        file_hash = compute_sha256(wheel_file)
        hash_str = f"sha256:{file_hash}"
        
        print(f"Processing: {package_name}=={version}")
        print(f"  File: {wheel_file.name}")
        print(f"  Hash: {hash_str}")
        
        # Store package info (use latest version if multiple exist)
        if package_name not in packages:
            packages[package_name] = {
                "version": version,
                "hashes": [],
                "files": []
            }
        
        # Add hash if not duplicate
        if hash_str not in packages[package_name]["hashes"]:
            packages[package_name]["hashes"].append(hash_str)
            packages[package_name]["files"].append(wheel_file.name)
    
    # Generate Pipfile.lock structure
    pipfile_lock = {
        "_meta": {
            "hash": {
                "sha256": "computed_from_pipfile"
            },
            "pipfile-spec": 6,
            "requires": {
                "python_version": "3.11"
            },
            "sources": [
                {
                    "name": "pypi",
                    "url": "https://pypi.org/simple",
                    "verify_ssl": True
                }
            ]
        },
        "default": {},
        "develop": {}
    }
    
    # Add packages to lock file
    for package_name, info in sorted(packages.items()):
        pipfile_lock["default"][package_name] = {
            "hashes": info["hashes"],
            "version": f"=={info['version']}",
            "files": info["files"]  # Added for reference
        }
        
        # Add markers for platform-specific packages
        if package_name in ["moderngl", "glcontext"]:
            pipfile_lock["default"][package_name]["markers"] = "python_version >= '3.11'"
        elif package_name == "stretchable":
            pipfile_lock["default"][package_name]["markers"] = "python_version >= '3.8'"
    
    # Add numpy (not in wheels, will need to be installed separately)
    if "numpy" not in pipfile_lock["default"]:
        pipfile_lock["default"]["numpy"] = {
            "hashes": [],
            "version": ">=1.20.0",
            "markers": "python_version >= '3.11'"
        }
    
    # Write to file
    output_file = Path(__file__).parent / "Pipfile.lock"
    with open(output_file, 'w') as f:
        json.dump(pipfile_lock, f, indent=4)
    
    print(f"\n✅ Generated {output_file}")
    print(f"📦 Total packages: {len(packages)}")
    print("\nPackages included:")
    for package_name in sorted(packages.keys()):
        print(f"  - {package_name} == {packages[package_name]['version']}")


if __name__ == "__main__":
    main()
