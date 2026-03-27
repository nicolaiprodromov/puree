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

import itertools
import os
import shutil
import sys
import threading
import time


# ── ANSI helpers ─────────────────────────────────────────────────────

def _supports_color():
    """Check if the terminal supports ANSI color codes."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    # Check stderr since that's where we write UI output
    if not hasattr(sys.stderr, "isatty") or not sys.stderr.isatty():
        return False
    return True


_COLOR = _supports_color()

# File descriptor for raw unbuffered writes — use stderr to avoid
# stdout buffering issues that block spinner animations during
# subprocess calls. This is the standard approach used by Rich, Halo, etc.
_FD = sys.stderr.fileno()


def _write(s):
    """Write string directly to stderr fd — unbuffered, never blocks."""
    os.write(_FD, s.encode())


def _ansi(code):
    return f"\033[{code}m" if _COLOR else ""


# Colors
RESET   = _ansi("0")
BOLD    = _ansi("1")
DIM     = _ansi("2")
ITALIC  = _ansi("3")
PINK    = _ansi("38;5;205")
MAGENTA = _ansi("38;5;199")
HOT     = _ansi("38;5;198")
CORAL   = _ansi("38;5;209")
PEACH   = _ansi("38;5;217")
BLUE    = _ansi("38;5;75")
CYAN    = _ansi("38;5;80")
GREEN   = _ansi("38;5;114")
YELLOW  = _ansi("38;5;221")
RED     = _ansi("38;5;203")
WHITE   = _ansi("38;5;255")
GREY    = _ansi("38;5;245")
DARK    = _ansi("38;5;238")

# Gradient palette for the logo (top-to-bottom)
# Smooth path through the 256-color cube: each step changes one RGB channel
# by one level, giving a natural hot-pink → golden-peach sunset gradient.
LOGO_GRADIENT = [
    _ansi("38;5;199"),  # #FF00AF — hot magenta-pink
    _ansi("38;5;205"),  # #FF5FAF — pink
    _ansi("38;5;211"),  # #FF87AF — light pink
    _ansi("38;5;210"),  # #FF8787 — warm salmon
    _ansi("38;5;216"),  # #FFAF87 — soft coral
    _ansi("38;5;222"),  # #FFD787 — golden peach
]


# ── Logo ─────────────────────────────────────────────────────────────

PUREE_LOGO_COMPACT = [
    r"  ██████╗ ██╗   ██╗██████╗ ███████╗ ███████╗ ",
    r"  ██╔══██╗██║   ██║██╔══██╗██╔════╝ ██╔════╝ ",
    r"  ██████╔╝██║   ██║██████╔╝█████╗   █████╗   ",
    r"  ██╔═══╝ ██║   ██║██╔══██╗██╔══╝   ██╔══╝   ",
    r"  ██║     ╚██████╔╝██║  ██║███████╗ ███████╗ ",
    r"  ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚══════╝ ",
]

# ── Spinner frames ───────────────────────────────────────────────────

# Braille dots spinner — smooth and clean
SPINNER_BRAILLE = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# Block bounce
SPINNER_BLOCKS = ["█▒▒▒▒", "██▒▒▒", "███▒▒", "████▒", "█████", "▒████", "▒▒███", "▒▒▒██", "▒▒▒▒█", "▒▒▒▒▒"]

# Wave dots
SPINNER_WAVE = ["∙∙∙∙∙", "●∙∙∙∙", "∙●∙∙∙", "∙∙●∙∙", "∙∙∙●∙", "∙∙∙∙●", "∙∙∙∙∙"]

# Gradient bar that fills and empties
SPINNER_FILL = ["░░░░░░░░░░", "█░░░░░░░░░", "██░░░░░░░░", "███░░░░░░░", "████░░░░░░",
                "█████░░░░░", "██████░░░░", "███████░░░", "████████░░", "█████████░",
                "██████████", "░█████████", "░░████████", "░░░███████", "░░░░██████",
                "░░░░░█████", "░░░░░░████", "░░░░░░░███", "░░░░░░░░██", "░░░░░░░░░█"]

# Puree themed — cooking!
SPINNER_COOK = ["🍳      ", " 🍳     ", "  🍳    ", "   🍳   ", "    🍳  ", "     🍳 ", "      🍳",
                "     🍳 ", "    🍳  ", "   🍳   ", "  🍳    ", " 🍳     "]

DEFAULT_SPINNER = SPINNER_COOK


# ── Progress bar ─────────────────────────────────────────────────────

def progress_bar(current, total, width=30, label=""):
    """Render a single-line progress bar. Call repeatedly to update."""
    if total <= 0:
        frac = 1.0
    else:
        frac = min(current / total, 1.0)
    filled = int(width * frac)
    empty = width - filled
    pct = int(frac * 100)

    bar_fill = '█' * filled
    bar_empty = '░' * empty
    if label and len(label) > 20:
        label = label[:17] + "..."
    lbl = f" {label}" if label else ""
    erase = "\033[K" if _COLOR else ""
    _write(f"\r  {PINK}{bar_fill}{DARK}{bar_empty}{RESET} {WHITE}{pct:3d}%{RESET}{GREY}{lbl}{RESET}{erase}")
    if current >= total:
        _write("\n")


# ── Spinner class ────────────────────────────────────────────────────

class Spinner:

    def __init__(self, message="Working", frames=None, color=PINK, speed=0.08):
        self.message = message
        self.frames = frames or DEFAULT_SPINNER
        self.color = color
        self.speed = speed
        self._stop_event = threading.Event()
        self._thread = None

    def _animate(self):
        cycle = itertools.cycle(self.frames)
        while not self._stop_event.is_set():
            frame = next(cycle)
            _write(f"\r  {self.color}{frame}{RESET} {GREY}{self.message}{RESET}  ")
            self._stop_event.wait(self.speed)
        erase = "\033[K" if _COLOR else ""
        _write(f"\r{erase}")

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
        return self

    def stop(self, final_message=None):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if final_message:
            _write(f"  {GREEN}✓{RESET} {final_message}\n")

    def fail(self, error_message=None):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        if error_message:
            _write(f"  {RED}✗{RESET} {error_message}\n")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.fail(f"{self.message} — failed")
        else:
            self.stop(self.message)
        return False


# ── Progress tracker ─────────────────────────────────────────────────

class ProgressTracker:

    def __init__(self, total, width=30):
        self.total = max(total, 1)
        self.current = 0
        self.width = width
        self._lines_below = 0
        self._render_bar()
        _write("\n")
        self._lines_below = 1

    def set_total(self, total):
        """Adjust total without changing current progress."""
        self.total = max(total, 1)
        self._update_bar()

    def _render_bar(self):
        frac = min(self.current / self.total, 1.0) if self.total > 0 else 1.0
        filled = int(self.width * frac)
        empty = self.width - filled
        pct = int(frac * 100)
        bar_fill = '\u2588' * filled
        bar_empty = '\u2591' * empty
        erase = "\033[K" if _COLOR else ""
        _write(f"\r  {PINK}{bar_fill}{DARK}{bar_empty}{RESET} {WHITE}{pct:3d}%{RESET}{erase}")

    def _update_bar(self):
        if self._lines_below > 0:
            _write(f"\033[{self._lines_below}A")
        self._render_bar()
        if self._lines_below > 0:
            _write(f"\033[{self._lines_below}B\r")

    def advance(self, n=1):
        """Advance progress by n steps."""
        self.current = min(self.current + n, self.total)
        self._update_bar()

    def finish(self):
        """Ensure bar shows 100%."""
        self.current = self.total
        self._update_bar()

    def _print_line(self, text):
        _write(f"{text}\n")
        self._lines_below += 1

    def step(self, msg):
        self._print_line(f"  {GREEN}\u2713{RESET} {msg}")

    def step_info(self, msg):
        self._print_line(f"  {DARK}\u2192{RESET} {GREY}{msg}{RESET}")

    def step_fail(self, msg):
        self._print_line(f"  {RED}\u2717{RESET} {msg}")

    def step_warn(self, msg):
        self._print_line(f"  {YELLOW}!{RESET} {msg}")

    def header(self, msg):
        _write("\n")
        self._lines_below += 1
        self._print_line(f"  {BOLD}{WHITE}{msg}{RESET}")

    def divider(self):
        cols = shutil.get_terminal_size((80, 24)).columns
        w = min(cols - 4, 50)
        self._print_line(f"  {DARK}{'\u2500' * w}{RESET}")


# ── Step logger ──────────────────────────────────────────────────────

def step(msg):
    """Print a completed step with a checkmark."""
    _write(f"  {GREEN}✓{RESET} {msg}\n")


def step_fail(msg):
    """Print a failed step."""
    _write(f"  {RED}✗{RESET} {msg}\n")


def step_warn(msg):
    """Print a warning step."""
    _write(f"  {YELLOW}!{RESET} {msg}\n")


def step_info(msg):
    """Print an info line (dimmed bullet)."""
    _write(f"  {DARK}→{RESET} {GREY}{msg}{RESET}\n")


def header(msg):
    """Print a bold header line."""
    _write(f"\n  {BOLD}{WHITE}{msg}{RESET}\n")


def divider():
    """Print a subtle divider."""
    cols = shutil.get_terminal_size((80, 24)).columns
    w = min(cols - 4, 50)
    _write(f"  {DARK}{'─' * w}{RESET}\n")


# ── Logo display ─────────────────────────────────────────────────────

def print_logo(animate=True):
    """Print the compact PUREE logo with gradient animation."""
    lines = PUREE_LOGO_COMPACT
    gradient = LOGO_GRADIENT

    _write("\n")
    for i, line in enumerate(lines):
        color = gradient[i % len(gradient)]
        _write(f"{color}{line}{RESET}\n")
        if animate:
            time.sleep(0.04)


# ── High-level wrappers for CLI commands ─────────────────────────────

def banner_init():
    """Animated banner for `puree init`."""
    print_logo(animate=True)
    header("Initializing new Puree project")
    divider()


def banner_build():
    """Banner for `puree build`."""
    print_logo(animate=True)
    header("Building extension")
    divider()


def banner_install():
    """Banner for `puree install`."""
    print_logo(animate=True)
    header("Installing extension")
    divider()


def banner_link():
    """Banner for `puree link`."""
    print_logo(animate=True)
    header("Linking for development")
    divider()


def banner_unlink():
    """Banner for `puree unlink`."""
    print_logo(animate=True)
    header("Unlinking")
    divider()


def banner_reload():
    """Banner for `puree reload`."""
    print_logo(animate=False)


def outro_success(message="Done!"):
    """Print a success outro."""
    _write(f"\n  {GREEN}{BOLD}{'─' * 3} {message} {'─' * 3}{RESET}\n\n")


def outro_fail(message="Failed"):
    """Print a failure outro."""
    _write(f"\n  {RED}{BOLD}{'─' * 3} {message} {'─' * 3}{RESET}\n\n")


# ── Demo (run this file directly) ────────────────────────────────────

if __name__ == "__main__":
    print_logo(animate=True)

    divider()
    header("Step examples")
    step("Created project structure")
    step("Copied wheels")
    step_info("Blender: /usr/bin/blender")
    step_info("Python:  3.13")
    step_warn("SCSS cache may be stale")
    step_fail("Build failed")

    divider()
    header("Spinner demo")

    with Spinner("Compiling shaders"):
        time.sleep(2)

    with Spinner("Packing GPU buffers", frames=SPINNER_BLOCKS, color=CYAN):
        time.sleep(2)

    with Spinner("Cooking UI", frames=SPINNER_COOK, color=CORAL):
        time.sleep(2)

    with Spinner("Blending ingredients", frames=SPINNER_WAVE, color=PEACH):
        time.sleep(2)

    divider()
    header("Progress bar demo")
    for i in range(31):
        progress_bar(i, 30, label="Copying wheels")
        time.sleep(0.05)

    outro_success("All systems go!")
