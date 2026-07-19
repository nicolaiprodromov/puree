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
"""Puree terminal UI — the design system behind the `puree` CLI.

Every command renders a connected *session rail*:

    ┌  puree build · v0.1.3
    │
    ◇  My Puree Addon v0.1.0
    │     blender   C:\\Program Files\\Blender\\blender.exe
    │
    ◆  Extension bundled · 1.9s
    │     dist\\my_addon-0.1.0.zip · 24.1 KB
    │
    └  Build complete · 4.2s

While a task runs, live output streams into a fixed-height scrolling
viewport under the spinner (Docker-build style) that collapses into the
final summary when the step completes:

    ⠸  Bundling extension · 4s
    │  ╭─ blender ──────────────────────────╮
    │  │ Found bundled python 3.11          │
    │  │ Info: created my_addon-0.1.0.zip   │
    │  ╰────────────────────────────────────╯

Design rules:
  - One visual language: rail glyphs carry state (◆ done, ✖ fail, ▲ warn,
    ◇ info), text stays plain, metadata is dim and separated by `·`.
  - Live feedback is honest: spinners show elapsed time, progress bars show
    real counts, log viewports show real output — never simulated.
  - Degrades gracefully: NO_COLOR / dumb terminals get plain glyphs, piped
    or CI output gets a clean linear log with zero cursor control codes.
"""

import atexit
import collections
import itertools
import os
import re
import shutil
import sys
import threading
import time
import unicodedata

# ── Capability detection ─────────────────────────────────────────────


def _enable_windows_vt():
    """Enable ANSI escape processing on classic Windows consoles."""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        ok = False
        for handle_id in (-11, -12):  # stdout, stderr
            handle = kernel32.GetStdHandle(handle_id)
            mode = ctypes.c_uint32()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                if kernel32.SetConsoleMode(handle, mode.value | 0x0004):
                    ok = True
        return ok
    except Exception:
        return False


def _isatty(stream):
    try:
        return stream.isatty()
    except Exception:
        return False


_VT_OK = _enable_windows_vt()


def _detect_color(stream):
    force = os.environ.get("FORCE_COLOR", "")
    if force and force != "0":
        return True
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return _isatty(stream)


# Color and interactivity are independent: a TTY with NO_COLOR still gets
# live spinner redraws (plain), while FORCE_COLOR into a pipe gets color
# but a linear, CI-safe log.
_COLOR = _detect_color(sys.stderr)
_INTERACTIVE = (
    (_isatty(sys.stderr) or bool(os.environ.get("PUREE_FORCE_TTY")))
    and os.environ.get("TERM") != "dumb"
    and (os.name != "nt" or _VT_OK or bool(os.environ.get("PUREE_FORCE_TTY")))
)


def _setup_windows_utf8():
    """Switch the Windows console to the UTF-8 code page (65001).

    Raw byte writes are decoded using the console's output code page —
    on legacy code pages (437/850/1252) our UTF-8 glyphs turn into
    mojibake like `Γûê`. Restores the previous code page on exit.
    """
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        prev = kernel32.GetConsoleOutputCP()
        if prev == 65001:
            return True
        if kernel32.SetConsoleOutputCP(65001):
            atexit.register(lambda: kernel32.SetConsoleOutputCP(prev))
            return True
        return False
    except Exception:
        return False


def _unicode_ok():
    """Can the attached terminal render our Unicode glyphs?"""
    if os.environ.get("PUREE_ASCII"):
        return False
    if not _isatty(sys.stderr):
        return True  # pipes/CI: UTF-8 bytes are the norm
    if os.name == "nt":
        return _setup_windows_utf8()
    enc = (getattr(sys.stderr, "encoding", None) or "utf-8").lower()
    return "utf" in enc


_UNICODE_OK = _unicode_ok()

# Transliteration for terminals that cannot render Unicode: applied as a
# single choke point in `_write`/`print_stdout`, so every caller degrades
# automatically (rail, glyphs, logo, separators, prose).
_ASCII_MAP = str.maketrans(
    {
        "█": "#",
        "░": ".",
        "▒": ".",
        "╔": "+",
        "╗": "+",
        "╚": "+",
        "╝": "+",
        "║": "#",
        "═": "=",
        "┌": "+",
        "└": "+",
        "│": "|",
        "─": "-",
        "╭": "+",
        "╮": "+",
        "╰": "+",
        "╯": "+",
        "◆": "*",
        "◇": "o",
        "✖": "x",
        "▲": "!",
        "·": "-",
        "→": ">",
        "—": "-",
        "–": "-",
        "…": "...",
        "‿": "_",
        "◕": "o",
    }
)

# Raw fd writes keep spinner animation smooth while subprocesses run
# (unbuffered, same approach as Rich/Halo). Fall back to the stream object.
try:
    _FD = sys.stderr.fileno()
except Exception:
    _FD = None


def _write(s):
    if not _UNICODE_OK:
        s = s.translate(_ASCII_MAP)
    if _FD is not None:
        try:
            os.write(_FD, s.encode("utf-8", "replace"))
            return
        except OSError:
            pass
    try:
        sys.stderr.write(s)
        sys.stderr.flush()
    except Exception:
        pass


def _ansi(code):
    return f"\033[{code}m" if _COLOR else ""


# ── Palette ──────────────────────────────────────────────────────────

RESET = _ansi("0")
BOLD = _ansi("1")
DIM = _ansi("2")
ITALIC = _ansi("3")
PINK = _ansi("38;5;205")
MAGENTA = _ansi("38;5;199")
CORAL = _ansi("38;5;209")
PEACH = _ansi("38;5;217")
BLUE = _ansi("38;5;75")
CYAN = _ansi("38;5;80")
GREEN = _ansi("38;5;114")
YELLOW = _ansi("38;5;221")
RED = _ansi("38;5;203")
WHITE = _ansi("38;5;255")
GREY = _ansi("38;5;245")
DARK = _ansi("38;5;240")

# Sunset gradient — the Puree brand (hot pink → golden peach)
LOGO_GRADIENT = [
    _ansi("38;5;199"),
    _ansi("38;5;205"),
    _ansi("38;5;211"),
    _ansi("38;5;210"),
    _ansi("38;5;216"),
    _ansi("38;5;222"),
]

PUREE_LOGO = [
    r"██████╗ ██╗   ██╗██████╗ ███████╗ ███████╗",
    r"██╔══██╗██║   ██║██╔══██╗██╔════╝ ██╔════╝",
    r"██████╔╝██║   ██║██████╔╝█████╗   █████╗  ",
    r"██╔═══╝ ██║   ██║██╔══██╗██╔══╝   ██╔══╝  ",
    r"██║     ╚██████╔╝██║  ██║███████╗ ███████╗",
    r"╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚══════╝",
]

# ── Glyphs ───────────────────────────────────────────────────────────
# State is carried by both glyph shape and color so the rail stays
# readable without color (pipes, NO_COLOR, screen readers).

GL_TOP = "┌"
GL_RAIL = "│"
GL_END = "└"
GL_DONE = "◆"
GL_INFO = "◇"
GL_FAIL = "✖"
GL_WARN = "▲"
SEP = "·"

# Live log viewport (rounded box)
BOX_TL = "╭"
BOX_TR = "╮"
BOX_BL = "╰"
BOX_BR = "╯"
BOX_V = "│"
BOX_H = "─"

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"] if _UNICODE_OK else ["|", "/", "-", "\\"]

_INDENT = "   "  # text column under a node glyph
_DETAIL_PAD = "    "  # detail indent after the rail glyph

# ── Formatting helpers ───────────────────────────────────────────────


def fmt_duration(seconds):
    if seconds < 10:
        return f"{seconds:.1f}s"
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m {s:02d}s"


def fmt_size(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _meta(text):
    """Dim metadata suffix: ` · text`."""
    return f" {DARK}{SEP}{RESET} {GREY}{text}{RESET}" if text else ""


def _char_width(ch):
    """Visual terminal width of a character (0 for combining, 2 for wide)."""
    if unicodedata.combining(ch):
        return 0
    if ch in ("\u200d", "\ufe0f", "\ufe0e"):  # ZWJ / variation selectors
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def _visual_width(text):
    return sum(_char_width(ch) for ch in text)


def _clip_visual(text, width):
    """Truncate *text* to at most *width* terminal columns (… suffix)."""
    if _visual_width(text) <= width:
        return text
    out, used = [], 0
    for ch in text:
        w = _char_width(ch)
        if used + w > width - 1:
            break
        out.append(ch)
        used += w
    return "".join(out) + "…"


def _term_cols():
    return shutil.get_terminal_size((80, 24)).columns


# ── Cursor management ────────────────────────────────────────────────

_cursor_hidden = False


def _hide_cursor():
    global _cursor_hidden
    if _INTERACTIVE and not _cursor_hidden:
        _write("\033[?25l")
        _cursor_hidden = True


def _show_cursor():
    global _cursor_hidden
    if _cursor_hidden:
        _write("\033[?25h")
        _cursor_hidden = False


atexit.register(_show_cursor)

# ── Session rail ─────────────────────────────────────────────────────

_session_t0 = None
_session_open = False


def _rail_gap():
    if _session_open:
        _write(f"{DARK}{GL_RAIL}{RESET}\n")


def begin(command, version=None):
    """Open a session: `┌  puree <command> · v1.2.3`."""
    global _session_t0, _session_open
    _session_t0 = time.monotonic()
    _session_open = True
    ver = _meta(f"v{version}") if version else ""
    _write(f"\n{DARK}{GL_TOP}{RESET}  {BOLD}{PINK}puree{RESET} {BOLD}{WHITE}{command}{RESET}{ver}\n")


def _node(glyph, color, msg, meta=None):
    _rail_gap()
    _write(f"{color}{glyph}{RESET}  {msg}{_meta(meta)}\n")


def step(msg, meta=None):
    """Completed step: green ◆."""
    _node(GL_DONE, GREEN, msg, meta)


def step_info(msg, meta=None):
    """Neutral fact: dim ◇."""
    _node(GL_INFO, DARK, msg, meta)


def step_warn(msg, meta=None):
    """Warning: yellow ▲."""
    _node(GL_WARN, YELLOW, msg, meta)


def step_fail(msg, meta=None):
    """Failure: red ✖."""
    _node(GL_FAIL, RED, msg, meta)


def detail(text):
    """A dim annotation line attached to the previous node."""
    _write(f"{DARK}{GL_RAIL}{RESET}{_DETAIL_PAD}{GREY}{text}{RESET}\n")


def details(pairs):
    """Aligned key/value lines attached to the previous node."""
    pairs = [(str(k), str(v)) for k, v in pairs]
    if not pairs:
        return
    width = max(len(k) for k, _ in pairs)
    for k, v in pairs:
        _write(f"{DARK}{GL_RAIL}{RESET}{_DETAIL_PAD}{DARK}{k.ljust(width)}{RESET}  {v}\n")


def finish(msg):
    """Close the session successfully: `└  msg · 4.2s`."""
    global _session_open
    elapsed = ""
    if _session_t0:
        seconds = time.monotonic() - _session_t0
        if seconds >= 0.1:
            elapsed = _meta(fmt_duration(seconds))
    _rail_gap()
    _session_open = False
    _write(f"{GREEN}{GL_END}{RESET}  {GREEN}{msg}{RESET}{elapsed}\n\n")


def finish_fail(msg):
    """Close the session with a failure: red `└  msg`."""
    global _session_open
    _rail_gap()
    _session_open = False
    _write(f"{RED}{GL_END}{RESET}  {RED}{msg}{RESET}\n\n")


# ── Post-session notes ───────────────────────────────────────────────


def note(title, rows):
    """A titled block after the session (e.g. next steps).

    Rows are (command, description) tuples — commands align in a pink
    column — or plain strings.
    """
    _write(f"{_INDENT}{BOLD}{WHITE}{title}{RESET}\n")
    tuples = [r for r in rows if isinstance(r, tuple)]
    width = max((len(c) for c, _ in tuples), default=0)
    for i, row in enumerate(rows, 1):
        if isinstance(row, tuple):
            cmd, desc = row
            _write(f"{_INDENT}{DARK}{i}{RESET}  {PINK}{cmd.ljust(width)}{RESET}  {GREY}{desc}{RESET}\n")
        else:
            _write(f"{_INDENT}{DARK}{i}{RESET}  {row}\n")
    _write("\n")


def hint(text):
    """A single dim footer line."""
    _write(f"{_INDENT}{DARK}{text}{RESET}\n\n")


# ── Live task (spinner node) ─────────────────────────────────────────


class Task:
    """A rail node that animates while work happens, then settles into a
    final state — leaving no transient lines behind.

    Interactive terminals get a live spinner with an elapsed-time counter,
    a real progress bar via `progress()`, and — via `log()` — a fixed-height
    scrolling viewport (Docker-build style) that shows the last few lines
    of live output in a box under the spinner:

        ⠸  Bundling extension · 4s
        │  ╭─ blender ──────────────────────────╮
        │  │ Found bundled python 3.11          │
        │  │ Info: created my_addon-0.1.0.zip   │
        │  ╰────────────────────────────────────╯

    The whole live region collapses when the task finishes, replaced by
    the final `◆ msg` line and summary details. Non-interactive output
    logs a single `◇ msg` line at start and the final state line at end.
    """

    def __init__(self, message, log_title=None, log_height=6):
        self.message = message
        self._t0 = time.monotonic()
        self._stop = threading.Event()
        self._thread = None
        self._progress = None  # (current, total, unit)
        self._log_title = log_title
        self._log = collections.deque(maxlen=max(log_height, 1))
        self._log_lock = threading.Lock()
        self._drawn = 0  # physical lines currently on screen
        _rail_gap()
        if _INTERACTIVE:
            _hide_cursor()
            self._thread = threading.Thread(target=self._animate, daemon=True)
            self._thread.start()
        else:
            _write(f"{DARK}{GL_INFO}{RESET}  {self.message}{DARK} …{RESET}\n")

    # -- live rendering ------------------------------------------------

    def _frame_text(self, frame):
        elapsed = time.monotonic() - self._t0
        counter = f" {fmt_duration(elapsed)}" if elapsed >= 1.0 else ""
        if self._progress:
            cur, total, unit = self._progress
            total = max(total, 1)
            filled = int(14 * min(cur / total, 1.0))
            bar_plain = "█" * filled + "░" * (14 - filled)
            count = f" {cur}/{total}{(' ' + unit) if unit else ''}"
            tail_plain = f"  {bar_plain}{count}"
            tail = f"  {PINK}{'█' * filled}{RESET}{DARK}{'░' * (14 - filled)}{RESET}{GREY}{count}{RESET}"
        else:
            tail_plain = ""
            tail = ""
        msg = self.message
        visible = 3 + len(msg) + len(tail_plain) + len(counter)
        max_w = _term_cols() - 1
        if visible > max_w:
            msg = msg[: max(0, max_w - (visible - len(msg)) - 1)] + "…"
        return f"{PINK}{frame}{RESET}  {msg}{tail}{DARK}{counter}{RESET}"

    def _box_lines(self):
        """Render the log viewport as rail-prefixed box lines."""
        with self._log_lock:
            entries = list(self._log)
        if not entries:
            return []
        width = max(min(_term_cols() - 5, 74), 16)
        inner = width - 4  # borders + padding
        rail = f"{DARK}{GL_RAIL}{RESET}  "
        title = f"{BOX_H} {self._log_title} " if self._log_title else ""
        if title:
            title = _clip_visual(title, width - 2)
        fill = BOX_H * max(width - 2 - len(title), 0)
        lines = [f"{rail}{DARK}{BOX_TL}{title}{fill}{BOX_TR}{RESET}"]
        for entry in entries:
            entry = _clip_visual(entry, inner)
            pad = " " * max(inner - _visual_width(entry), 0)
            lines.append(f"{rail}{DARK}{BOX_V}{RESET} {GREY}{entry}{pad}{RESET} {DARK}{BOX_V}{RESET}")
        lines.append(f"{rail}{DARK}{BOX_BL}{BOX_H * (width - 2)}{BOX_BR}{RESET}")
        return lines

    def _render_region(self, lines):
        """Redraw the live region in place (cursor parks on the last line)."""
        out = []
        if self._drawn > 1:
            out.append(f"\r\033[{self._drawn - 1}A")
        elif self._drawn == 1:
            out.append("\r")
        for i, line in enumerate(lines):
            out.append(f"\033[K{line}")
            if i < len(lines) - 1:
                out.append("\n")
        _write("".join(out))
        self._drawn = len(lines)

    def _erase_region(self):
        """Clear every live line, leaving the cursor at the region start."""
        if not self._drawn:
            return
        out = ["\r\033[K"]
        for _ in range(self._drawn - 1):
            out.append("\033[1A\r\033[K")
        _write("".join(out))
        self._drawn = 0

    def _animate(self):
        cycle = itertools.cycle(SPINNER_FRAMES)
        while not self._stop.is_set():
            self._render_region([self._frame_text(next(cycle))] + self._box_lines())
            self._stop.wait(0.08)
        self._erase_region()

    def _halt(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        _show_cursor()

    # -- public API ------------------------------------------------------

    def update(self, message):
        """Swap the live message (interactive only — final line wins in logs)."""
        self.message = message
        return self

    def progress(self, current, total, unit=""):
        """Report real progress; renders a live bar on the spinner line."""
        self._progress = (current, total, unit)
        return self

    def log(self, line):
        """Feed a line of live output into the scrolling viewport.

        No-op on non-interactive output (CI logs stay linear); callers
        keep their own transcript for failure reporting.
        """
        if not _INTERACTIVE:
            return self
        line = _ANSI_RE.sub("", str(line)).split("\r")[-1].expandtabs(2).rstrip()
        if line:
            with self._log_lock:
                self._log.append(line)
        return self

    def _finalize(self, glyph, color, msg, meta):
        self._halt()
        elapsed = time.monotonic() - self._t0
        parts = []
        if meta:
            parts.append(meta)
        if elapsed >= 0.3:
            parts.append(fmt_duration(elapsed))
        _write(f"{color}{glyph}{RESET}  {msg or self.message}{_meta(f' {SEP} '.join(parts)) if parts else ''}\n")

    def done(self, msg=None, meta=None):
        self._finalize(GL_DONE, GREEN, msg, meta)

    def warn(self, msg=None, meta=None):
        self._finalize(GL_WARN, YELLOW, msg, meta)

    def fail(self, msg=None, meta=None):
        self._finalize(GL_FAIL, RED, msg, meta)


def task(message, log_title=None, log_height=6):
    return Task(message, log_title=log_title, log_height=log_height)


# ── Brand ────────────────────────────────────────────────────────────


def print_logo(animate=True, tagline=None):
    """The gradient logo — reserved for `init` and the help screen."""
    _write("\n")
    for i, line in enumerate(PUREE_LOGO):
        color = LOGO_GRADIENT[i % len(LOGO_GRADIENT)]
        _write(f"{_INDENT}{color}{line}{RESET}\n")
        if animate and _INTERACTIVE:
            time.sleep(0.04)
    if tagline:
        _write(f"\n{_INDENT}{GREY}{tagline}{RESET}\n")


def wordmark():
    """Inline gradient `puree` wordmark."""
    if not _COLOR:
        return "puree"
    letters = "puree"
    return "".join(f"{LOGO_GRADIENT[i]}{ch}" for i, ch in enumerate(letters)) + RESET


# ── stdout printing (help / version) ─────────────────────────────────

_ANSI_RE = re.compile(r"\033\[[0-9;?]*[A-Za-z]")


def print_stdout(text):
    """Print to stdout, stripping ANSI when stdout isn't color-capable."""
    if not _UNICODE_OK:
        text = text.translate(_ASCII_MAP)
    if not _detect_color(sys.stdout):
        text = _ANSI_RE.sub("", text)
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except Exception:
        pass


# ── Demo ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print_logo(animate=True, tagline="Declarative, GPU-accelerated UI for Blender addons")

    begin("demo", "0.1.3")

    t = task("Detecting Blender", log_title="blender")
    _fake_blender = [
        "Blender 5.0.0 (hash a37564c4df7a)",
        "Read prefs: userpref.blend",
        "Found bundled python: python3.11",
        "import extensions module",
        "checking add-on compatibility",
        "python: 3.11",
        "Blender quit",
    ]
    for line in _fake_blender:
        t.log(line)
        time.sleep(0.4)
    t.done("Blender 5.0 detected")
    details([("binary", r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"), ("python", "3.11")])

    step("Project structure created")
    detail("static\\index.yaml · static\\style.scss · static\\script.py")

    t = task("Collecting wheels", log_title="wheels")
    _wheels = [
        "attrs-25.3.0-py3-none-any.whl",
        "glcontext-3.0.0-cp313-cp313-win_amd64.whl",
        "moderngl-5.12.0-cp313-cp313-win_amd64.whl",
        "PyYAML-6.0.2-cp313-cp313-win_amd64.whl",
        "puree_ui-0.1.3-py3-none-any.whl",
        "stretchable-1.1.7-cp38-abi3-win_amd64.whl",
        "typing_extensions-4.15.0-py3-none-any.whl",
    ]
    for i, name in enumerate(_wheels):
        t.log(name)
        t.progress(i + 1, len(_wheels), "wheels")
        time.sleep(0.35)
    t.done("7 wheels collected", meta="727.8 KB")

    step_info("My Puree Addon v0.1.0")
    step_warn("SCSS cache may be stale")

    finish("Project ready")

    note(
        "Next steps",
        [
            ("puree build", "bundle the extension zip"),
            ("puree install", "install into Blender"),
            ("blender", "find the Puree tab in the N-panel"),
        ],
    )
    hint("Docs · https://github.com/nicolaiprodromov/puree")

    begin("demo-fail", "0.1.3")
    t = task("Bundling extension", log_title="blender")
    for line in ["Blender 5.0.0", "building zip...", "Error: manifest invalid", "Blender quit"]:
        t.log(line)
        time.sleep(0.4)
    t.fail("Build failed")
    detail("Error: manifest invalid")
    detail("Blender exited with code 1")
    finish_fail("Build failed")
