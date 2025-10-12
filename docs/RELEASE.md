# Release Process

This project uses a local build + automated GitHub release process.

## Prerequisites

Before creating a release, ensure you have:

1. **Blender 4.2+** installed on your system
2. **Python 3.10+** installed
3. **GitHub CLI (`gh`)** installed and authenticated
   - Install: [https://cli.github.com/](https://cli.github.com/)
   - Authenticate: `gh auth login`
4. **Just** or **Make** installed for task automation

## How to Create a Release

### Quick Method (Recommended)

Use the `just` command to handle everything automatically:

```powershell
just release 0.0.8
```

This single command will:
1. Update version in `blender_manifest.toml` and `__init__.py`
2. Commit the version bump
3. Push changes to GitHub
4. Build the addon zip locally (using your installed Blender)
5. Create a GitHub release with the zip file attached
6. Create and push the git tag

### Manual Method

If you prefer to do it step by step:

1. **Update the version:**
   ```powershell
   just update_version 0.0.8
   ```

2. **Commit the changes:**
   ```powershell
   git add blender_manifest.toml __init__.py
   git commit -m "Bump version to 0.0.8"
   git push origin master
   ```

3. **Build and release:**
   ```powershell
   cd dist
   python release.py 0.0.8
   ```

## What Happens

The release script (`dist/release.py`) does the following:

1. **Builds locally** - Uses your installed Blender to package the addon (fast, no download needed)
2. **Creates GitHub release** - Uses GitHub CLI to create a release with:
   - Tag: `v0.0.8`
   - Release name: `Puree UI 0.0.8`
   - Attached zip file: `Puree_UI_0.0.8.zip`
   - Installation instructions in release notes

## Checking Release Status

After running the release command, you'll see:
- Build progress messages
- GitHub release creation status
- Direct link to the release page

Visit your releases at: `https://github.com/nicolaiprodromov/puree/releases`

## Important Notes

- **Version format**: Use semantic versioning (e.g., `0.0.8`, `1.2.3`)
- **Local build**: Builds happen on your machine, so make sure Blender is installed
- **Git tag**: The tag is created automatically during the release process
- **Fast process**: Takes ~30 seconds (vs 5-10 minutes with GitHub Actions)
- **GitHub CLI required**: Make sure `gh` is installed and authenticated

## Installing GitHub CLI

### Windows
```powershell
winget install --id GitHub.cli
```

### macOS
```bash
brew install gh
```

### Linux
```bash
sudo apt install gh
```

After installing, authenticate:
```bash
gh auth login
```

## Troubleshooting

### "gh: command not found"
Install GitHub CLI from [https://cli.github.com/](https://cli.github.com/)

### "Blender not found"
Ensure Blender 4.2+ is installed in the standard location

### "Release already exists"
The script will automatically delete and recreate the release

### Build fails
- Check that Blender is properly installed
- Verify `dist/build.bat` works manually
- Ensure all required files are present

## Example Workflow

```powershell
just release 0.1.0
```

Output:
```
Updating version to 0.1.0...
Version updated to 0.1.0
Committing version bump...
[master abc1234] Bump version to 0.1.0
Building and releasing v0.1.0...
Building addon version 0.1.0...
Build successful: X:\path\to\dist\Puree_UI_0.1.0.zip
Creating GitHub release v0.1.0...
Release created successfully!
URL: https://github.com/nicolaiprodromov/puree/releases/tag/v0.1.0
Release v0.1.0 completed!
```

Done! Your release is now live on GitHub.
