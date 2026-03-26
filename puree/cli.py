#!/usr/bin/env python3
"""
Puree CLI — Bootstrap, build, and install Puree UI addons for Blender.

Usage:
    puree init              Initialize a new Puree project in the current directory
    puree build             Build the extension zip using Blender on PATH
    puree install           Install the built extension into Blender
    puree --version         Show version
    puree --help            Show this help
"""
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path


def _get_version():
    """Read version from the installed puree package metadata or fallback."""
    try:
        from importlib.metadata import version
        return version("puree-ui")
    except Exception:
        return "dev"


def _find_blender():
    """Find the blender executable on PATH."""
    blender = shutil.which("blender")
    if blender is None:
        print("Error: 'blender' not found on PATH.")
        print("Make sure Blender is installed and available in your system PATH.")
        sys.exit(1)
    return blender


def _get_blender_version(blender_exe):
    """Get the major.minor version string from blender."""
    try:
        result = subprocess.run(
            [blender_exe, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        match = re.search(r"Blender\s+(\d+\.\d+)", result.stdout)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def _get_blender_python_version(blender_exe):
    """Get the Python version bundled with Blender (e.g. '3.13')."""
    try:
        result = subprocess.run(
            [blender_exe, "--background", "--python-expr",
             "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            capture_output=True, text=True, timeout=30,
        )
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if re.match(r"^\d+\.\d+$", line):
                return line
    except Exception:
        pass
    return "3.13"


# ── Templates ────────────────────────────────────────────────────────

INIT_YAML = textwrap.dedent("""\
    app:
      selected_theme: default_theme
      default_theme: default_theme

      theme:
        - name: default_theme
          author: me
          version: 1.0.0
          default_font: NeueMontreal-Regular
          scripts:
            - static/script.py
          styles:
            - static/style.scss
          components: static/components/

          root:
            class: root

            hero:
              class: hero
              text: PUREE
              font: NeueMontreal-Bold
              passive: true
""")

INIT_SCSS = textwrap.dedent("""\
    $pink:  #ff5eac;
    $blue:  #3d7eff;
    $white: #ffffff;

    root {
        flex-direction:  column;
        justify-content: center;
        align-items:     center;
        width:           100%;
        height:          100%;
        background-color: $pink;
    }

    hero {
        width:           80%;
        height:          40%;
        justify-content: center;
        align-items:     center;
        border-radius:   16px;
        color:           $blue;
        font-size:       72px;
        text-align:      center;
    }
""")

INIT_SCRIPT = textwrap.dedent("""\
    def main(self, app):
        \"\"\"Entry point — called once when the UI loads.\"\"\"
        return app
""")

INIT_ENTRY = textwrap.dedent("""\
    import bpy
    import os
    from puree import register as xwz_ui_register, unregister as xwz_ui_unregister
    from puree import set_addon_root

    bl_info = {
        "name"       : "My Puree Addon",
        "author"     : "me",
        "version"    : (0, 1, 0),
        "blender"    : (5, 1, 0),
        "location"   : "3D View > Sidebar > Puree",
        "description": "A Puree UI addon",
        "category"   : "Interface"
    }

    def register():
        set_addon_root(os.path.dirname(os.path.abspath(__file__)))
        xwz_ui_register()
        wm = bpy.context.window_manager
        wm.xwz_ui_conf_path = "static/index.yaml"
        wm.xwz_debug_panel  = True
        wm.xwz_auto_start   = True

    def unregister():
        xwz_ui_unregister()

    if __name__ == "__main__":
        register()
""")


def _manifest_template(py_version):
    """Generate blender_manifest.toml with correct wheel filenames for the platform."""
    # Determine platform tag for wheels
    system = platform.system()
    machine = platform.machine()
    if system == "Linux" and machine == "x86_64":
        plat_tag = "manylinux_2_17_x86_64.manylinux2014_x86_64"
        cp_plat = f"cp{py_version.replace('.', '')}-cp{py_version.replace('.', '')}-{plat_tag}"
        gl_plat = f"cp{py_version.replace('.', '')}-cp{py_version.replace('.', '')}-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64"
        yaml_plat = f"cp{py_version.replace('.', '')}-cp{py_version.replace('.', '')}-{plat_tag}"
        stretch_plat = f"cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64"
        moderngl_plat = f"cp{py_version.replace('.', '')}-cp{py_version.replace('.', '')}-{plat_tag}"
        blender_platforms = '  "linux-x64",'
    elif system == "Windows":
        cp = f"cp{py_version.replace('.', '')}"
        cp_plat = f"{cp}-{cp}-win_amd64"
        gl_plat = cp_plat
        yaml_plat = cp_plat
        stretch_plat = "cp38-abi3-win_amd64"
        moderngl_plat = cp_plat
        blender_platforms = '  "windows-x64",'
    elif system == "Darwin":
        cp = f"cp{py_version.replace('.', '')}"
        if machine == "arm64":
            mac_tag = "macosx_11_0_arm64"
            blender_platforms = '  "macos-arm64",'
        else:
            mac_tag = "macosx_10_9_x86_64"
            blender_platforms = '  "macos-x64",'
        cp_plat = f"{cp}-{cp}-{mac_tag}"
        gl_plat = cp_plat
        yaml_plat = cp_plat
        stretch_plat = f"cp38-abi3-{mac_tag}"
        moderngl_plat = cp_plat
    else:
        # Fallback — user will need to fix
        cp_plat = "FIXME"
        gl_plat = "FIXME"
        yaml_plat = "FIXME"
        stretch_plat = "FIXME"
        moderngl_plat = "FIXME"
        blender_platforms = '  "linux-x64",'

    return textwrap.dedent(f"""\
        schema_version = "1.0.0"

        id         = "my_puree_addon"
        version    = "0.1.0"
        name       = "My Puree Addon"
        tagline    = "A Puree UI addon"
        maintainer = "me"
        type       = "add-on"

        blender_version_min = "5.1.0"

        license = [
          "SPDX:GPL-3.0-or-later",
        ]

        copyright = [
          "2026 me",
        ]

        platforms = [
        {blender_platforms}
        ]

        wheels = [
        ]

        [build]
        paths_exclude_pattern = [
          "__pycache__/",
          "*.zip",
          "*.pyc",
          ".gitignore",
          ".vscode/",
          ".git/",
        ]
    """)


# ── Commands ─────────────────────────────────────────────────────────

def cmd_init(args):
    """Initialize a new Puree project in the current directory."""
    cwd = Path.cwd()

    # Safety check — don't overwrite existing project
    if (cwd / "static" / "index.yaml").exists():
        print("Error: A Puree project already exists in this directory.")
        print("       (static/index.yaml found)")
        sys.exit(1)

    print("Initializing Puree project...")

    # Find blender to determine Python version for wheels
    blender_exe = _find_blender()
    py_version = _get_blender_python_version(blender_exe)
    print(f"  Blender: {blender_exe}")
    print(f"  Python:  {py_version}")

    # Create directory structure
    (cwd / "static" / "components").mkdir(parents=True, exist_ok=True)
    (cwd / "wheels").mkdir(exist_ok=True)
    (cwd / "assets").mkdir(exist_ok=True)
    (cwd / "fonts").mkdir(exist_ok=True)

    # Write template files
    (cwd / "static" / "index.yaml").write_text(INIT_YAML)
    (cwd / "static" / "style.scss").write_text(INIT_SCSS)
    (cwd / "static" / "script.py").write_text(INIT_SCRIPT)
    (cwd / "__init__.py").write_text(INIT_ENTRY)
    (cwd / "blender_manifest.toml").write_text(_manifest_template(py_version))

    print("  Created project structure")

    # Download wheels
    print("  Downloading wheels...")
    wheels_dir = cwd / "wheels"
    try:
        subprocess.run(
            [
                sys.executable, "-m", "pip", "download",
                "--only-binary=:all:",
                "--python-version", py_version,
                "--dest", str(wheels_dir),
                "puree-ui",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"  Warning: Failed to download wheels: {e.stderr.strip()}")
        print("  You can download them manually: pip download --only-binary=:all: "
              f"--python-version {py_version} --dest wheels puree-ui")

    # Update manifest with actual wheel filenames
    _update_manifest_wheels(cwd)

    print()
    print("Done! Your Puree project is ready.")
    print()
    print("Next steps:")
    print(f"  1. puree build     — Build the extension zip")
    print(f"  2. puree install   — Install into Blender")
    print(f"  3. Open Blender and look for the Puree tab in the N-panel")
    print()


def _update_manifest_wheels(project_dir):
    """Update the wheels list in blender_manifest.toml to match actual wheel files."""
    manifest_path = project_dir / "blender_manifest.toml"
    wheels_dir = project_dir / "wheels"

    if not manifest_path.exists():
        return

    wheel_files = sorted([f"./wheels/{f.name}" for f in wheels_dir.glob("*.whl")])

    content = manifest_path.read_text()

    # Build new wheels block
    if wheel_files:
        wheels_lines = "\n".join(f'  "{whl}",' for whl in wheel_files)
        new_wheels = f"wheels = [\n{wheels_lines}\n]"
    else:
        new_wheels = "wheels = [\n]"

    # Replace the wheels section
    content = re.sub(
        r"wheels\s*=\s*\[.*?\]",
        new_wheels,
        content,
        flags=re.DOTALL,
    )

    manifest_path.write_text(content)


def cmd_build(args):
    """Build the extension zip using Blender on PATH."""
    cwd = Path.cwd()

    manifest = cwd / "blender_manifest.toml"
    if not manifest.exists():
        print("Error: blender_manifest.toml not found in current directory.")
        print("Run 'puree init' first, or cd into your project directory.")
        sys.exit(1)

    blender_exe = _find_blender()

    # Parse addon name and version from manifest
    content = manifest.read_text()
    name_match = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)

    addon_name = name_match.group(1).replace(" ", "_") if name_match else "addon"
    version = version_match.group(1) if version_match else "0.0.0"

    # Create dist directory
    dist_dir = cwd / "dist"
    dist_dir.mkdir(exist_ok=True)

    # Clean old zips
    for old_zip in dist_dir.glob("*.zip"):
        old_zip.unlink()

    output_file = dist_dir / f"{addon_name}_{version}.zip"

    print(f"Building {addon_name} v{version}...")
    print(f"  Blender: {blender_exe}")

    result = subprocess.run(
        [blender_exe, "--background", "--command", "extension", "build",
         "--source-dir", str(cwd), "--output-filepath", str(output_file)],
        capture_output=True, text=True,
    )

    if output_file.exists():
        print(f"  Output:  {output_file}")
        print("Build successful!")
    else:
        print("Build failed!")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        sys.exit(1)


def cmd_install(args):
    """Install the built extension into Blender."""
    cwd = Path.cwd()

    manifest = cwd / "blender_manifest.toml"
    if not manifest.exists():
        print("Error: blender_manifest.toml not found in current directory.")
        print("Run 'puree init' first.")
        sys.exit(1)

    blender_exe = _find_blender()

    # Find the zip
    dist_dir = cwd / "dist"
    zips = sorted(dist_dir.glob("*.zip"))
    if not zips:
        print("Error: No built zip found in dist/. Run 'puree build' first.")
        sys.exit(1)

    package_file = zips[-1]  # Latest

    print(f"Installing {package_file.name}...")
    print(f"  Blender: {blender_exe}")

    install_script = textwrap.dedent(f"""\
        import bpy
        try:
            bpy.ops.extensions.package_install_files(
                filepath=r'{package_file}',
                repo='user_default',
                enable_on_install=True,
            )
            print('Extension installed and enabled successfully')
        except Exception as e:
            print(f'Installation failed: {{e}}')
            raise SystemExit(1)
    """)

    result = subprocess.run(
        [blender_exe, "--background", "--python-expr", install_script],
        capture_output=True, text=True,
    )

    if "installed and enabled successfully" in result.stdout:
        print("Install successful!")
    else:
        print("Install may have failed. Blender output:")
        if result.stdout:
            for line in result.stdout.splitlines():
                if line.strip():
                    print(f"  {line}")
        if result.stderr:
            for line in result.stderr.splitlines():
                if line.strip():
                    print(f"  {line}")
        sys.exit(1)


# ── Entry Point ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="puree",
        description="Puree UI — Bootstrap, build, and install Blender addons",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"puree {_get_version()}",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Initialize a new Puree project in the current directory")
    subparsers.add_parser("build", help="Build the extension zip using Blender on PATH")
    subparsers.add_parser("install", help="Install the built extension into Blender")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "init": cmd_init,
        "build": cmd_build,
        "install": cmd_install,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
