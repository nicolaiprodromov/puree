import os
import sys


def strip_rust_comments(source: str) -> str:
    result = []
    i = 0
    n = len(source)

    while i < n:
        if source[i] == '"':
            j = i + 1
            while j < n:
                if source[j] == "\\":
                    j += 2
                    continue
                if source[j] == '"':
                    j += 1
                    break
                j += 1
            result.append(source[i:j])
            i = j

        elif source[i] == "r" and i + 1 < n and source[i + 1] in '#"':
            j = i + 1
            hashes = 0
            while j < n and source[j] == "#":
                hashes += 1
                j += 1
            if j < n and source[j] == '"':
                j += 1
                closing = '"' + "#" * hashes
                end = source.find(closing, j)
                if end == -1:
                    result.append(source[i:])
                    i = n
                else:
                    end += len(closing)
                    result.append(source[i:end])
                    i = end
            else:
                result.append(source[i])
                i += 1

        elif source[i] == "'" and i + 1 < n:
            if i + 2 < n and source[i + 1] == "\\":
                j = i + 3
                if j < n and source[j] == "'":
                    j += 1
                result.append(source[i:j])
                i = j
            elif i + 2 < n and source[i + 2] == "'":
                result.append(source[i : i + 3])
                i += 3
            else:
                result.append(source[i])
                i += 1

        elif source[i : i + 3] in ("///", "//!"):
            j = source.find("\n", i)
            if j == -1:
                result.append(source[i:])
                i = n
            else:
                result.append(source[i:j])
                i = j

        elif source[i : i + 2] == "//":
            line_start = source.rfind("\n", 0, i)
            before = source[line_start + 1 : i] if line_start != -1 else source[:i]
            j = source.find("\n", i)
            if j == -1:
                j = n

            if before.strip() == "":
                start = line_start + 1 if line_start != -1 else 0
                while result and result[-1] in (" ", "\t"):
                    result.pop()
                if start > 0:
                    back = len(source[start:i])
                    while back > 0 and result and result[-1] in (" ", "\t"):
                        result.pop()
                        back -= 1
                if j < n:
                    j += 1
                i = j
            else:
                trimmed = before.rstrip()
                excess = len(before) - len(trimmed)
                if excess > 0:
                    while excess > 0 and result and result[-1] in (" ", "\t"):
                        result.pop()
                        excess -= 1
                i = j

        elif source[i : i + 2] == "/*":
            j = source.find("*/", i + 2)
            if j == -1:
                i = n
            else:
                line_start = source.rfind("\n", 0, i)
                before = source[line_start + 1 : i] if line_start != -1 else source[:i]
                after_end = j + 2
                after = source[after_end : source.find("\n", after_end)] if after_end < n else ""

                if before.strip() == "" and (after.strip() == "" or after_end >= n or source[after_end] == "\n"):
                    start = line_start + 1 if line_start != -1 else 0
                    end = source.find("\n", after_end)
                    if end == -1:
                        end = n
                    else:
                        end += 1
                    while result and result[-1] in (" ", "\t"):
                        result.pop()
                    i = end
                else:
                    i = after_end

        else:
            result.append(source[i])
            i += 1

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

    stripped = strip_rust_comments(original)
    if stripped != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(stripped)
        return True
    return False


def collect_rs_files(paths: list[str]) -> list[str]:
    files = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".rs"):
            files.append(p)
        elif os.path.isdir(p):
            for root, dirs, filenames in os.walk(p):
                dirs[:] = [d for d in dirs if d not in ("target", ".git")]
                for fn in sorted(filenames):
                    if fn.endswith(".rs"):
                        files.append(os.path.join(root, fn))
    return files


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file_or_dir> ...")
        sys.exit(1)

    files = collect_rs_files(sys.argv[1:])
    changed = 0
    for f in files:
        if process_file(f):
            print(f"  stripped: {f}")
            changed += 1
    print(f"  {changed}/{len(files)} files stripped")
