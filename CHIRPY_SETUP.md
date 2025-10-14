# Chirpy Theme Setup for Puree Documentation

## What I've Done

I've set up the Chirpy Jekyll theme for your GitHub Pages documentation. Here's what was created:

### Files Created:

1. **`.github/workflows/pages.yml`** - GitHub Actions workflow to build and deploy the site
2. **`docs/Gemfile`** - Ruby dependencies for the Chirpy theme
3. **`docs/_tabs/home.md`** - Your main homepage (converted from index.md)
4. **`docs/_tabs/documentation.md`** - Documentation page
5. **`docs/_tabs/support.md`** - Support page
6. **Updated `docs/_config.yml`** - Configured for Chirpy theme

### How to Enable It:

1. **Push these changes to GitHub:**
   ```powershell
   git add .
   git commit -m "Add Chirpy theme to documentation"
   git push
   ```

2. **Enable GitHub Actions for Pages:**
   - Go to your repo: https://github.com/nicolaiprodromov/puree
   - Settings → Pages
   - Under "Build and deployment" → Source: Select **GitHub Actions**
   - Save

3. **Wait for the workflow to complete** (1-2 minutes)
   - Go to Actions tab to watch the build
   - Once done, your site will be live at: https://nicolaiprodromov.github.io/puree

### Features You Get:

- ✅ **Dark theme by default** (GitHub-style dark mode)
- ✅ **Responsive design** (mobile-friendly)
- ✅ **Search functionality** (built-in)
- ✅ **Table of contents** (auto-generated)
- ✅ **Sidebar navigation** with tabs
- ✅ **Syntax highlighting** for code blocks
- ✅ **SEO optimized**
- ✅ **RSS feed**

### Chirpy Special Features:

Use these in your markdown files:

```markdown
> This is a tip
{: .prompt-tip }

> This is a warning
{: .prompt-warning }

> This is important info
{: .prompt-info }

> This is danger/error
{: .prompt-danger }
```

### Troubleshooting:

If the build fails:
1. Check the Actions tab for error messages
2. Make sure GitHub Pages is set to "GitHub Actions" source
3. Verify all files are committed and pushed

### To Test Locally (Optional):

```powershell
cd docs
bundle install
bundle exec jekyll serve
# Visit http://localhost:4000/puree
```

## What Happened to Old Files:

- `docs/index.md` - Keep it for now, but it won't be used (tabs system replaced it)
- `docs/assets/css/style.scss` - Not needed anymore (Chirpy has its own dark theme)

You can delete these after confirming the new theme works!
