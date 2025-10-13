## Contributing

</div>

We welcome contributions to puree! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

### Development Setup

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

#### Available Commands

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

### Contribution Guidelines

1. Create a feature branch from `master`
2. Make your changes with clear, descriptive commits
3. Test your changes with `make deploy` in Blender 4.2+
4. Ensure no regressions in existing functionality
5. Submit a pull request with a clear description of changes