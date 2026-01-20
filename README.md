# Git Project Manager

A web application to manage multiple Git projects from a single interface. Add your local project directories and perform Git operations like checking status, switching branches, and pulling changes.

## Features

- 📁 Add and manage multiple project directories
- 📊 View Git status and current branch
- 🔄 Switch between Git branches
- ⬇️ Pull changes from remote repository
- 🎨 Modern, responsive UI

## Requirements

- Python 3.7+
- Git installed on your system

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

## Usage

1. **Add a Project**: Click the "+ Add Project" button and enter the full path to your project directory.

2. **View Project Actions**: Click on any project card (or the three dots menu) to see available Git operations.

3. **Git Operations**:
   - **Show Git Status**: View the current branch and repository status
   - **Switch Branch**: Enter a branch name to checkout
   - **Pull Changes**: Pull the latest changes from the remote repository

## API Endpoints

- `GET /api/projects` - Get all projects
- `POST /api/projects` - Add a new project
- `DELETE /api/projects/<id>` - Delete a project
- `GET /api/projects/<id>/git-status` - Get Git status
- `POST /api/projects/<id>/checkout` - Switch branch
- `POST /api/projects/<id>/pull` - Pull changes

## Notes

- Projects are stored in `projects.json` file
- The application verifies that project paths exist before adding them
- All Git operations are executed in the project's directory
