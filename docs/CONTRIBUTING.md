# Contributing

We welcome contributions to puree! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

## Development Setup

Puree uses **Make** or **Just** for build automation. Both systems provide identical functionality with cross-platform support for Windows, Linux, and macOS:

<details>
<summary>
Click here for installation commands
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
    | [Blender 4.1+](https://www.blender.org/download/) |
    | [Make](https://makefiletutorial.com/) / [Just](https://just.systems/man/en/) |
    | [Rust](https://rust-lang.org/tools/install/) |
    | [Python 3.10+](https://www.python.org/downloads/) |
    | [Blender MCP Addon](https://github.com/XWZ/blender-mcp-addon) |

2. Clone this repository.

    ```plaintext
    git clone https://github.com/nicolaiprodromov/puree
    cd puree
    ```

3. Run `just wheels` or `make wheels` to download the python dependencies and add them automatically to the manifest file
4. Run `just build_core` or `make build_core` to build the core binaries
5. Run `just build_package` or `make build_package` to build the python package.
6. Run `just build` or `make build` to build the addon zip file (make sure Blender is running).
7. Run `just install` or `make install` to install the addon in Blender.
    - Alternatively, run `just deploy` or `make deploy` to build core, build package, and build and install addon in one command (make sure Blender is running).

### Available Commands

| Command | Description |
|---------|-------------|
| `make build` / `just build` | Packages the addon into a zip file in `dist/` |
| `make install` / `just install` | Installs the addon to Blender (requires [Blender MCP](https://github.com/XWZ/blender-mcp-addon)) |
| `make uninstall` / `just uninstall` | Removes the addon from Blender |
| `make wheels` / `just wheels` | Downloads platform-specific dependency wheels to `puree/wheels/` |
| `make build_package` / `just build_package` | Builds the python puree package |
| `make deploy` / `just deploy` | Full workflow: builds package & addon, creates zip, uninstalls old version, installs new version |
| `make bump VERSION=x.y.z` / `just bump x.y.z` | Updates version across all project files and rebuilds |
| `make release VERSION=x.y.z` / `just release x.y.z` | Complete release workflow: bumps version, commits, pushes, and creates GitHub release |

> [!NOTE]
> Before bumping version, make sure all changes are commited.

## Contribution Guidelines

1. Create a feature branch from `master`
2. Make your changes with clear, descriptive commits
3. Test your changes with `make deploy` in Blender 4.2+
4. Ensure no regressions in existing functionality
5. Submit a pull request with a clear description of changes

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
