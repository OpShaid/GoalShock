# GoalShock Backend - Windows Installation Guide

## ✅ Quick Install (Recommended)

\`\`\`cmd
cd backend
setup-windows.bat
\`\`\`

That's it! The script handles everything automatically.

---

## 📋 Requirements

- **Python 3.10, 3.11, or 3.12** (recommended: 3.11)
- **Windows 10 or 11**
- **Internet connection** (for downloading packages)
- **NO compiler needed** - all packages use precompiled Windows wheels

---

## 🚀 Installation Options

### Option 1: Automated Setup (Easiest)

\`\`\`cmd
cd backend
setup-windows.bat
\`\`\`

This script will:
1. Check Python installation
2. Create virtual environment
3. Upgrade pip/setuptools/wheel
4. Install all dependencies with Windows wheels
5. Create .env configuration
6. Start the server automatically

### Option 2: Manual Installation

\`\`\`cmd
cd backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate.bat

# Upgrade pip (important!)
python -m pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirements.txt --prefer-binary

# Create config
copy .env.example .env

# Run server
python main.py
\`\`\`

### Option 3: Docker (Cross-platform)

\`\`\`cmd
cd backend
docker-compose up
\`\`\`

---

## 🐛 Troubleshooting

### Problem: "Python is not recognized"

**Solution:**
1. Install Python from https://www.python.org/downloads/
2. **CHECK "Add Python to PATH"** during installation
3. Restart your terminal
4. Verify: `python --version`

### Problem: "Failed to create virtual environment"

**Solutions:**
- Run terminal as **Administrator**
- Make sure you have write permissions in the folder
- Try: `python -m venv venv --clear`

### Problem: "pydantic-core" or "aiohttp" build errors

**This should NOT happen** with the new requirements.txt, but if it does:

**Solutions:**
1. **Use Python 3.11** (best Windows compatibility)
2. Make sure pip is upgraded: `python -m pip install --upgrade pip`
3. Delete `venv` folder and run `setup-windows.bat` again
4. Try installing with: `pip install --only-binary :all: -r requirements.txt`

### Problem: "Microsoft Visual C++ 14.0 is required"

**Solution:**
The new `requirements.txt` uses precompiled wheels, so this should NOT occur.
If you see this, you're using wrong package versions. Delete `venv` and re-run `setup-windows.bat`.

### Problem: Port 8000 already in use

**Solutions:**
- Option 1: Kill the process using port 8000
  \`\`\`cmd
  netstat -ano | findstr :8000
  taskkill /PID <PID> /F
  \`\`\`

- Option 2: Change port in `.env`
  \`\`\`env
  PORT=8001
  \`\`\`

### Problem: "ImportError" or "ModuleNotFoundError"

**Solutions:**
1. Make sure virtual environment is activated:
   \`\`\`cmd
   venv\Scripts\activate.bat
   \`\`\`
   You should see `(venv)` in your prompt.

2. Reinstall dependencies:
   \`\`\`cmd
   pip install -r requirements.txt --force-reinstall
   \`\`\`

3. Nuclear option - start fresh:
   \`\`\`cmd
   rmdir /s /q venv
   setup-windows.bat
   \`\`\`

---

## 📦 Package Versions

All packages in `requirements.txt` have been tested on Windows and have **precompiled binary wheels** on PyPI:

| Package | Version | Notes |
|---------|---------|-------|
| fastapi | 0.104.1 | Has Windows wheels |
| pydantic | 2.5.0 | Older stable version with wheels |
| pydantic-core | 2.14.1 | Pre-built binary |
| aiohttp | 3.9.1 | Pre-built binary |
| uvicorn | 0.24.0 | Pure Python |

**No Rust compiler needed!**
**No C++ compiler needed!**
**No Visual Studio needed!**

---

## ✅ Verification

After installation, verify everything works:

\`\`\`cmd
# Check Python
python --version

# Check virtual environment
where python
# Should show: ...\venv\Scripts\python.exe

# Check packages
python -c "import fastapi, uvicorn, pydantic, aiohttp; print('All packages installed!')"

# Test API
python -c "import requests; print(requests.get('http://localhost:8000/health').json())"
\`\`\`

---

## 🔧 Advanced Configuration

### Use Different Python Version

If you have multiple Python versions:

\`\`\`cmd
# Use specific version
py -3.11 -m venv venv

# Or with full path
C:\Python311\python.exe -m venv venv
\`\`\`

### Install in Developer Mode

For development with hot reload:

\`\`\`cmd
# Install dev dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --reload
\`\`\`

### Offline Installation

If you need to install without internet:

1. On a machine with internet, download all wheels:
   \`\`\`cmd
   pip download -r requirements.txt --dest wheels
   \`\`\`

2. Copy `wheels` folder to offline machine

3. Install from wheels:
   \`\`\`cmd
   pip install --no-index --find-links=wheels -r requirements.txt
   \`\`\`

---

## 📝 Environment Variables

Edit `.env` file to configure:

\`\`\`env
# Server
PORT=8000
HOST=0.0.0.0
DEBUG=true

# Mode
DEMO_MODE=true

# Risk Parameters
MAX_TRADE_SIZE_USD=1000
MAX_DAILY_LOSS_USD=5000
UNDERDOG_THRESHOLD=0.50

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=true
\`\`\`

---

## 🆘 Still Having Issues?

1. **Check Python version**: `python --version` (should be 3.10, 3.11, or 3.12)
2. **Run as Administrator**: Right-click terminal → "Run as Administrator"
3. **Delete everything and start over**:
   \`\`\`cmd
   rmdir /s /q venv
   del .env
   setup-windows.bat
   \`\`\`

4. **Try Docker instead**:
   \`\`\`cmd
   docker-compose up
   \`\`\`

5. **Check antivirus**: Sometimes antivirus blocks pip/venv

---

## ✨ Success!

If you see:
\`\`\`
Server will be available at:
  - API:       http://localhost:8000
  - API Docs:  http://localhost:8000/docs
  - WebSocket: ws://localhost:8000/ws
\`\`\`

**You're all set!** 🎉

Visit http://localhost:8000/docs to see the API documentation.

---

## 🚀 Next Steps

1. **Start frontend**: Open new terminal, `cd app`, `npm install`, `npm run dev`
2. **Test API**: `python test_api.py`
3. **Read docs**: Check `README.md` for usage guide

---

**Questions?** Check `README.md` or `backend/README.md` for more details.
