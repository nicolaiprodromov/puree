#!/usr/bin/env python3
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
import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import textwrap
import threading
import zipfile
from pathlib import Path

DOCS_URL = "https://github.com/nicolaiprodromov/puree"
TAGLINE = "Declarative, GPU-accelerated UI for Blender addons"

# terminal_ui ships in the same package; the fallback shim only exists so a
# vendored/broken install still gets working (plain) output.
try:
    from . import terminal_ui as tui
except ImportError:
    try:
        import terminal_ui as tui
    except ImportError:
        tui = None


class _PlainTask:
    def __init__(self, msg):
        self.msg = msg
        print(f"* {msg} ...")

    def update(self, msg):
        self.msg = msg
        return self

    def progress(self, *a, **k):
        return self

    def log(self, *a, **k):
        return self

    def done(self, msg=None, meta=None):
        print(f"+ {msg or self.msg}" + (f" ({meta})" if meta else ""))

    def warn(self, msg=None, meta=None):
        print(f"! {msg or self.msg}")

    def fail(self, msg=None, meta=None):
        print(f"x {msg or self.msg}")


class _PlainTUI:
    """Bare-bones stand-in when terminal_ui cannot be imported."""

    RESET = BOLD = DIM = PINK = GREEN = YELLOW = RED = WHITE = GREY = DARK = ""

    def begin(self, command, version=None):
        print(f"puree {command}" + (f" v{version}" if version else ""))

    def step(self, msg, meta=None):
        print(f"+ {msg}" + (f" ({meta})" if meta else ""))

    def step_info(self, msg, meta=None):
        print(f"- {msg}" + (f" ({meta})" if meta else ""))

    def step_warn(self, msg, meta=None):
        print(f"! {msg}")

    def step_fail(self, msg, meta=None):
        print(f"x {msg}")

    def detail(self, text):
        print(f"    {text}")

    def details(self, pairs):
        for k, v in pairs:
            print(f"    {k}: {v}")

    def finish(self, msg):
        print(f"= {msg}")

    def finish_fail(self, msg):
        print(f"= {msg}")

    def note(self, title, rows):
        print(f"\n{title}:")
        for i, row in enumerate(rows, 1):
            print(f"  {i}. {row[0]}  {row[1]}" if isinstance(row, tuple) else f"  {i}. {row}")

    def hint(self, text):
        print(f"  {text}")

    def task(self, msg, **kwargs):
        return _PlainTask(msg)

    def print_logo(self, animate=True, tagline=None):
        if tagline:
            print(f"puree — {tagline}")

    def wordmark(self):
        return "puree"

    def print_stdout(self, text):
        sys.stdout.write(re.sub(r"\033\[[0-9;?]*[A-Za-z]", "", text))

    @staticmethod
    def fmt_size(n):
        return f"{n / 1024:.1f} KB" if n < 1024 * 1024 else f"{n / (1024 * 1024):.1f} MB"

    @staticmethod
    def fmt_duration(s):
        return f"{s:.1f}s"


if tui is None:
    tui = _PlainTUI()


def _get_version():
    """Version from installed metadata, the repo pyproject.toml, or 'dev'."""
    try:
        from importlib.metadata import version

        return version("puree-ui")
    except Exception:
        pass
    try:
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.MULTILINE)
        if match:
            return f"{match.group(1)}-dev"
    except Exception:
        pass
    return "dev"


def _find_blender():
    """Find the blender executable on PATH (None when missing)."""
    blender = shutil.which("blender")
    if blender is None:
        return None
    root, ext = os.path.splitext(blender)
    return root + ext.lower()


def _blender_missing(session_end):
    tui.step_fail("Blender not found on PATH")
    tui.detail("Install Blender and make sure `blender` runs from your terminal")
    tui.detail("https://www.blender.org/download/")
    session_end()
    sys.exit(1)


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

    Returns None when installed from PyPI (no local source tree available), or
    ("incomplete", path) when the dir exists but has no puree_ui wheel.
    """
    try:
        import puree as _puree_pkg

        candidate = Path(_puree_pkg.__file__).parent.parent / "wheels"
        if not candidate.is_dir():
            return None
        if not list(candidate.glob("puree_ui-*.whl")):
            return ("incomplete", candidate)
        return candidate
    except Exception:
        return None


def _get_addon_id(project_dir):
    """Read the extension ID from blender_manifest.toml (None when missing)."""
    manifest = project_dir / "blender_manifest.toml"
    content = manifest.read_text()
    match = re.search(r'^id\s*=\s*"([^"]+)"', content, re.MULTILINE)
    return match.group(1) if match else None


def _get_blender_paths(blender_exe, version=None, with_site_packages=True):
    """Determine Blender extension and site-packages paths.

    Returns (ext_path, site_packages) or (None, None) when undetectable.
    Skipping site-packages avoids a slow Blender cold start on non-Windows.
    """
    version = version or _get_blender_version(blender_exe)
    if not version:
        return None, None

    system = platform.system()
    if system == "Linux":
        base = Path.home() / ".config" / "blender" / version
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support" / "Blender" / version
    elif system == "Windows":
        base = Path(os.environ.get("APPDATA", "")) / "Blender Foundation" / "Blender" / version
    else:
        return None, None

    ext_path = base / "extensions" / "user_default"
    if not with_site_packages:
        return str(ext_path), None
    if system == "Windows":
        site_packages = base / "extensions" / ".local" / "Lib" / "site-packages"
    else:
        py_version = _get_blender_python_version(blender_exe)
        site_packages = base / "extensions" / ".local" / "lib" / f"python{py_version}" / "site-packages"

    return str(ext_path), str(site_packages)


def _require_manifest(cwd, session_end, hint_init=True):
    """Fail the session cleanly when no blender_manifest.toml is present."""
    if (cwd / "blender_manifest.toml").exists():
        return
    tui.step_fail("No Puree project in this directory")
    tui.detail("blender_manifest.toml was not found")
    if hint_init:
        tui.detail("Run `puree init` to start a project, or cd into an existing one")
    session_end()
    sys.exit(1)


def _tail_lines(*streams, limit=12):
    """Last non-empty lines from subprocess output, for error details."""
    lines = []
    for s in streams:
        if s:
            lines.extend(line.strip() for line in s.splitlines() if line.strip())
    return lines[-limit:]


def _run_streaming(cmd, on_line, timeout=None):
    """Run a command, feeding merged stdout/stderr lines to *on_line* live.

    Returns (returncode, all_lines). Lines also accumulate so failures can
    be reported after the live viewport collapses. A watchdog kills the
    process after *timeout* seconds (None = unlimited).
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    watchdog = None
    if timeout:
        watchdog = threading.Timer(timeout, proc.kill)
        watchdog.daemon = True
        watchdog.start()
    lines = []
    try:
        for raw in proc.stdout:
            line = raw.rstrip()
            if line.strip():
                lines.append(line)
                on_line(line)
        proc.wait()
    finally:
        if watchdog:
            watchdog.cancel()
    return proc.returncode, lines


# ── Templates ────────────────────────────────────────────────────────

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
    # Determine platform tag for wheels
    system = platform.system()
    machine = platform.machine()
    if system == "Linux" and machine == "x86_64":
        plat_tag = "manylinux_2_17_x86_64.manylinux2014_x86_64"
        cp_plat = f"cp{py_version.replace('.', '')}-cp{py_version.replace('.', '')}-{plat_tag}"
        _gl_plat = f"cp{py_version.replace('.', '')}-cp{py_version.replace('.', '')}-manylinux_2_5_x86_64.manylinux1_x86_64.manylinux_2_17_x86_64.manylinux2014_x86_64"
        _yaml_plat = f"cp{py_version.replace('.', '')}-cp{py_version.replace('.', '')}-{plat_tag}"
        _stretch_plat = "cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64"
        _moderngl_plat = f"cp{py_version.replace('.', '')}-cp{py_version.replace('.', '')}-{plat_tag}"
        blender_platforms = '  "linux-x64",'
    elif system == "Windows":
        cp = f"cp{py_version.replace('.', '')}"
        cp_plat = f"{cp}-{cp}-win_amd64"
        _gl_plat = cp_plat
        _yaml_plat = cp_plat
        _stretch_plat = "cp38-abi3-win_amd64"
        _moderngl_plat = cp_plat
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
        _gl_plat = cp_plat
        _yaml_plat = cp_plat
        _stretch_plat = f"cp38-abi3-{mac_tag}"
        _moderngl_plat = cp_plat
    else:
        # Fallback — user will need to fix
        cp_plat = "FIXME"
        _gl_plat = "FIXME"
        _yaml_plat = "FIXME"
        _stretch_plat = "FIXME"
        _moderngl_plat = "FIXME"
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


def _update_manifest_wheels(project_dir):
    """Update the wheels list in blender_manifest.toml to match actual wheel files.

    Returns the number of wheels registered.
    """
    manifest_path = project_dir / "blender_manifest.toml"
    wheels_dir = project_dir / "wheels"

    if not manifest_path.exists():
        return 0

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
    return len(wheel_files)


# ── Commands ─────────────────────────────────────────────────────────


def cmd_init(args):
    """Initialize a new Puree project in the current directory."""
    cwd = Path.cwd()

    if (cwd / "static" / "index.yaml").exists():
        tui.begin("init", _get_version())
        tui.step_fail("A Puree project already exists here")
        tui.detail(f"static{os.sep}index.yaml was found in this directory")
        tui.detail("Pick an empty directory to start a new project")
        tui.finish_fail("Nothing to do")
        sys.exit(1)

    tui.print_logo(animate=True, tagline=TAGLINE)
    tui.begin("init", _get_version())

    # -- Wheel source check (instant — fail before writing anything) ----
    local_wheels_dir = _find_local_wheels_dir()
    if isinstance(local_wheels_dir, tuple):  # local checkout without built wheels
        tui.step_fail("Local wheels directory has no puree_ui wheel")
        tui.detail(f"Looked in {local_wheels_dir[1]}")
        tui.detail("Run `just build_core` and `just build_package` first")
        tui.finish_fail("Init aborted")
        sys.exit(1)

    # -- Blender detection (cold background launch, the slow part) -----
    t = tui.task("Detecting Blender", log_title="blender")
    blender_exe = _find_blender()
    if blender_exe is None:
        t.fail("Blender not found on PATH")
        tui.detail("Install Blender and make sure `blender` runs from your terminal")
        tui.detail("https://www.blender.org/download/")
        tui.finish_fail("Init aborted")
        sys.exit(1)

    t.update("Detecting Blender · querying version")
    bl_version = _get_blender_version(blender_exe)
    t.update("Detecting Blender · querying bundled Python (cold start)")
    _, detect_lines = _run_streaming(
        [
            blender_exe,
            "--background",
            "--python-expr",
            "import sys; print(f'python: {sys.version_info.major}.{sys.version_info.minor}')",
        ],
        t.log,
        timeout=60,
    )
    py_version = "3.13"
    for line in detect_lines:
        match = re.match(r"^python:\s*(\d+\.\d+)$", line.strip())
        if match:
            py_version = match.group(1)
    t.done(f"Blender {bl_version} detected" if bl_version else "Blender detected")
    tui.details([("binary", blender_exe), ("python", py_version)])

    # -- Project structure ---------------------------------------------
    (cwd / "static" / "components").mkdir(parents=True, exist_ok=True)
    (cwd / "wheels").mkdir(exist_ok=True)
    (cwd / "assets").mkdir(exist_ok=True)
    (cwd / "fonts").mkdir(exist_ok=True)

    (cwd / "static" / "index.yaml").write_text(INIT_YAML)
    (cwd / "static" / "style.scss").write_text(INIT_SCSS)
    (cwd / "static" / "script.py").write_text(INIT_SCRIPT)
    (cwd / "__init__.py").write_text(INIT_ENTRY)
    (cwd / "blender_manifest.toml").write_text(_manifest_template(py_version))

    s = os.sep
    tui.step("Project structure created")
    tui.detail(f"static{s}index.yaml · static{s}style.scss · static{s}script.py")
    tui.detail(f"__init__.py · blender_manifest.toml · assets{s} · fonts{s}")

    # -- AI configuration scaffold ---------------------------------------
    scaffold_dir = Path(__file__).parent / "scaffold"
    if scaffold_dir.is_dir():
        copied = []
        for sub in (".agents", ".github"):
            src = scaffold_dir / sub
            dst = cwd / sub
            if src.is_dir() and not dst.exists():
                shutil.copytree(src, dst)
                copied.append(f"{sub}{s}")
        if copied:
            tui.step("AI agent configuration added", meta=" · ".join(copied))

    # -- Wheels -----------------------------------------------------------
    wheels_dir = cwd / "wheels"
    wheels_ok = True
    if local_wheels_dir:
        whl_list = sorted(local_wheels_dir.glob("*.whl"))
        t = tui.task("Collecting wheels", log_title="wheels")
        total_bytes = 0
        for i, whl in enumerate(whl_list):
            t.log(whl.name)
            shutil.copy2(whl, wheels_dir / whl.name)
            total_bytes += whl.stat().st_size
            t.progress(i + 1, len(whl_list), "wheels")
        t.done(f"{len(whl_list)} wheels collected", meta=tui.fmt_size(total_bytes))
        tui.detail(f"from local checkout · into wheels{s}")
    else:
        t = tui.task(f"Downloading wheels from PyPI (python {py_version})", log_title="pip")
        code, pip_lines = _run_streaming(
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
            t.log,
            timeout=900,
        )
        if code == 0:
            whl_list = sorted(wheels_dir.glob("*.whl"))
            total_bytes = sum(w.stat().st_size for w in whl_list)
            t.done(f"{len(whl_list)} wheels downloaded", meta=tui.fmt_size(total_bytes))
            tui.detail(f"from PyPI · into wheels{s}")
        else:
            wheels_ok = False
            t.warn("Wheel download failed — project created without dependencies")
            for line in _tail_lines("\n".join(pip_lines), limit=4):
                tui.detail(line)
            tui.detail("Retry later with:")
            tui.detail(f"pip download --only-binary=:all: --python-version {py_version} --dest wheels puree-ui")

    # -- Manifest --------------------------------------------------------
    n = _update_manifest_wheels(cwd)
    tui.step("Extension manifest written", meta=f"{n} wheels registered")

    tui.finish("Project ready")

    steps = [
        ("puree build", "bundle the extension zip"),
        ("puree install", "install it into Blender"),
        ("blender", "open the Puree tab in the 3D-View sidebar"),
    ]
    if not wheels_ok:
        steps.insert(0, ("pip download …", "fetch the wheels listed above"))
    tui.note("Next steps", steps)
    tui.hint(f"Docs · {DOCS_URL}")


def cmd_build(args):
    """Build the extension zip using Blender on PATH."""
    cwd = Path.cwd()
    tui.begin("build", _get_version())
    _require_manifest(cwd, lambda: tui.finish_fail("Build failed"))

    blender_exe = _find_blender()
    if blender_exe is None:
        _blender_missing(lambda: tui.finish_fail("Build failed"))

    content = (cwd / "blender_manifest.toml").read_text()
    name_match = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)

    display_name = name_match.group(1) if name_match else "addon"
    file_name = display_name.replace(" ", "_")
    version = version_match.group(1) if version_match else "0.0.0"

    tui.step_info(f"{display_name} v{version}")
    tui.details([("blender", blender_exe), ("source", str(cwd))])

    dist_dir = cwd / "dist"
    dist_dir.mkdir(exist_ok=True)
    for old_zip in dist_dir.glob("*.zip"):
        old_zip.unlink()

    output_file = dist_dir / f"{file_name}_{version}.zip"

    t = tui.task("Bundling extension", log_title="blender")
    _, build_lines = _run_streaming(
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
        t.log,
    )

    if output_file.exists():
        size = output_file.stat().st_size
        t.done("Extension bundled")
        tui.detail(f"dist{os.sep}{output_file.name} · {tui.fmt_size(size)}")
        tui.finish("Build complete")
    else:
        t.fail("Blender could not build the extension")
        for line in _tail_lines("\n".join(build_lines)):
            tui.detail(line)
        tui.finish_fail("Build failed")
        sys.exit(1)


def cmd_install(args):
    """Install the built extension into Blender."""
    cwd = Path.cwd()
    tui.begin("install", _get_version())
    _require_manifest(cwd, lambda: tui.finish_fail("Install failed"))

    blender_exe = _find_blender()
    if blender_exe is None:
        _blender_missing(lambda: tui.finish_fail("Install failed"))

    zips = sorted((cwd / "dist").glob("*.zip")) if (cwd / "dist").is_dir() else []
    if not zips:
        tui.step_fail("No built extension found")
        tui.detail(f"dist{os.sep} has no .zip — run `puree build` first")
        tui.finish_fail("Install failed")
        sys.exit(1)

    package_file = zips[-1]  # latest build

    tui.step_info(package_file.name, meta=tui.fmt_size(package_file.stat().st_size))
    tui.details([("blender", blender_exe), ("repository", "user_default")])

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

    t = tui.task("Installing into Blender", log_title="blender")
    _, install_lines = _run_streaming(
        [blender_exe, "--background", "--python-expr", install_script],
        t.log,
    )

    # Blender operators can refuse a package (e.g. blender_version_min not
    # met) without raising, so verify the extension actually landed on disk.
    installed_path = None
    ext_dir = None
    addon_id = _get_addon_id(cwd)
    if addon_id:
        ext_dir, _ = _get_blender_paths(blender_exe, with_site_packages=False)
        if ext_dir and (Path(ext_dir) / addon_id).is_dir():
            installed_path = Path(ext_dir) / addon_id

    reported_ok = any("installed and enabled successfully" in line for line in install_lines)

    if reported_ok and (installed_path or not addon_id):
        t.done("Extension installed and enabled")
        if installed_path:
            tui.detail(str(installed_path))
        tui.finish("Install complete")
        tui.note(
            "Try it",
            [
                ("blender", "launch Blender"),
                ("N-panel", "open the sidebar in the 3D Viewport → Puree tab"),
            ],
        )
    else:
        if reported_ok:
            t.fail("Blender accepted the package but the extension is missing")
            tui.detail(f"expected at {Path(ext_dir) / addon_id}" if ext_dir else "install location unknown")
            tui.detail("check the version requirements in blender_manifest.toml")
        else:
            t.fail("Installation failed")
        for line in _tail_lines("\n".join(install_lines)):
            tui.detail(line)
        tui.finish_fail("Install failed")
        sys.exit(1)


def cmd_link(args):
    """Symlink project into Blender's extensions for development."""
    cwd = Path.cwd()
    tui.begin("link", _get_version())
    _require_manifest(cwd, lambda: tui.finish_fail("Link failed"))

    addon_id = _get_addon_id(cwd)
    if not addon_id:
        tui.step_fail("No `id` field in blender_manifest.toml")
        tui.finish_fail("Link failed")
        sys.exit(1)

    blender_exe = _find_blender()
    if blender_exe is None:
        _blender_missing(lambda: tui.finish_fail("Link failed"))

    bl_version = _get_blender_version(blender_exe)
    tui.step_info(addon_id, meta=f"Blender {bl_version}" if bl_version else None)

    ext_dir, _ = _get_blender_paths(blender_exe, bl_version, with_site_packages=False)
    if ext_dir is None:
        tui.step_fail("Could not locate Blender's extensions directory")
        tui.detail(f"platform: {platform.system()} · version: {bl_version or 'unknown'}")
        tui.finish_fail("Link failed")
        sys.exit(1)

    ext_dir = Path(ext_dir)
    addon_link = ext_dir / addon_id
    ext_dir.mkdir(parents=True, exist_ok=True)

    replaced = None
    if addon_link.is_symlink():
        addon_link.unlink()
        replaced = "updated existing symlink"
    elif addon_link.is_dir():
        shutil.rmtree(addon_link)
        replaced = "replaced installed extension copy"

    try:
        addon_link.symlink_to(cwd)
    except OSError as e:
        tui.step_fail("Could not create the symlink")
        tui.detail(str(e))
        if platform.system() == "Windows":
            tui.detail("On Windows, enable Developer Mode (Settings → System → For developers)")
            tui.detail("or run this command from an elevated (admin) terminal")
        tui.finish_fail("Link failed")
        sys.exit(1)

    tui.step("Symlink created", meta=replaced)
    tui.details([("link", str(addon_link)), ("target", str(cwd))])

    # Extract wheels directly (they are zip files) to avoid pip rejecting
    # wheels built for Blender's Python version.
    wheels = sorted((cwd / "wheels").glob("*.whl")) if (cwd / "wheels").is_dir() else []
    if wheels:
        t = tui.task("Installing wheel dependencies", log_title="wheels")
        # Locating site-packages may cold-start Blender on Linux/macOS —
        # keep it inside the spinner.
        _, site_packages = _get_blender_paths(blender_exe, bl_version)
        site_packages = Path(site_packages)
        site_packages.mkdir(parents=True, exist_ok=True)
        installed, failed = 0, []
        for i, whl in enumerate(wheels):
            t.log(whl.name)
            try:
                with zipfile.ZipFile(whl, "r") as zf:
                    zf.extractall(site_packages)
                installed += 1
            except Exception:
                failed.append(whl.name)
            t.progress(i + 1, len(wheels), "wheels")
        if failed:
            t.warn(f"{installed}/{len(wheels)} wheel dependencies installed")
            for name in failed:
                tui.detail(f"failed: {name}")
        else:
            t.done(f"{installed} wheel dependencies installed")
        tui.detail(f"into {site_packages}")
    else:
        tui.step_warn("No wheels found — dependencies not installed", meta="run `puree init` to fetch them")

    tui.finish("Dev mode active")
    tui.note(
        "Development loop",
        [
            ("blender", "restart Blender to load the addon"),
            ("puree reload", "push code changes to the running instance"),
            ("puree unlink", "leave dev mode when done"),
        ],
    )


def cmd_unlink(args):
    """Remove the development symlink from Blender's extensions."""
    cwd = Path.cwd()
    tui.begin("unlink", _get_version())
    _require_manifest(cwd, lambda: tui.finish_fail("Unlink failed"), hint_init=False)

    addon_id = _get_addon_id(cwd)
    if not addon_id:
        tui.step_fail("No `id` field in blender_manifest.toml")
        tui.finish_fail("Unlink failed")
        sys.exit(1)

    blender_exe = _find_blender()
    if blender_exe is None:
        _blender_missing(lambda: tui.finish_fail("Unlink failed"))

    ext_dir, _ = _get_blender_paths(blender_exe, with_site_packages=False)
    addon_link = Path(ext_dir) / addon_id if ext_dir else None

    if addon_link and addon_link.is_symlink():
        addon_link.unlink()
        tui.step("Symlink removed")
        tui.detail(str(addon_link))
        tui.finish("Dev mode deactivated")
    elif addon_link and addon_link.is_dir():
        tui.step_warn("Found an installed copy, not a symlink — left untouched")
        tui.detail(str(addon_link))
        tui.detail("Remove it from Blender: Preferences → Get Extensions")
        tui.finish("Nothing unlinked")
    else:
        tui.step_warn("No symlink found", meta=addon_id)
        if addon_link:
            tui.detail(f"looked in {addon_link.parent}")
        tui.finish("Nothing to do")


def cmd_reload(args):
    """Reload addon in a running Blender instance."""
    import socket
    import time as _time

    tui.begin("reload", _get_version())

    # Primary: TCP reload via Puree's built-in reload server
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect(("127.0.0.1", 19746))
        s.sendall(b"reload")
        resp = s.recv(64).decode("utf-8", errors="ignore").strip()
        s.close()
        if resp == "ok":
            tui.step("Reload signal sent", meta="tcp 127.0.0.1:19746")
            tui.finish("Blender is reloading")
            return
        tui.step_warn("Reload server answered unexpectedly", meta=repr(resp))
    except (ConnectionRefusedError, OSError, socket.timeout):
        tui.step_warn("Reload server not reachable", meta="tcp 127.0.0.1:19746")

    # Fallback: sentinel file watched by the addon
    sentinel = Path.cwd() / ".puree_reload"
    sentinel.write_text(str(_time.time()))
    tui.step("Reload sentinel written", meta=".puree_reload")
    tui.detail("a running Blender picks this up within ~2 seconds")
    tui.detail("no Blender running? just start it — the addon loads fresh code anyway")
    tui.finish("Reload requested")


# ── Help / version ───────────────────────────────────────────────────

COMMANDS = {
    "init": ("Scaffold a new Puree project in the current directory", cmd_init),
    "build": ("Bundle the project into an installable extension zip", cmd_build),
    "install": ("Install the built extension into Blender", cmd_install),
    "link": ("Symlink the project into Blender for live development", cmd_link),
    "unlink": ("Remove the development symlink", cmd_unlink),
    "reload": ("Hot-reload the addon in a running Blender", cmd_reload),
}


def _print_help():
    tui.print_logo(animate=False, tagline=TAGLINE)
    P, W, G, D, B, R = tui.PINK, tui.WHITE, tui.GREY, tui.DARK, tui.BOLD, tui.RESET
    pad = max(len(c) for c in COMMANDS)
    lines = ["", f"   {B}{W}Usage{R}", f"     {tui.wordmark()} {G}<command>{R}", ""]
    lines.append(f"   {B}{W}Commands{R}")
    for cmd, (desc, _) in COMMANDS.items():
        lines.append(f"     {P}{cmd.ljust(pad)}{R}  {G}{desc}{R}")
    opt_pad = len("-V, --version") + 2
    lines += [
        "",
        f"   {B}{W}Options{R}",
        f"     {P}{'-h, --help'.ljust(opt_pad)}{R}{G}Show this help{R}",
        f"     {P}{'-V, --version'.ljust(opt_pad)}{R}{G}Show the puree version{R}",
        "",
        f"   {B}{W}Workflow{R}",
        f"     {D}${R} {P}puree init{R}        {D}start a project{R}",
        f"     {D}${R} {P}puree build{R}       {D}produce dist/<addon>.zip{R}",
        f"     {D}${R} {P}puree install{R}     {D}install the zip into Blender{R}",
        f"     {D}${R} {P}puree link{R}        {D}…or develop live with hot reload{R}",
        f"     {D}${R} {P}puree reload{R}      {D}push changes to a running Blender{R}",
        "",
        f"   {D}Docs · {DOCS_URL}{R}",
        "",
    ]
    tui.print_stdout("\n".join(lines))


def _print_version():
    tui.print_stdout(f"{tui.wordmark()} {tui.GREY}v{_get_version()}{tui.RESET}\n")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        match = re.search(r"invalid choice: '([^']+)'", message)
        if match:
            tui.step_fail(f"Unknown command `{match.group(1)}`")
            tui.detail("run `puree --help` to see available commands")
        else:
            tui.step_fail(message)
        sys.exit(2)


# ── Entry Point ──────────────────────────────────────────────────────


def main():
    argv = sys.argv[1:]

    if not argv or "-h" in argv or "--help" in argv or argv[0] == "help":
        _print_help()
        return
    if argv[0] in ("-V", "--version"):
        _print_version()
        return

    parser = _Parser(prog="puree", add_help=False)
    subparsers = parser.add_subparsers(dest="command")
    for name in COMMANDS:
        subparsers.add_parser(name, add_help=False)

    args = parser.parse_args(argv)
    if args.command is None:
        _print_help()
        return
    COMMANDS[args.command][1](args)


if __name__ == "__main__":
    main()
