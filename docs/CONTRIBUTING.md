## Contributing

</div>

We welcome contributions to Puree! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

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

Puree uses **Make** or **Just** for build automation. The build system supports Windows, Linux, and macOS:

| Command | Description |
|---------|-------------|
| `make build` / `just build` | Packages the addon into a zip file in `dist/` |
| `make install` / `just install` | Installs the addon to Blender (requires [Blender MCP](https://github.com/XWZ/blender-mcp-addon)) |
| `make uninstall` / `just uninstall` | Removes the addon from Blender |
| `make deploy` / `just deploy` | Full workflow: downloads wheels, builds, uninstalls old version, installs new version |
| `make update_version VERSION=x.y.z` | Updates version in `blender_manifest.toml` and `__init__.py` |

### Contribution Guidelines

1. Create a feature branch from `master`
2. Make your changes with clear, descriptive commits
3. Test your changes with `make deploy` in Blender 4.2+
4. Ensure no regressions in existing functionality
5. Submit a pull request with a clear description of changes