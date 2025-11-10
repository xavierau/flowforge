# PM2 "Script not found" Error with Virtual Environment Python

**Date:** 2025-11-10
**Issue:** PM2 unable to start services with error "Script not found: /home/forge/flowforge_app.activedevelopment.cloud/.venv/bin/python"
**Severity:** High (production deployment blocker)

## Symptoms

```bash
[PM2][ERROR] Error: Script not found: /home/forge/flowforge_app.activedevelopment.cloud/.venv/bin/python
```

PM2 logs showed system Python being used instead of virtual environment:
```
0|ai-docum | /usr/bin/python3: No module named uvicorn
```

## Root Causes

### 1. **Hardcoded Path Mismatch** (Primary Issue)
- **Problem:** `ecosystem.config.js` had hardcoded path `/home/forge/flowforge_app.activedevelopment.cloud`
- **Reality:** Build script showed actual path was `/home/forge/flowforge_app.anacreation.com`
- **Impact:** PM2 couldn't find the Python binary because it was looking in the wrong directory

### 2. **Misunderstanding UV Virtual Environment Structure**
- **Initial assumption:** `.venv/bin/python` should be a real Python binary
- **Reality:** UV creates symlinks by design:
  ```bash
  lrwxrwxrwx 1 forge forge 16 Nov 10 07:10 .venv/bin/python -> /usr/bin/python3
  ```
- **How it works:** Packages are installed in `.venv/lib/python3.12/site-packages`, and Python finds them via `VIRTUAL_ENV` environment variable

### 3. **PM2 Configuration Caching**
- Using `pm2 startOrReload` doesn't update script paths
- Must use `pm2 delete all` before restarting to pick up new configuration

## Solution

### Fix 1: Use Dynamic Path Resolution
**File:** `ecosystem.config.js`

```javascript
// ❌ BEFORE: Hardcoded path (breaks on different servers)
const projectRoot = '/home/forge/flowforge_app.activedevelopment.cloud';

// ✅ AFTER: Dynamic path using __dirname
const projectRoot = __dirname;
const venvPython = path.join(projectRoot, '.venv', 'bin', 'python');
```

### Fix 2: Ensure VIRTUAL_ENV Environment Variable
**File:** `ecosystem.config.js`

```javascript
env: {
  NODE_ENV: 'production',
  VIRTUAL_ENV: path.join(projectRoot, '.venv'),
  PATH: `${path.join(projectRoot, '.venv', 'bin')}:${process.env.PATH}`,
}
```

This ensures Python finds the packages in `.venv/lib/python3.12/site-packages`.

### Fix 3: Auto-Install UV in Build Script
**File:** `build.sh`

```bash
# Install/update uv if needed
if ! command -v uv &> /dev/null; then
    print_status "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Create virtual environment and sync dependencies
uv sync
```

### Fix 4: Proper PM2 Restart Procedure
```bash
git pull origin develop
pm2 delete all  # Required to clear cached paths
bash build.sh --skip-frontend
```

## Troubleshooting Workflow

1. **Verify `.venv` exists and has packages:**
   ```bash
   ls -la .venv/bin/python  # Should show symlink to system Python
   ls .venv/lib/python3.*/site-packages/  # Should show installed packages
   ```

2. **Check actual project path:**
   ```bash
   pwd  # Shows current directory
   ```

3. **Verify PM2 is using correct path:**
   ```bash
   pm2 describe ai-document-processing-api | grep script
   ```

4. **Test Python can import packages:**
   ```bash
   VIRTUAL_ENV=.venv .venv/bin/python -c "import uvicorn; print(uvicorn.__version__)"
   ```

## Prevention Strategies

### 1. Never Hardcode Paths
- ✅ Use `__dirname` in ecosystem.config.js
- ✅ Use `$(pwd)` or relative paths in shell scripts
- ❌ Avoid absolute paths that differ between environments

### 2. Always Set VIRTUAL_ENV
When running Python from a virtual environment in PM2:
```javascript
env: {
  VIRTUAL_ENV: path.join(projectRoot, '.venv'),
  PATH: `${path.join(projectRoot, '.venv', 'bin')}:${process.env.PATH}`,
}
```

### 3. Use PM2 Delete for Configuration Changes
When changing script paths or environment variables:
```bash
pm2 delete all  # Clear old config
pm2 start ecosystem.config.js  # Load new config
```

### 4. Add Debug Output to Build Scripts
```bash
# Show Python binary details
ls -lh .venv/bin/python
file .venv/bin/python
.venv/bin/python --version
pwd  # Show current directory
```

## Related Files

- `ecosystem.config.js:4-8` - Dynamic path resolution
- `ecosystem.config.js:35-38` - VIRTUAL_ENV configuration
- `build.sh:41-54` - UV installation and venv creation
- `build.sh:58-73` - Python binary verification

## Related Issues

- Initial errors: "No module named uvicorn" (system Python being used)
- Multiple attempts with different Python path strategies
- Understanding UV's symlink-based virtual environment structure

## Key Learnings

1. **UV's Design:** UV creates lightweight venvs with symlinks to system Python, not copied binaries
2. **PM2 Path Resolution:** PM2 must be completely restarted (`delete all`) when script paths change
3. **Environment Variables Matter:** `VIRTUAL_ENV` is crucial for Python to find packages
4. **Dynamic Paths:** Always use `__dirname` or dynamic detection, never hardcode server paths
5. **Build Script Debugging:** Adding detailed file info (`ls -lh`, `file`, `pwd`) saves debugging time

## Verification

After fix, PM2 logs should show:
```
Using Python: /home/forge/[actual-path]/.venv/bin/python
[PM2] Process successfully started
```

And service logs should NOT show "No module named uvicorn" errors.

---

**Status:** ✅ Resolved
**Commit:** `ee73e5a` - "fix: use __dirname for dynamic project root path"
**Time to Resolution:** ~2 hours (multiple iterations to understand UV venv structure)
