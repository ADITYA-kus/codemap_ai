# CodeMap

**CodeMap** is a pure local developer tool that analyzes Python codebases and provides:

- 📊 **Architecture Analysis** - Understand code structure, dependencies, and call graphs
- 🦺 **Call Graph Extraction** - Trace function/method calls across your codebase
- ⚠️ **Risk Analysis** - Identify complex code patterns and potential issues
- 📈 **Symbol Indexing** - Search and explore functions, classes, and methods
- 🌐 **Local Web Dashboard** - Visual code analysis interface
- 🔐 **Privacy First** - All analysis runs locally, no data leaves your machine

## Requirements

- **Python 3.10+**
- **pip** (Python package manager)
- **~5 minutes** to get started

## Quick Start (3 Steps)

### Step 1️⃣: Install CodeMap

```bash
# Install from PyPI (easiest)
pip install codemap-python
```

**Verify installation:**
```bash
codemap --help
```

You should see:
```
usage: codemap [-h] {analyze,dashboard,open,cache} ...
```
### Step 2️⃣: Analyze Your First Repository

**IMPORTANT:** The `analyze` command REQUIRES the `--path` argument pointing to a directory!

```bash
# Analyze the demo repo (takes 5-10 seconds)
codemap analyze --path demo_repo
```

**Output: JSON analysis data**
```json
{
  "ok": true,
  "cache_dir": ".codemap_cache/...",
  "analysis_version": "2.2",
  "repo_dir": "demo_repo"
}
```

**Analyze your own Python project:**
```bash
codemap analyze --path /path/to/your/python/project
```

**Analyze a GitHub repository:**
```bash
codemap analyze --github https://github.com/owner/repo
```

---

### Step 3️⃣: View in Web Dashboard

```bash
# Start the web dashboard
codemap dashboard --port 8000
```

**Open in browser:**
```
http://127.0.0.1:8000
```

You'll see:
- List of analyzed repositories
- Call graphs
- Architecture metrics
- Risk analysis
- Symbol search

---

## Common Commands

### Analyze Commands
```bash
# ⚠️ REQUIRED: Analyze needs --path argument!

# Analyze a local repository
codemap analyze --path <repo_directory>

# Analyze a GitHub repository (public)
codemap analyze --github https://github.com/owner/repo

# Analyze private GitHub repo (requires token)
codemap analyze --github https://github.com/owner/private-repo --token YOUR_GITHUB_TOKEN

# Force rebuild analysis (ignore cache)
codemap analyze --path <repo_directory> --rebuild

# Use API for detailed JSON output
codemap api analyze --path <repo_directory>
```

### Dashboard Commands
```bash
# Start web dashboard (default: localhost:8000)
codemap dashboard --port 8000

# Start dashboard with auto-reload (development)
codemap dashboard --port 8000 --reload

# Open dashboard in browser
codemap open --port 8000
```




[![Watch Demo](https://img.youtube.com/vi/MG6bgVk-uUU/0.jpg)](https://www.youtube.com/watch?v=MG6bgVk-uUU)

### Cache Management
```bash
# 📋 List all analyzed repositories and their cache info
codemap cache list

# 📊 Show detailed cache information for a specific repository
codemap cache info --path <repo_directory>

# ⏱️ Set cache retention policy (automatically clean old caches)
codemap cache retention --path <repo_directory> --days 30 --yes

# 🧹 Preview what would be cleaned (safe, no deletion)
codemap cache sweep --dry-run

# 🧹 Actually clean up expired caches (requires --yes confirmation)
codemap cache sweep --yes

# 🗑️ Clear cache for a specific repository (preview first)
codemap cache clear --path <repo_directory> --dry-run

# 🗑️ Actually delete a repository's cache (requires --yes confirmation)
codemap cache clear --path <repo_directory> --yes
```

**Cache Management Tips:**
- ✅ Always use `--dry-run` first to preview changes
- ✅ Add `--yes` flag to skip confirmation (useful in scripts)
- ✅ Default retention is 14 days; adjust with `--days <number>`
- ✅ Cache is stored in: `~/.codemap_cache/` (varies by OS)
- ✅ Use `cache list` to see all cached repositories and their sizes

**Get GitHub Token (for private repos):**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name (e.g., "CodeMap")
4. Select **`repo`** scope (full control of private repos)
5. Copy the token and save it somewhere safe
6. Use in commands: `--token ghp_xxxxx`

**Or pass token via stdin (more secure):**
```bash
echo "YOUR_TOKEN" | codemap analyze --github https://github.com/owner/repo --token-stdin
```
---

## Features Explained

### 🔍 Symbol Search
Find all functions, classes, and methods in your codebase:

```bash
codemap api search --path <repo_path> --query "MyClass"
codemap api search --path <repo_path> --query "function_name"
```

### 📊 Call Graph
Understand how functions call each other:

```bash
codemap api explain --path <repo_path> --symbol "module.ClassName.method"
```

### ⚠️ Risk Radar
Detect complex code patterns and potential issues:

```bash
codemap api risk_radar --path <repo_path>
```

### 📈 Impact Analysis
See which files/functions are affected by changes:

```bash
codemap api impact --path <repo_path> --target "module.function"
```

---









## Privacy & Security

✅ **100% Local**
- All analysis happens on your machine
- No data sent to external servers
- .env files and secrets are never exposed

✅ **Secure Cache**
- Analysis results cached locally
- Cache auto-cleared after 14 days (configurable)
- No credentials stored

✅ **Secret Redaction**
- API keys automatically masked in output
- GitHub tokens never logged
- Safe error messages

---

## Example Workflow

### Local Project Analysis
```bash
# 1. Navigate to your Python project
cd C:\Users\YourName\my_python_project

# 2. Analyze it with CodeMap
codemap analyze --path .
# ✅ Analysis complete! Results cached locally

# 3. Start the web dashboard
codemap dashboard --port 8000
# ✅ Dashboard running at http://127.0.0.1:8000

# 4. Open in browser
codemap open --port 8000

# 5. Explore in browser:
#    - View all repositories
#    - See call graphs
#    - Check architecture metrics
#    - View risk analysis

# 6. Search for a specific class
codemap api search --path . --query "MyClass"

# 7. Check call graph for a function
codemap api explain --path . --symbol "mymodule.MyClass.method"
```

### GitHub Repository Analysis
```bash
# 1. Analyze a public GitHub repo
codemap analyze --github https://github.com/owner/awesome-project
# ✅ Downloaded and analyzed

# 2. View in dashboard
codemap dashboard --port 8000
codemap open --port 8000

# 3. Clean up old repos
codemap cache list      # See all cached repos
codemap cache sweep    # Auto-cleanup old ones
```

---

## Next Steps

1. 🎯 **First analysis** - Try the demo:
   ```bash
   codemap analyze --path demo_repo
   ```

2. 📊 **View results** - Open the dashboard:
   ```bash
   codemap dashboard --port 8000
   ```

3. 📁 **Analyze your code** - Point to your project:
   ```bash
   codemap analyze --path ~/my-project
   ```

4. 🔗 **Try GitHub** - Analyze public repos:
   ```bash
   codemap analyze --github https://github.com/owner/repo
   ```

5. 🚀 **Advanced features** - Explore search, impact, risk analysis:
   ```bash
   codemap api search --path . --query "YourClass"
   ```

---

## Quick Reference

```bash
# Installation
pip install -e .

# Most common commands
codemap analyze --path <directory>              # Analyze local repo
codemap analyze --github <url>                  # Analyze GitHub repo
codemap dashboard --port 8000                   # Start dashboard
codemap open --port 8000                        # Open in browser
codemap cache list                              # List all analyses
codemap cache clear <hash>                      # Delete one analysis
```

---

## Support & Help

✅ **Run without arguments** to see all available commands:
```bash
codemap --help
codemap analyze --help
codemap dashboard --help
codemap api --help
```

✅ **Check requirements:**
```bash
python --version          # Should be 3.10+
pip --version             # Should be installed
git --version             # For GitHub repos
```

✅ **Verify repo path:**
```bash
# Make sure your repo has Python files
dir <your_repo>                 # Windows
ls <your_repo>                  # Linux/Mac
find <your_repo> -name "*.py"   # Find Python files
```

---

**Happy coding! 🚀**

---

**GitHub:** https://github.com/ADITYA-kus/codemap_ai

