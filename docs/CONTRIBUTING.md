# Contributing

We welcome contributions to puree! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

## Development Setup

Puree uses **Make** or **Just** for build automation. Both systems provide identical functionality with cross-platform support for Windows, Linux, and macOS:

<details>
<summary>
🖥️ Click here for installation commands
</summary>

<br>

- Linux:

<pre>
<code class="language-bash">
    sudo apt update
    sudo apt install make
    sudo snap install --edge --classic just
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
</code>
</pre>

- MacOS:
<pre>
<code class="language-bash">
    brew install make
    brew install just
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
</code>
</pre>

- Windows:

<pre>
<code class="language-bash">
    choco install make
    winget install --id Casey.Just
    winget install Rustlang.Rustup
</code>
</pre>
</details>

1. Install the following:

    | Dependencies |
    |-------------|
    | [Blender 5.1+](https://www.blender.org/download/) (must be on PATH) |
    | [Make](https://makefiletutorial.com/) / [Just](https://just.systems/man/en/) |
    | [Rust](https://rust-lang.org/tools/install/) |
    | [Python 3.10+](https://www.python.org/downloads/) |

2. Clone this repository.

    ```plaintext
    git clone https://github.com/nicolaiprodromov/puree
    cd puree
    ```

3. Run `just wheels` or `make wheels` to download the python dependencies and add them automatically to the manifest file
4. Run `just build_core` to build the core binaries
5. Run `just link` to symlink the source into Blender's extensions directory (auto-installs wheel dependencies)
6. Open Blender — the addon is live. A built-in reload server (TCP on port 19746) starts automatically with the addon.
    - Use `just reload` (or `puree reload`) after making code changes (triggers reload via the TCP server).
    - Use `just tail` to live-follow the log, or `just logs` to see the last 50 lines.
    - Or use `just deploy` as a shortcut for `just link && just reload`.

### Available Commands

| Command | Description |
|---------|-------------|
| `just build_core` | Compile Rust native binary |
| `just build_package` | Build the Python puree package |
| `just build` | Build extension zip using Blender on PATH |
| `just link` | Symlink source into Blender extensions for development (auto-installs deps) |
| `just unlink` | Remove dev symlinks |
| `just reload` | Reload addon in running Blender (via built-in TCP reload server) |
| `just tail` | Live-follow the Puree log file |
| `just logs` | Print last 50 lines of the log (`just logs 100` for more) |
| `just clear-logs` | Delete all log files |
| `just refresh <folder>` | Refresh `puree_ui` wheel in a target project after engine changes |
| `just deploy` | Link + reload (quick dev cycle) |
| `just install` | Install puree CLI locally for testing (creates .venv) |
| `just venv` | Create venv and install CLI in editable mode |
| `just install-deps` | Install wheel dependencies into Blender’s extension site-packages |
| `just wheels` | Download platform-specific dependency wheels |
| `just bump x.y.z` | Update version across all project files and rebuild |
| `just release x.y.z` | Bump, commit, tag, and push — GitHub Actions handles build & publish |
| `just ci` | Run all CI checks locally (Python lint/format, Rust build/clippy/test/fmt) |

> All `just` commands have `make` equivalents (`make deploy`, `make link`, etc.)

> [!NOTE]
> Before bumping version, make sure all changes are committed.

## CI / CD

CI runs automatically on every push to `master` and on all pull requests. It checks:
- **Python**: `ruff check` (lint) + `ruff format --check` (formatting) + YAML validation + package build
- **Rust**: `cargo build --release` + `cargo clippy` + `cargo test` + `cargo fmt --check`

Run the same checks locally before pushing:

```bash
just ci
```

If CI fails on your PR, check the **Actions** tab on GitHub for details.

Releases are automated: `just release x.y.z` bumps the version, tags, and pushes. GitHub Actions then builds cross-platform wheels, publishes to PyPI, and creates a GitHub Release.

See [CI/CD Guide](tmp/CICD.md) for full details.

## Contribution Guidelines

1. Create a feature branch from `master`
2. Make your changes with clear, descriptive commits
3. Run `just ci` to verify your changes pass all checks
4. Test your changes with `just link && just reload` (or `puree link && puree reload`) in Blender 5.1+
5. Ensure no regressions in existing functionality
6. Submit a pull request with a clear description of changes

### All contributions to this repository must adhere to the following rules

- Commits must be made in English.
- Commit messages must be in [imperative mood](https://chris.beams.io/posts/git-commit/#imperative).
- Commits must be atomic (i.e., each commit should represent a single logical change).

### All commits must follow the following format

```html
<type>(<scope>): <short description>
```

### Types of commits

- `feat`    : A new feature.
- `fix`     : A bug fix.
- `docs`    : Documentation changes.
- `style`   : Code style changes (e.g., formatting, no functional change).
- `refactor`: Code changes that neither add features nor fix bugs.
- `test`    : Adding or modifying tests.
- `chore`   : Maintenance tasks (e.g., updating dependencies).

### Examples

1. **Simple Feature Commit**
   ```
   feat(auth): add user login endpoint
   ```

2. **Bug Fix**
   ```
   fix(ui): resolve button alignment issue on mobile
   ```

3. **Documentation Update**
   ```
   docs(readme): update installation instructions
   ```

4. **Refactor with Scope**
   ```
   refactor(database): optimize query performance
   ```

5. **Chore with No Scope**
   ```
   chore: update npm dependencies to latest versions
   ```
