# Contributing to CodeMap

Thank you for your interest in contributing to CodeMap! 🎉

This guide explains how our CI pipeline works and what you need to do before submitting a pull request.

## CI Pipeline Overview

Every push and pull request goes through automated checks to ensure code quality and user safety.

### Checks We Run

1. **🔍 Syntax Check** - Validates all Python files have correct syntax
2. **📦 Package Build** - Ensures the package builds successfully
3. **🧪 Test Suite** - Runs all unit tests
4. **🛡️ File Validation** - Checks critical files exist and no secrets are hardcoded
5. **🎯 CLI Tests** - Verifies all CLI commands work correctly

## Before You Submit a PR

### 1. **Local Testing**

Test your changes locally before pushing:

```bash
# Install dependencies
pip install -e .

# Run linting (optional but recommended)
pip install pylint
pylint $(find . -name "*.py" -not -path "./__pycache__/*")

# Run tests
pip install pytest
pytest tests/ -v

# Test CLI commands
codemap --help
codemap analyze --help
codemap dashboard --help
```

### 2. **Check for Secrets**

Never commit API keys, tokens, or passwords:

```bash
# Search for potential secrets (before committing)
grep -r "sk-\|ghp_\|Bearer\|password" . --include="*.py"
```

If you accidentally added secrets:
1. Don't push yet
2. Remove them: `git rm --cached <file>`
3. Update your git history with `git filter-branch` (if already pushed)
4. Rotate the exposed secret on the service

### 3. **Git Workflow**

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes and test locally
# ... (test everything)

# Commit with clear message
git commit -m "Add: Description of changes"

# Push to your fork
git push origin feature/your-feature-name

# Create pull request on GitHub
# Describe what changed and why
```

## What Happens on PR

1. **Automatic Checks Run** - All CI jobs start immediately
2. **Status Visible** - See results in the PR checks section
3. **Must Pass** - All checks must pass before merging
4. **Review + Merge** - If checks pass, maintainers review and merge

## Common Issues

### ❌ "Python syntax error"

**Problem:** Your Python file has invalid syntax

**Fix:**
```bash
python -m py_compile your_file.py
```

Check the error output and fix the syntax.

### ❌ "Package build failed"

**Problem:** Dependencies missing or setup.py issue

**Fix:**
```bash
pip install -e . --force-reinstall --no-deps
```

### ❌ "Hardcoded secrets detected"

**Problem:** You committed an API key or password

**Fix:**
1. Remove from code
2. Add to `.gitignore`
3. Use environment variables instead:

```python
# ❌ Wrong
API_KEY = "sk-abc123"

# ✅ Right
import os
API_KEY = os.getenv("API_KEY")
```

### ❌ "Tests failing"

**Problem:** Your changes broke existing tests

**Fix:**
```bash
# Run tests locally to see what broke
pytest tests/ -v

# Fix your code or update tests as needed
```

## Code Style

### Python

- Use clear variable names
- Add docstrings to functions
- Keep functions small and focused
- Use type hints when possible

```python
def analyze_repo(path: str) -> dict:
    """Analyze a Python repository.
    
    Args:
        path: Directory path to analyze
        
    Returns:
        Dictionary with analysis results
    """
    ...
```

### Commits

- Use present tense: "Add feature" not "Added feature"
- Keep commits focused on one change
- Reference issues: "Fixes #123"

```bash
git commit -m "Add: Dark theme toggle with localStorage persistence"
git commit -m "Fix: Theme not loading on page load (#15)"
git commit -m "Docs: Update installation guide"
```

## Reporting Issues

Found a bug? Create an issue with:

1. **Description** - What's the problem?
2. **Steps to reproduce** - How to trigger it?
3. **Expected behavior** - What should happen?
4. **Actual behavior** - What actually happened?
5. **Environment** - OS, Python version, etc.

Example:
```
## Syntax error on Windows

**Description**
When running `codemap analyze` on Windows with spaces in path, 
I get a syntax error.

**Steps to reproduce**
1. Create folder: `D:\My Projects\test-repo`
2. Run: `codemap analyze --path "D:\My Projects\test-repo"`

**Expected**
Analysis should complete successfully

**Actual**
Got: `SyntaxError: invalid character in path`

**Environment**
- OS: Windows 11
- Python: 3.10.5
```

## Development Resources

- **Main Code:** `analysis/` folder contains the analysis engine
- **UI:** `ui/` folder contains the web dashboard
- **CLI:** `cli.py` and `codemap_cli.py` are the command-line interface
- **Tests:** `tests/` folder contains unit tests
- **Docs:** `README.md` and `.github/workflows/` for CI config

## Need Help?

- Check existing issues: https://github.com/ADITYA-kus/codemap_ai/issues
- Ask a question in a new issue
- Review the code comments in source files

## License

By contributing to CodeMap, you agree your code will be licensed under the MIT License.

---

**Thanks for contributing to CodeMap! Your help makes it better for everyone.** 🚀
