# OpenCV ImportError in Production (libGL.so.1 Missing)

**Date:** 2025-12-10
**Status:** ✅ Fixed
**Severity:** Critical (Production Down)

## Problem

Celery worker crashes on startup in production with:

```
ImportError: libGL.so.1: cannot open shared object file: No such file or directory
```

### Stack Trace
```
app/tasks/__init__.py → combined_extraction.py → image_preprocessor.py →
app/utils/image_utils.py → cv2 → libGL.so.1 (missing)
```

### Root Cause
The application was using `opencv-python` which includes GUI dependencies (X11/OpenGL). Headless production servers don't have these system libraries installed, causing the import to fail.

## Solution

Replace `opencv-python` with `opencv-python-headless` in dependencies.

### Changes Made

**File:** `pyproject.toml:33`

```diff
- "opencv-python>=4.12.0.88",
+ "opencv-python-headless>=4.12.0.88",
```

### Why This Works
- `opencv-python-headless` provides the same OpenCV functionality without GUI dependencies
- No system libraries (libGL, X11) required
- Perfect for server/headless environments
- Same API, zero code changes needed

## Deployment Steps

### On Production Server

1. **Pull the latest changes:**
   ```bash
   cd /home/forge/flowforge-app.phbsolution.com
   git pull origin develop
   ```

2. **Update dependencies:**
   ```bash
   source .venv/bin/activate
   uv sync
   ```

3. **Restart services:**
   ```bash
   pm2 restart all
   ```

4. **Verify Celery worker starts:**
   ```bash
   pm2 logs ai-document-processing-celery-worker
   ```

   You should see:
   ```
   [timestamp] - celery@hostname ready.
   ```

### Alternative: Quick Fix Without Git Pull

If you need an immediate fix without pulling code:

```bash
cd /home/forge/flowforge-app.phbsolution.com
source .venv/bin/activate
pip uninstall opencv-python -y
pip install opencv-python-headless>=4.12.0.88
pm2 restart all
```

## Verification

### Test cv2 Import
```bash
source .venv/bin/activate
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
```

Expected output:
```
OpenCV version: 4.12.0.88
```

### Check Celery Worker
```bash
pm2 logs ai-document-processing-celery-worker --lines 50
```

Should show:
```
[timestamp] INFO/MainProcess] Connected to redis://localhost:6379/0
[timestamp] INFO/MainProcess] celery@hostname ready.
```

### Test Document Processing
```bash
# Upload a test document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf"

# Check logs for image preprocessing
pm2 logs ai-document-processing-celery-worker | grep "preprocess"
```

## Prevention

### For Future Deployments

The `start-production.sh` script now includes a note about this:

```bash
# start-production.sh:39-40
echo "Note: This project uses opencv-python-headless for server environments."
echo "If you encounter cv2 import errors, ensure you've run 'uv sync' after pulling latest changes."
```

### Development vs Production

| Environment | Package | Why |
|-------------|---------|-----|
| Development (any) | `opencv-python-headless` | Works everywhere, simpler |
| Production (headless) | `opencv-python-headless` | **Required** - no GUI libs |
| Development (with GUI) | `opencv-python` | Optional - for GUI features |

**Recommendation:** Use `opencv-python-headless` everywhere unless you specifically need GUI features (imshow, highgui, etc.)

## Related Issues

- [Common Issues Guide](2025-11-02-common-issues.md#opencv-import-errors)
- OpenCV Docs: [OpenCV-Python Packages](https://github.com/opencv/opencv-python#packages)

## Technical Details

### System Libraries Required by opencv-python (but NOT headless)
- `libGL.so.1` - OpenGL
- `libglib2.0-0` - GLib
- `libsm6` - X11 Session Management
- `libxext6` - X11 extensions
- `libxrender-dev` - X11 Render extension
- `libgomp1` - GNU OpenMP

### Why These Aren't Needed in Production
- No GUI display needed
- All image processing is headless
- Video display/windows not required
- Saves ~200MB of system dependencies

## Files Modified

1. `pyproject.toml:33` - Changed dependency
2. `start-production.sh:39-40` - Added deployment note
3. `docs/troubleshooting/2025-12-10-opencv-headless-production-fix.md` - This file

## References

- **OpenCV-Python Packages:** https://github.com/opencv/opencv-python#packages
- **Headless OpenCV:** https://pypi.org/project/opencv-python-headless/
- **PM2 Documentation:** https://pm2.keymetrics.io/docs/usage/quick-start/
