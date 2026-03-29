#!/usr/bin/env python3
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

try:
    from . import terminal_ui as tui
except ImportError:
    try:
        import terminal_ui as tui
    except ImportError:
        tui = None


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
            capture_output=True,
            text=True,
            timeout=10,
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
            [
                blender_exe,
                "--background",
                "--python-expr",
                "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if re.match(r"^\d+\.\d+$", line):
                return line
    except Exception:
        pass
    return "3.13"


def _find_local_wheels_dir():
    """Return the repo's wheels/ dir if puree is running from a local/editable install.

    Returns None when installed from PyPI (no local source tree available).
    Exits with an error if the dir exists but contains no puree_ui wheel — meaning
    the user needs to run `just build_core && just build_package` first.
    """
    try:
        import puree as _puree_pkg

        candidate = Path(_puree_pkg.__file__).parent.parent / "wheels"
        if not candidate.is_dir():
            return None
        if not list(candidate.glob("puree_ui-*.whl")):
            print(
                "Error: Local wheels/ directory found but contains no puree_ui wheel."
            )
            print("       Run 'just build_core && just build_package' first.")
            sys.exit(1)
        return candidate
    except Exception:
        return None


def _get_addon_id(project_dir):
    """Read the extension ID from blender_manifest.toml."""
    manifest = project_dir / "blender_manifest.toml"
    content = manifest.read_text()
    match = re.search(r'^id\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        print("Error: Could not find 'id' in blender_manifest.toml")
        sys.exit(1)
    return match.group(1)


def _get_blender_paths(blender_exe):
    """Determine Blender extension and site-packages paths from version info."""
    version = _get_blender_version(blender_exe)
    if not version:
        print("Error: Could not determine Blender version.")
        sys.exit(1)

    py_version = _get_blender_python_version(blender_exe)

    system = platform.system()
    if system == "Linux":
        base = Path.home() / ".config" / "blender" / version
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "Blender" / version
    elif system == "Windows":
        base = (
            Path(os.environ.get("APPDATA", ""))
            / "Blender Foundation"
            / "Blender"
            / version
        )
    else:
        print(f"Error: Unsupported platform '{system}'.")
        sys.exit(1)

    ext_path = base / "extensions" / "user_default"
    if system == "Windows":
        site_packages = base / "extensions" / ".local" / "Lib" / "site-packages"
    else:
        site_packages = (
            base
            / "extensions"
            / ".local"
            / "lib"
            / f"python{py_version}"
            / "site-packages"
        )

    return str(ext_path), str(site_packages)


INIT_YAML = textwrap.dedent("""\
    app:
      selected_theme: default_theme
      default_theme: default_theme

      theme:
        - name: default_theme
          author: me
          version: 1.0.0
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
              passive: true
""")

INIT_SCSS = textwrap.dedent("""\
    $pink:  #ff5eac;
    $blue:  #3d7eff;
    $white: #ffffff;

    .root {
        flex-direction:  column;
        justify-content: center;
        align-items:     center;
        width:           100%;
        height:          100%;
        background-color: $pink;
    }

    .hero {
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
    import sys
    import importlib

    # Force-reload puree submodules on Blender script reload
    if "puree" in sys.modules:
        importlib.reload(sys.modules["puree"])

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


def _run_with_progress(tracker, fn, steps, interval=0.8):
    """Run *fn* in a background thread while ticking the progress bar.

    Advances the tracker by up to *steps* increments (one every *interval*
    seconds).  When *fn* finishes, any remaining steps are flushed at once
    so the bar always lands at the expected position.
    """
    result = [None]
    error = [None]

    def _worker():
        try:
            result[0] = fn()
        except Exception as exc:
            error[0] = exc

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    advanced = 0
    while t.is_alive() and advanced < steps - 1:
        time.sleep(interval)
        if t.is_alive() and advanced < steps - 1:
            tracker.advance()
            advanced += 1

    t.join()

    remaining = steps - advanced
    if remaining > 0:
        tracker.advance(remaining)

    if error[0] is not None:
        raise error[0]
    return result[0]


def cmd_init(args):
    """Initialize a new Puree project in the current directory."""
    cwd = Path.cwd()

    if (cwd / "static" / "index.yaml").exists():
        if tui:
            tui.step_fail("A Puree project already exists in this directory")
            tui.step_info("static/index.yaml found")
        else:
            print("Error: A Puree project already exists in this directory.")
            print("       (static/index.yaml found)")
        sys.exit(1)

    if tui:
        tui.print_logo(animate=True)
        tracker = tui.ProgressTracker(total=16)
        tracker.header("Initializing new Puree project")
        tracker.divider()
        tracker.step_info("Detecting Blender...")
    else:
        print("Initializing Puree project...")

    blender_exe = _find_blender()

    if tui:
        py_version = _run_with_progress(
            tracker,
            lambda: _get_blender_python_version(blender_exe),
            steps=8,
        )
        tracker.step("Detected Blender")
        tracker.step_info(f"Blender: {blender_exe}")
        tracker.step_info(f"Python:  {py_version}")
    else:
        py_version = _get_blender_python_version(blender_exe)
        print(f"  Blender: {blender_exe}")
        print(f"  Python:  {py_version}")

    (cwd / "static" / "components").mkdir(parents=True, exist_ok=True)
    (cwd / "wheels").mkdir(exist_ok=True)
    (cwd / "assets").mkdir(exist_ok=True)
    (cwd / "fonts").mkdir(exist_ok=True)

    (cwd / "static" / "index.yaml").write_text(INIT_YAML)
    (cwd / "static" / "style.scss").write_text(INIT_SCSS)
    (cwd / "static" / "script.py").write_text(INIT_SCRIPT)
    (cwd / "__init__.py").write_text(INIT_ENTRY)
    (cwd / "blender_manifest.toml").write_text(_manifest_template(py_version))

    if tui:
        tracker.advance()
        tracker.step("Created project structure")
    else:
        print("  Created project structure")

    scaffold_dir = Path(__file__).parent / "scaffold"
    if scaffold_dir.is_dir():
        for sub in (".agents", ".github"):
            src = scaffold_dir / sub
            dst = cwd / sub
            if src.is_dir() and not dst.exists():
                shutil.copytree(src, dst)
        if tui:
            tracker.advance()
            tracker.step("Created AI configuration (.agents/, .github/)")
        else:
            print("  Created AI configuration (.agents/, .github/)")
    else:
        if tui:
            tracker.advance()

    wheels_dir = cwd / "wheels"
    local_wheels_dir = _find_local_wheels_dir()
    if local_wheels_dir:
        if tui:
            tracker.step_info("Collecting wheels...")

        def _copy_local_wheels():
            whl_list = sorted(local_wheels_dir.glob("*.whl"))
            for whl in whl_list:
                shutil.copy2(whl, wheels_dir / whl.name)
            return whl_list

        if tui:
            wheels_list = _run_with_progress(tracker, _copy_local_wheels, steps=5)
            tracker.step(f"Collected {len(wheels_list)} wheels")
        else:
            wheels_list = _copy_local_wheels()
            for whl in wheels_list:
                print(f"    ✓ {whl.name}")
    else:
        if tui:
            tracker.step_info("Downloading wheels from PyPI...")
        else:
            print("  Collecting wheels...")

        def _download_wheels():
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    "--only-binary=:all:",
                    "--python-version",
                    py_version,
                    "--dest",
                    str(wheels_dir),
                    "puree-ui",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

        try:
            if tui:
                _run_with_progress(tracker, _download_wheels, steps=5)
                tracker.step("Downloaded wheels")
            else:
                _download_wheels()
        except subprocess.CalledProcessError as e:
            if tui:
                tracker.advance(5)
                tracker.step_warn("Failed to download wheels")
                tracker.step_info(
                    f"pip download --only-binary=:all: "
                    f"--python-version {py_version} --dest wheels puree-ui"
                )
            else:
                print(f"  Warning: Failed to download wheels: {e.stderr.strip()}")
                print(
                    "  You can download them manually: pip download --only-binary=:all: "
                    f"--python-version {py_version} --dest wheels puree-ui"
                )

    _update_manifest_wheels(cwd)
    if tui:
        tracker.advance()
        tracker.finish()
        tui.outro_success("Your Puree project is ready!")
        tui.step_info("puree build     — Build the extension zip")
        tui.step_info("puree install   — Install into Blender")
        tui.step_info("Open Blender and look for the Puree tab in the N-panel")
        print()
    else:
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

    if wheel_files:
        wheels_lines = "\n".join(f'  "{whl}",' for whl in wheel_files)
        new_wheels = f"wheels = [\n{wheels_lines}\n]"
    else:
        new_wheels = "wheels = [\n]"

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
        if tui:
            tui.step_fail("blender_manifest.toml not found in current directory")
            tui.step_info("Run 'puree init' first, or cd into your project directory.")
        else:
            print("Error: blender_manifest.toml not found in current directory.")
            print("Run 'puree init' first, or cd into your project directory.")
        sys.exit(1)

    blender_exe = _find_blender()

    content = manifest.read_text()
    name_match = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)

    addon_name = name_match.group(1).replace(" ", "_") if name_match else "addon"
    version = version_match.group(1) if version_match else "0.0.0"

    if tui:
        tui.banner_build()
        tui.step_info(f"Blender: {blender_exe}")
        tui.step_info(f"{addon_name} v{version}")
    else:
        print(f"Building {addon_name} v{version}...")
        print(f"  Blender: {blender_exe}")

    dist_dir = cwd / "dist" / "out"
    dist_dir.mkdir(parents=True, exist_ok=True)

    for old_zip in dist_dir.glob("*.zip"):
        old_zip.unlink()

    output_file = dist_dir / f"{addon_name}_{version}.zip"

    if tui:
        sp = tui.Spinner(
            "Building extension zip", frames=tui.SPINNER_BLOCKS, color=tui.MAGENTA
        )
        sp.start()

    result = subprocess.run(
        [
            blender_exe,
            "--background",
            "--command",
            "extension",
            "build",
            "--source-dir",
            str(cwd),
            "--output-filepath",
            str(output_file),
        ],
        capture_output=True,
        text=True,
    )

    if output_file.exists():
        if tui:
            sp.stop(f"Built {output_file.name}")
            tui.outro_success("Build successful!")
        else:
            print(f"  Output:  {output_file}")
            print("Build successful!")
    else:
        if tui:
            sp.fail("Build failed")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            tui.outro_fail("Build failed")
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
        if tui:
            tui.step_fail("blender_manifest.toml not found in current directory")
            tui.step_info("Run 'puree init' first.")
        else:
            print("Error: blender_manifest.toml not found in current directory.")
            print("Run 'puree init' first.")
        sys.exit(1)

    blender_exe = _find_blender()

    dist_dir = cwd / "dist" / "out"
    zips = sorted(dist_dir.glob("*.zip"))
    if not zips:
        if tui:
            tui.step_fail("No built zip found in dist/out/")
            tui.step_info("Run 'puree build' first.")
        else:
            print("Error: No built zip found in dist/out/. Run 'puree build' first.")
        sys.exit(1)

    package_file = zips[-1]

    if tui:
        tui.banner_install()
        tui.step_info(f"Blender: {blender_exe}")
        tui.step_info(f"Package: {package_file.name}")
    else:
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

    if tui:
        sp = tui.Spinner("Installing into Blender", color=tui.BLUE)
        sp.start()

    result = subprocess.run(
        [blender_exe, "--background", "--python-expr", install_script],
        capture_output=True,
        text=True,
    )

    if "installed and enabled successfully" in result.stdout:
        if tui:
            sp.stop("Extension installed and enabled")
            tui.outro_success("Install successful!")
        else:
            print("Install successful!")
    else:
        if tui:
            sp.fail("Installation may have failed")
            if result.stdout:
                for line in result.stdout.splitlines():
                    if line.strip():
                        tui.step_info(line.strip())
            tui.outro_fail("Install failed")
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


def cmd_link(args):
    """Symlink project into Blender's extensions for development."""
    cwd = Path.cwd()

    manifest = cwd / "blender_manifest.toml"
    if not manifest.exists():
        if tui:
            tui.step_fail("blender_manifest.toml not found in current directory")
            tui.step_info("Run 'puree init' first.")
        else:
            print("Error: blender_manifest.toml not found in current directory.")
            print("Run 'puree init' first.")
        sys.exit(1)

    addon_id = _get_addon_id(cwd)
    blender_exe = _find_blender()

    if tui:
        tui.banner_link()
        tui.step_info(f"Addon:   {addon_id}")
        tui.step_info(f"Blender: {blender_exe}")
    else:
        print(f"Linking {addon_id} for development...")
        print(f"  Blender: {blender_exe}")

    ext_dir, site_packages = _get_blender_paths(blender_exe)
    ext_dir = Path(ext_dir)
    site_packages = Path(site_packages)
    addon_link = ext_dir / addon_id

    ext_dir.mkdir(parents=True, exist_ok=True)

    if addon_link.is_symlink():
        if tui:
            tui.step_info("Symlink already exists, updating...")
        else:
            print("  Symlink already exists, updating...")
        addon_link.unlink()
    elif addon_link.is_dir():
        if tui:
            tui.step_info("Removing installed extension copy...")
        else:
            print("  Removing installed extension copy...")
        shutil.rmtree(addon_link)

    addon_link.symlink_to(cwd)
    if tui:
        tui.step(f"Linked: {addon_link} \u2192 {cwd}")
    else:
        print(f"  \u2713 Linked: {addon_link} \u2192 {cwd}")

    import zipfile

    wheels_dir = cwd / "wheels"
    if wheels_dir.exists() and list(wheels_dir.glob("*.whl")):
        if tui:
            sp = tui.Spinner(
                "Installing wheel dependencies",
                frames=tui.SPINNER_COOK,
                color=tui.CORAL,
            )
            sp.start()
        else:
            print("  Installing wheel dependencies...")
        site_packages.mkdir(parents=True, exist_ok=True)
        whl_count = 0
        for whl in sorted(wheels_dir.glob("*.whl")):
            try:
                with zipfile.ZipFile(whl, "r") as zf:
                    zf.extractall(site_packages)
                whl_count += 1
                if not tui:
                    print(f"    \u2713 {whl.name}")
            except Exception as e:
                if tui:
                    pass
                else:
                    print(f"    \u2717 {whl.name}: {e}")
        if tui:
            sp.stop(f"Installed {whl_count} wheel dependencies")

    if tui:
        tui.outro_success("Dev mode active")
        tui.step_info("Open Blender to load the addon")
        tui.step_info("Use 'puree reload' after code changes")
        print()
    else:
        print()
        print("Dev mode active. Open Blender to load the addon.")
        print("Use 'puree reload' after code changes.")


def cmd_unlink(args):
    """Remove the development symlink from Blender's extensions."""
    cwd = Path.cwd()

    manifest = cwd / "blender_manifest.toml"
    if not manifest.exists():
        if tui:
            tui.step_fail("blender_manifest.toml not found in current directory")
        else:
            print("Error: blender_manifest.toml not found in current directory.")
        sys.exit(1)

    addon_id = _get_addon_id(cwd)
    blender_exe = _find_blender()
    ext_dir, _ = _get_blender_paths(blender_exe)

    if tui:
        tui.banner_unlink()

    addon_link = Path(ext_dir) / addon_id

    if addon_link.is_symlink():
        addon_link.unlink()
        if tui:
            tui.step(f"Removed symlink: {addon_link}")
        else:
            print(f"\u2713 Removed symlink: {addon_link}")
    else:
        if tui:
            tui.step_warn(f"No symlink found at {addon_link}")
        else:
            print(f"No symlink found at {addon_link}")

    if tui:
        tui.step("Dev mode deactivated")
    else:
        print("Dev mode deactivated.")


def cmd_reload(args):
    """Reload addon in a running Blender instance."""
    import socket
    import time

    if tui:
        tui.banner_reload()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect(("127.0.0.1", 19746))
        s.sendall(b"reload")
        resp = s.recv(64).decode("utf-8", errors="ignore").strip()
        s.close()
        if resp == "ok":
            if tui:
                tui.step("Reload triggered (via reload server)")
            else:
                print("[Puree] \u2713 Reload triggered (via reload server)")
            return
    except (ConnectionRefusedError, OSError, socket.timeout):
        pass

    if tui:
        tui.step_warn("Reload server not reachable, using sentinel fallback")
    else:
        print("[Puree] Reload server not reachable, using sentinel fallback...")
    sentinel = Path.cwd() / ".puree_reload"
    sentinel.write_text(str(time.time()))
    if tui:
        tui.step("Sentinel written \u2014 Blender will pick this up within ~2s")
    else:
        print(
            "[Puree] \u2713 Sentinel written \u2014 Blender will pick this up within ~2s"
        )


def main():
    parser = argparse.ArgumentParser(
        prog="puree",
        description="Puree UI — Bootstrap, build, and install Blender addons",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"puree {_get_version()}",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "init", help="Initialize a new Puree project in the current directory"
    )
    subparsers.add_parser("build", help="Build the extension zip using Blender on PATH")
    subparsers.add_parser("install", help="Install the built extension into Blender")
    subparsers.add_parser("link", help="Symlink project into Blender for development")
    subparsers.add_parser("unlink", help="Remove the development symlink")
    subparsers.add_parser("reload", help="Reload addon in a running Blender instance")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "init": cmd_init,
        "build": cmd_build,
        "install": cmd_install,
        "link": cmd_link,
        "unlink": cmd_unlink,
        "reload": cmd_reload,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
