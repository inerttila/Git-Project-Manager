# How to Start the App

## Quick Start (Double-Click Method)

### Option 1: With Console Window (Recommended for debugging)
1. Double-click `start_app.bat`
2. A console window will open showing the server status
3. Your browser will open automatically to http://localhost:5000
4. Keep the console window open while using the app
5. Press Ctrl+C to stop the server

### Option 2: Silent Start (No console window)
1. Double-click `start_app_silent.bat`
2. The app will start in the background
3. Your browser will open automatically
4. To stop the server, close the Python process from Task Manager

## What the Batch Files Do

- **start_app.bat**: 
  - Shows a console window with server logs
  - Automatically activates virtual environment if it exists
  - Installs dependencies if needed
  - Starts the Flask server
  - Keeps window open for debugging

- **start_app_silent.bat**:
  - Runs in background (no console window)
  - Automatically opens browser
  - Best for regular use

## Requirements

- Python 3.7+ must be installed and in your system PATH
- If you have a virtual environment, the batch file will use it automatically
- If not, it will use your system Python

## Troubleshooting

If the app doesn't start:
1. Make sure Python is installed: Open Command Prompt and type `python --version`
2. If Python is not found, install it from python.org
3. Make sure you're double-clicking the .bat file, not the .py file
4. Check that all files are in the same folder
