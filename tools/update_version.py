import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import addon_paths  # sibling tools script

from puree.log import setup_cli_logging

logger = setup_cli_logging(os.path.splitext(os.path.basename(__file__))[0])


def update_version(version):
    root = addon_paths.PROJECT_ROOT
    # The addon (manifest + bl_info) lives under tests/, the package metadata at the root.
    manifest_path = str(addon_paths.MANIFEST)
    init_path = str(addon_paths.ADDON_INIT)
    setup_path = str(root / "setup.py")
    pyproject_path = str(root / "pyproject.toml")
    cargo_toml_path = str(root / "puree" / "puree_core" / "Cargo.toml")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_content = f.read()

    # Every substitution keeps the file's own spacing (capture group 1) so a bump
    # never produces a diff that `ruff format --check` rejects in CI.
    manifest_content = re.sub(
        r'^(version\s*=\s*)"[^"]*"',
        rf'\g<1>"{version}"',
        manifest_content,
        flags=re.MULTILINE,
    )

    manifest_content = re.sub(
        r'"\./wheels/puree_ui-[^"]*-py3-none-any\.whl"',
        f'"./wheels/puree_ui-{version}-py3-none-any.whl"',
        manifest_content,
    )

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)

    with open(init_path, "r", encoding="utf-8") as f:
        init_content = f.read()

    version_tuple = "(" + ", ".join(version.split(".")) + ")"
    init_content = re.sub(r'("version"\s*:\s*)\([^)]*\)', rf"\g<1>{version_tuple}", init_content)

    with open(init_path, "w", encoding="utf-8") as f:
        f.write(init_content)

    with open(setup_path, "r", encoding="utf-8") as f:
        setup_content = f.read()

    setup_content = re.sub(
        r'(version\s*=\s*)"[^"]*"',
        rf'\g<1>"{version}"',
        setup_content,
    )

    with open(setup_path, "w", encoding="utf-8") as f:
        f.write(setup_content)

    with open(pyproject_path, "r", encoding="utf-8") as f:
        pyproject_content = f.read()

    pyproject_content = re.sub(
        r'^(version\s*=\s*)"[^"]*"',
        rf'\g<1>"{version}"',
        pyproject_content,
        flags=re.MULTILINE,
    )

    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(pyproject_content)

    with open(cargo_toml_path, "r", encoding="utf-8") as f:
        cargo_content = f.read()

    cargo_content = re.sub(
        r'^(version\s*=\s*)"[^"]*"',
        rf'\g<1>"{version}"',
        cargo_content,
        flags=re.MULTILINE,
    )

    with open(cargo_toml_path, "w", encoding="utf-8") as f:
        f.write(cargo_content)

    logger.info(f"Version updated to {version} in all files")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("Error: VERSION argument required")
        sys.exit(1)

    update_version(sys.argv[1])
