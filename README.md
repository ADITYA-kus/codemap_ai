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
# Clone or download the repository
git clone https://github.com/yourusername/codemap_ai_clean.git
cd codemap_ai_clean

# Install as a local package
pip install -e .
```

**Verify installation:**
```bash
codemap --help
```

You should see:
```
usage: codemap [-h] {analyze,dashboard,open,cache} ...
```

---

### Step 2️⃣: Analyze Your First Repository

Try with the included demo:

```bash
# Analyze the demo repo (takes 5-10 seconds)
codemap api analyze --path demo_repo
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

Or **analyze your own code**:
```bash
codemap api analyze --path /path/to/your/python/project
```

---

### Step 3️⃣: View in Web Dashboard

```bash
# Start the dashboard
codemap ui --port 8000
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

### Analyze & View
```bash
# Analyze a repository
codemap api analyze --path <repo_directory>

# Start web dashboard
codemap ui --port 8000

# Open dashboard in browser
codemap open
```

### Cache Management
```bash
# List all analyzed repos
codemap cache list

# View cache details
codemap cache info <repo_hash>

# Clear specific cache
codemap cache clear <repo_hash>

# Clear all caches
codemap cache clear --all
```

### Analyze GitHub Repositories
```bash
# Analyze a public GitHub repo (will download it)
codemap api analyze --github https://github.com/owner/repo

# Analyze a private repo (requires GitHub token)
codemap api analyze --github https://github.com/owner/repo --token YOUR_GITHUB_TOKEN
```

**Get GitHub Token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token"
3. Select `repo` scope
4. Copy the token
5. Use in commands: `--token YOUR_TOKEN`

---

## Directory Structure

```
codemap_ai_clean/
├── README.md              # This file
├── cli.py                 # Command-line interface
├── security_utils.py      # Security & secret redaction
├── pyproject.toml         # Package configuration
├── analysis/              # Code analysis engine
│   ├── core/             # AST parsing, imports
│   ├── call_graph/       # Call graph building
│   ├── explain/          # Symbol metadata
│   ├── architecture/     # Dependency analysis
│   └── graph/            # Graph indexing
├── ui/                    # Web dashboard
│   ├── app.py            # FastAPI server
│   ├── templates/        # HTML templates
│   └── static/           # CSS, JavaScript
├── tests/                 # Test suite
└── demo_repo/            # Example repository
```

---

## Features Explained

### 🔍 Symbol Search
Find all functions, classes, and methods in your codebase:

```bash
codemap api search --repo <analyzed_repo_path> --query "class_name"
```

### 📊 Call Graph
Understand how functions call each other:

```bash
codemap api explain --repo <repo_path> --symbol "module.ClassName.method"
```

### ⚠️ Risk Radar
Detect complex code patterns and potential issues:

```bash
codemap api risk_radar --repo <repo_path>
```

### 📈 Impact Analysis
See which files/functions are affected by changes:

```bash
codemap api impact --repo <repo_path> --target "module.function"
```

---

## Troubleshooting

### **"codemap: command not found"**
Make sure you installed the package:
```bash
pip install -e .
```

### **"Repository not analyzed yet"**
Run analysis first:
```bash
codemap api analyze --path <repo_path>
```

### **Port 8000 already in use**
Use a different port:
```bash
codemap ui --port 8001
```

### **GitHub token not working**
- Verify token has `repo` scope
- Make sure it's not expired
- Try: `codemap api analyze --github <url> --token YOUR_TOKEN --refresh`

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

```bash
# 1. Clone a Python project
git clone https://github.com/some/project
cd project

# 2. Analyze it with CodeMap
codemap api analyze --path .

# 3. Start the dashboard
codemap ui --port 8000

# 4. Open browser and explore
# http://127.0.0.1:8000

# 5. Search for a specific class
codemap api search --repo . --query "MyClass"

# 6. Check call graph for a function
codemap api explain --repo . --symbol "module.MyClass.method"
```

---

## Next Steps

- 📚 [Check the demo repo](demo_repo/) for an example
- 🧪 Try analyzing different Python projects
- 📊 Explore the dashboard features
- 🔗 Use GitHub URLs to analyze public repos

---

## Support

- Check error messages - they're usually clear
- Verify Python 3.10+ installed: `python --version`
- Verify pip: `pip --version`
- Check repo path exists and contains `.py` files

---

**Happy coding! 🚀**

