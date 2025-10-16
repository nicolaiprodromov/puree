# Contributing

We welcome contributions to puree! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

## Development Setup

1. **Fork and clone the repository:**

    ```bash
    git clone https://github.com/yourusername/puree.git
    cd puree
    ```

2. **Download platform-specific wheels:**

    ```bash
    make wheels
    # or
    just wheels
    ```

### Build Process

Puree uses **Make** or **Just** for build automation. Both systems provide identical functionality with cross-platform support for Windows, Linux, and macOS:

- **Make**: Traditional build tool using `Makefile`. Best for environments where Make is already available.
- **Just**: Modern command runner using `justfile`. Offers simpler syntax and better cross-platform consistency.

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
