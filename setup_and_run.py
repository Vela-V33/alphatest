#!/usr/bin/env python3
"""
AlphaTest - Setup and Run
Handles first-time setup and launches the web UI.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    venv_dir = script_dir / "venv"
    
    # Determine Python paths
    if sys.platform == "win32":
        python_venv = venv_dir / "Scripts" / "python.exe"
        pip_venv = venv_dir / "Scripts" / "pip.exe"
    else:
        python_venv = venv_dir / "bin" / "python"
        pip_venv = venv_dir / "bin" / "pip"
    
    # Check if setup needed
    if not venv_dir.exists():
        print("")
        print("=" * 55)
        print("  🧪 AlphaTest - First Time Setup")
        print("  This will take 2-3 minutes...")
        print("=" * 55)
        print("")
        
        # Create virtual environment
        print("📦 Creating Python environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        print("   ✓ Done")
        
        # Upgrade pip
        print("⬆️  Upgrading pip...")
        subprocess.run([str(pip_venv), "install", "--upgrade", "pip", "-q"], check=True)
        print("   ✓ Done")
        
        # Install requirements
        print("📥 Installing dependencies...")
        subprocess.run([str(pip_venv), "install", "-r", "requirements.txt"], check=True)
        print("   ✓ Done")
        
        # Install Playwright browser
        print("🌐 Downloading browser...")
        subprocess.run([str(python_venv), "-m", "playwright", "install", "chromium"], check=True)
        print("   ✓ Done")
        
        print("")
        print("=" * 55)
        print("  ✅ Setup Complete!")
        print("=" * 55)
        print("")
    
    # Launch the server
    print("")
    print("🚀 Starting AlphaTest...")
    print("   Opening in your browser...")
    print("")
    
    subprocess.run([str(python_venv), "server.py"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nIf Python is not installed:")
        print("  → Download from https://python.org")
        input("\nPress Enter to close...")
