# Release Process

This project uses automated GitHub Actions to create releases.

## How to Create a Release

### Quick Method (Recommended)

Use the `just` command to handle everything automatically:

```powershell
just release 0.0.7
```

This will:
1. Update the version in `blender_manifest.toml` and `__init__.py`
2. Commit the version bump
3. Create and push a git tag
4. Trigger the GitHub Actions workflow to build and publish the release

### Manual Method

If you prefer to do it manually:

1. Update the version:
   ```powershell
   just update_version 0.0.7
   ```

2. Commit the changes:
   ```powershell
   git add blender_manifest.toml __init__.py
   git commit -m "Bump version to 0.0.7"
   ```

3. Create and push the tag:
   ```powershell
   git tag v0.0.7
   git push origin master
   git push origin v0.0.7
   ```

## What Happens Next

Once you push a tag (e.g., `v0.0.7`), GitHub Actions will:

1. **Checkout** the code at that tag
2. **Download** Blender 4.2 automatically
3. **Build** the addon zip file (`Puree_UI_0.0.7.zip`)
4. **Create** a new GitHub release with:
   - The zip file as a downloadable asset
   - Installation instructions
   - Release notes

## Checking Release Status

After pushing a tag:
1. Go to your repository on GitHub
2. Click the **Actions** tab
3. You'll see the release workflow running
4. Once complete, check the **Releases** page

## Important Notes

- **Version format**: Always use semantic versioning (e.g., `0.0.7`, `1.2.3`)
- **Tag format**: Tags must start with `v` (e.g., `v0.0.7`)
- **No updates**: Each release is permanent - create new versions instead of updating
- **Build time**: The workflow takes ~5-10 minutes (downloads Blender, builds addon)

## Troubleshooting

If the release fails:
1. Check the Actions tab for error logs
2. Ensure the version in `blender_manifest.toml` matches your tag
3. Verify all required files are committed
4. Make sure you have the necessary GitHub permissions

## Example Workflow

```powershell
just release 0.1.0
```

Wait 5-10 minutes, then visit:
```
https://github.com/nicolaiprodromov/puree/releases
```

Your new release will be there with the downloadable zip file!
