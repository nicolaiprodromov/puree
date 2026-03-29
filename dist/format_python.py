import sys
import tokenize
import io
import os


def strip_comments(source: str) -> str:
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    lines = source.splitlines(True)
    removals: list[tuple[int, int, int, int]] = []

    for tok in tokens:
        if tok.type != tokenize.COMMENT:
            continue
        text = tok.string.strip()
        if text.startswith("#!"):
            continue
        if "type: ignore" in text or "type:ignore" in text:
            continue
        if "noqa" in text:
            continue
        srow, scol = tok.start
        erow, ecol = tok.end
        removals.append((srow, scol, erow, ecol))

    for srow, scol, erow, ecol in reversed(removals):
        line = lines[srow - 1]
        before = line[:scol]
        after = line[ecol:]
        new_line = before.rstrip() + after
        if new_line.strip() == "":
            lines[srow - 1] = None
        else:
            lines[srow - 1] = new_line

    result = []
    for line in lines:
        if line is None:
            continue
        result.append(line)

    text = "".join(result)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def process_file(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            original = f.read()
    except (UnicodeDecodeError, PermissionError):
        return False

    if not original.strip():
        return False

    try:
        stripped = strip_comments(original)
    except tokenize.TokenError:
        return False

    if stripped != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(stripped)
        return True
    return False


def collect_py_files(paths: list[str]) -> list[str]:
    files = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".py"):
            files.append(p)
        elif os.path.isdir(p):
            for root, dirs, filenames in os.walk(p):
                dirs[:] = [
                    d for d in dirs
                    if d not in ("__pycache__", ".venv", "venv", "node_modules", "target", ".git")
                ]
                for fn in sorted(filenames):
                    if fn.endswith(".py"):
                        files.append(os.path.join(root, fn))
    return files


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file_or_dir> ...")
        sys.exit(1)

    targets = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--dir":
            i += 1
            while i < len(sys.argv) and not sys.argv[i].startswith("-"):
                targets.append(sys.argv[i])
                i += 1
        else:
            targets.append(sys.argv[i])
            i += 1

    files = collect_py_files(targets)
    changed = 0
    for f in files:
        if process_file(f):
            print(f"  stripped: {f}")
            changed += 1
    print(f"  {changed}/{len(files)} files stripped")
