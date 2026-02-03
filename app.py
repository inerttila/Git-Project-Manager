from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
import subprocess
import platform
from pathlib import Path

# Get creation flags for Windows
if platform.system() == 'Windows':
    CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
    CREATE_NEW_CONSOLE = 0x00000010  # New console window for terminal
else:
    CREATE_NO_WINDOW = 0
    CREATE_NEW_CONSOLE = 0

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
CORS(app)

# File to store projects
PROJECTS_FILE = 'projects.json'
SETTINGS_FILE = 'settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def load_projects():
    if os.path.exists(PROJECTS_FILE):
        with open(PROJECTS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_projects(projects):
    with open(PROJECTS_FILE, 'w') as f:
        json.dump(projects, f, indent=2)

def get_project_name(path):
    return os.path.basename(path.rstrip('/\\'))

def get_git_remote_url(project_path):
    if not os.path.exists(project_path):
        return None
    
    try:
        # Get git remote URL (hide console window on Windows)
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            # Try without 'origin', get first remote
            result = subprocess.run(
                ['git', 'remote', '-v'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW
            )
            if result.returncode == 0 and result.stdout:
                # Extract URL from first line
                lines = result.stdout.strip().split('\n')
                if lines:
                    # Format: "origin  https://gitlab.com/user/repo.git (fetch)"
                    parts = lines[0].split()
                    if len(parts) >= 2:
                        remote_url = parts[1]
                    else:
                        return None
                else:
                    return None
            else:
                return None
        else:
            remote_url = result.stdout.strip()
        
        # Convert SSH URL to HTTPS if needed, and ensure it's a web URL
        if remote_url.startswith('git@'):
            # Convert SSH to HTTPS: git@gitlab.com:user/repo.git -> https://gitlab.com/user/repo
            remote_url = remote_url.replace('git@', 'https://').replace(':', '/')
            if remote_url.endswith('.git'):
                remote_url = remote_url[:-4]
        elif remote_url.startswith('http'):
            # Already HTTPS/HTTP, just remove .git if present
            if remote_url.endswith('.git'):
                remote_url = remote_url[:-4]
        else:
            return None
        
        return remote_url
        
    except (subprocess.TimeoutExpired, Exception):
        return None

@app.route('/')
def index():
    """Serve the main HTML file"""
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/api/projects', methods=['GET'])
def get_projects():
    projects = load_projects()
    # Verify projects still exist and get their names
    valid_projects = []
    updated = False
    
    for project in projects:
        if os.path.exists(project['path']):
            project_data = {
                'path': project['path'],
                'name': get_project_name(project['path'])
            }
            
            # Only use existing git_remote_url if it exists, don't fetch again
            if 'git_remote_url' in project:
                project_data['git_remote_url'] = project['git_remote_url']
            
            valid_projects.append(project_data)
        else:
            # Project path doesn't exist, mark for removal
            updated = True
    
    # Save updated projects if any were removed
    if updated:
        save_projects(valid_projects)
    
    return jsonify(valid_projects)

@app.route('/api/projects', methods=['POST'])
def add_project():
    data = request.json
    path = data.get('path', '').strip()
    
    if not path:
        return jsonify({'error': 'Path is required'}), 400
    
    # Normalize path
    path = os.path.normpath(path)
    
    if not os.path.exists(path):
        return jsonify({'error': 'Path does not exist'}), 400
    
    if not os.path.isdir(path):
        return jsonify({'error': 'Path must be a directory'}), 400
    
    projects = load_projects()
    
    # Check if project already exists
    if any(p['path'] == path for p in projects):
        return jsonify({'error': 'Project already exists'}), 400
    
    # Get git remote URL when adding project
    git_remote_url = get_git_remote_url(path)
    
    project_data = {'path': path}
    if git_remote_url:
        project_data['git_remote_url'] = git_remote_url
    
    projects.append(project_data)
    save_projects(projects)
    
    response_data = {
        'path': path,
        'name': get_project_name(path)
    }
    if git_remote_url:
        response_data['git_remote_url'] = git_remote_url
    
    return jsonify(response_data), 201

@app.route('/api/projects/clone', methods=['POST'])
def clone_project():
    data = request.json
    clone_path = data.get('clone_path', '').strip()
    repository_url = data.get('repository_url', '').strip()
    
    if not clone_path:
        return jsonify({'error': 'Clone path is required'}), 400
    
    if not repository_url:
        return jsonify({'error': 'Repository URL is required'}), 400
    
    # Normalize path
    clone_path = os.path.normpath(clone_path)
    
    if not os.path.exists(clone_path):
        return jsonify({'error': 'Clone path does not exist'}), 400
    
    if not os.path.isdir(clone_path):
        return jsonify({'error': 'Clone path must be a directory'}), 400
    
    # Extract repository name from URL
    repo_name = repository_url.rstrip('/').split('/')[-1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    # Full path where the repository will be cloned
    project_path = os.path.join(clone_path, repo_name)
    
    # Check if project already exists
    projects = load_projects()
    if any(p['path'] == project_path for p in projects):
        return jsonify({'error': 'Project already exists'}), 400
    
    # Check if directory already exists
    if os.path.exists(project_path):
        return jsonify({'error': f'Directory {project_path} already exists'}), 400
    
    try:
        # Clone the repository
        result = subprocess.run(
            ['git', 'clone', repository_url, project_path],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
            creationflags=CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Failed to clone repository',
                'message': result.stderr
            }), 400
        
        # Get git remote URL (should be the same as what we cloned)
        git_remote_url = get_git_remote_url(project_path)
        
        # Add project to list
        project_data = {'path': project_path}
        if git_remote_url:
            project_data['git_remote_url'] = git_remote_url
        
        projects.append(project_data)
        save_projects(projects)
        
        response_data = {
            'path': project_path,
            'name': get_project_name(project_path)
        }
        if git_remote_url:
            response_data['git_remote_url'] = git_remote_url
        
        return jsonify(response_data), 201
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Clone operation timed out'}), 500
    except Exception as e:
        return jsonify({'error': f'Error cloning repository: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    projects = load_projects()
    
    if project_id < 0 or project_id >= len(projects):
        return jsonify({'error': 'Project not found'}), 404
    
    projects.pop(project_id)
    save_projects(projects)
    
    return jsonify({'message': 'Project deleted'}), 200

@app.route('/api/projects/reorder', methods=['POST'])
def reorder_projects():
    data = request.json or {}
    ordered_paths = data.get('ordered_paths', [])

    if not isinstance(ordered_paths, list) or not all(isinstance(p, str) for p in ordered_paths):
        return jsonify({'error': 'ordered_paths must be a list of strings'}), 400

    projects = load_projects()

    # Build lookup by path for stable ordering
    by_path = {p.get('path'): p for p in projects if isinstance(p, dict) and p.get('path')}

    reordered = []
    seen = set()

    # Add in requested order (only if path exists in current projects)
    for path in ordered_paths:
        proj = by_path.get(path)
        if proj and path not in seen:
            reordered.append(proj)
            seen.add(path)

    # Append any projects not included (e.g., new ones) to keep them from disappearing
    for proj in projects:
        path = proj.get('path') if isinstance(proj, dict) else None
        if path and path not in seen:
            reordered.append(proj)
            seen.add(path)

    save_projects(reordered)
    return jsonify({'message': 'Projects reordered'}), 200

@app.route('/api/projects/<int:project_id>/git-status', methods=['GET'])
def git_status(project_id):
    projects = load_projects()
    
    if project_id < 0 or project_id >= len(projects):
        return jsonify({'error': 'Project not found'}), 404
    
    project_path = projects[project_id]['path']
    
    if not os.path.exists(project_path):
        return jsonify({'error': 'Project path does not exist'}), 404
    
    try:
        # Get current branch
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        current_branch = result.stdout.strip() if result.returncode == 0 else 'Not a git repository'
        
        # Get git status
        status_result = subprocess.run(
            ['git', 'status'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        status_output = status_result.stdout if status_result.returncode == 0 else 'Not a git repository'
        
        return jsonify({
            'branch': current_branch,
            'status': status_output
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Git command timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/checkout', methods=['POST'])
def git_checkout(project_id):
    projects = load_projects()
    
    if project_id < 0 or project_id >= len(projects):
        return jsonify({'error': 'Project not found'}), 404
    
    data = request.json
    branch_name = data.get('branch', '').strip()
    
    if not branch_name:
        return jsonify({'error': 'Branch name is required'}), 400
    
    project_path = projects[project_id]['path']
    
    if not os.path.exists(project_path):
        return jsonify({'error': 'Project path does not exist'}), 404
    
    try:
        result = subprocess.run(
            ['git', 'checkout', branch_name],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Failed to checkout branch',
                'message': result.stderr
            }), 400
        
        return jsonify({
            'message': f'Switched to branch: {branch_name}',
            'output': result.stdout
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Git command timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/pull', methods=['POST'])
def git_pull(project_id):
    projects = load_projects()
    
    if project_id < 0 or project_id >= len(projects):
        return jsonify({'error': 'Project not found'}), 404
    
    project_path = projects[project_id]['path']
    
    if not os.path.exists(project_path):
        return jsonify({'error': 'Project path does not exist'}), 404
    
    try:
        result = subprocess.run(
            ['git', 'pull'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            return jsonify({
                'error': 'Failed to pull changes',
                'message': result.stderr
            }), 400
        
        return jsonify({
            'message': 'Successfully pulled changes',
            'output': result.stdout
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Git command timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/git-remote', methods=['GET'])
def get_git_remote(project_id):
    projects = load_projects()
    
    if project_id < 0 or project_id >= len(projects):
        return jsonify({'error': 'Project not found'}), 404
    
    project_path = projects[project_id]['path']
    
    if not os.path.exists(project_path):
        return jsonify({'error': 'Project path does not exist'}), 404
    
    try:
        # Get git remote URL
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            # Try without 'origin', get first remote
            result = subprocess.run(
                ['git', 'remote', '-v'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW
            )
            if result.returncode == 0 and result.stdout:
                # Extract URL from first line
                lines = result.stdout.strip().split('\n')
                if lines:
                    # Format: "origin  https://gitlab.com/user/repo.git (fetch)"
                    parts = lines[0].split()
                    if len(parts) >= 2:
                        remote_url = parts[1]
                    else:
                        return jsonify({'error': 'No git remote found'}), 404
                else:
                    return jsonify({'error': 'No git remote found'}), 404
            else:
                return jsonify({'error': 'Not a git repository or no remote configured'}), 404
        else:
            remote_url = result.stdout.strip()
        
        # Convert SSH URL to HTTPS if needed, and ensure it's a web URL
        if remote_url.startswith('git@'):
            # Convert SSH to HTTPS: git@gitlab.com:user/repo.git -> https://gitlab.com/user/repo
            remote_url = remote_url.replace('git@', 'https://').replace(':', '/')
            if remote_url.endswith('.git'):
                remote_url = remote_url[:-4]
        elif remote_url.startswith('http'):
            # Already HTTPS/HTTP, just remove .git if present
            if remote_url.endswith('.git'):
                remote_url = remote_url[:-4]
        else:
            return jsonify({'error': 'Unknown remote URL format'}), 400
        
        return jsonify({
            'remote_url': remote_url,
            'original_url': result.stdout.strip() if 'result' in locals() else remote_url
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Git command timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<int:project_id>/open-terminal', methods=['POST'])
def open_terminal(project_id):
    projects = load_projects()
    if project_id < 0 or project_id >= len(projects):
        return jsonify({'error': 'Project not found'}), 404
    project_path = projects[project_id]['path']
    if not os.path.exists(project_path):
        return jsonify({'error': 'Project path does not exist'}), 404
    try:
        if platform.system() == 'Windows':
            # Prefer PowerShell 7 (pwsh) over Windows PowerShell (powershell)
            path_escaped = project_path.replace("'", "''")
            cmd = [
                None, '-NoExit', '-Command',
                "Set-Location -LiteralPath '%s'" % path_escaped
            ]
            for exe in ('pwsh', 'pwsh.exe', 'powershell', 'powershell.exe'):
                try:
                    cmd[0] = exe
                    subprocess.Popen(cmd, creationflags=CREATE_NEW_CONSOLE)
                    break
                except FileNotFoundError:
                    continue
            else:
                return jsonify({'error': 'PowerShell not found (tried pwsh, powershell)'}), 400
        else:
            # macOS: Terminal.app with open -a Terminal and run script to cd
            # Linux: try xterm, gnome-terminal, or xdg-open
            if platform.system() == 'Darwin':
                script = 'tell application "Terminal" to do script "cd \'%s\' && exec $SHELL"' % project_path.replace("'", "'\\''")
                subprocess.Popen(['osascript', '-e', script])
            else:
                for term in ['gnome-terminal', 'xterm', 'konsole']:
                    try:
                        subprocess.Popen([term, '--working-directory', project_path])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    return jsonify({'error': 'No terminal found (tried gnome-terminal, xterm, konsole)'}), 400
        return jsonify({'message': 'Terminal opened', 'path': project_path}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/projects/<int:project_id>/open-cursor', methods=['POST'])
def open_cursor(project_id):
    projects = load_projects()
    
    if project_id < 0 or project_id >= len(projects):
        return jsonify({'error': 'Project not found'}), 404
    
    project_path = projects[project_id]['path']
    
    if not os.path.exists(project_path):
        return jsonify({'error': 'Project path does not exist'}), 404
    
    try:
        # Try to open Cursor - common commands for different OS
        import platform
        system = platform.system()
        
        if system == 'Windows':
            # Try different ways to open Cursor on Windows
            # Use Popen with shell=True for better Windows compatibility
            try:
                # Try cursor command first
                subprocess.Popen(
                    ['cursor', project_path],
                    cwd=project_path,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return jsonify({
                    'message': f'Opening Cursor at {project_path}',
                    'command': 'cursor'
                })
            except FileNotFoundError:
                # Try VS Code as fallback
                try:
                    subprocess.Popen(
                        ['code', project_path],
                        cwd=project_path,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    return jsonify({
                        'message': f'Opening VS Code at {project_path} (Cursor not found)',
                        'command': 'code'
                    })
                except FileNotFoundError:
                    return jsonify({
                        'error': 'Could not find Cursor or VS Code. Make sure Cursor is installed and added to PATH.'
                    }), 400
            except Exception as e:
                return jsonify({'error': f'Error opening Cursor: {str(e)}'}), 500
        elif system == 'Darwin':  # macOS
            commands = [
                ['cursor', project_path],
                ['open', '-a', 'Cursor', project_path],
            ]
        else:  # Linux
            commands = [
                ['cursor', project_path],
                ['code', project_path],  # Fallback
            ]
        
        # Try each command until one works
        last_error = None
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=False,
                    creationflags=CREATE_NO_WINDOW
                )
                # If we get here, command executed (even if it failed)
                return jsonify({
                    'message': f'Opening Cursor at {project_path}',
                    'command': ' '.join(cmd)
                })
            except FileNotFoundError:
                last_error = f'Command not found: {cmd[0]}'
                continue
            except subprocess.TimeoutExpired:
                # Command is running, that's good
                return jsonify({
                    'message': f'Opening Cursor at {project_path}',
                    'command': ' '.join(cmd)
                })
            except Exception as e:
                last_error = str(e)
                continue
        
        # If all commands failed
        return jsonify({
            'error': f'Could not open Cursor. Make sure Cursor is installed and in your PATH. Last error: {last_error}'
        }), 400
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/open-odoo-config', methods=['POST'])
def open_odoo_config():
    settings = load_settings()
    odoo_config_path = settings.get('odoo_config_path')

    if not odoo_config_path:
        return jsonify({'error': 'Odoo config path not set'}), 400
    
    if not os.path.exists(odoo_config_path):
        return jsonify({'error': 'Odoo config file not found at the specified path'}), 404
    
    try:
        import platform
        system = platform.system()
        
        if system == 'Windows':
            # Try to open the file in Cursor
            try:
                subprocess.Popen(
                    ['cursor', odoo_config_path],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return jsonify({
                    'message': f'Opening Odoo config in Cursor: {odoo_config_path}',
                    'command': 'cursor'
                })
            except FileNotFoundError:
                # Try VS Code as fallback
                try:
                    subprocess.Popen(
                        ['code', odoo_config_path],
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    return jsonify({
                        'message': f'Opening Odoo config in VS Code: {odoo_config_path}',
                        'command': 'code'
                    })
                except FileNotFoundError:
                    return jsonify({
                        'error': 'Could not find Cursor or VS Code. Make sure Cursor is installed and added to PATH.'
                    }), 400
            except Exception as e:
                return jsonify({'error': f'Error opening file: {str(e)}'}), 500
        else:
            # For macOS and Linux
            try:
                subprocess.Popen(
                    ['cursor', odoo_config_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return jsonify({
                    'message': f'Opening Odoo config in Cursor: {odoo_config_path}',
                    'command': 'cursor'
                })
            except FileNotFoundError:
                return jsonify({
                    'error': 'Could not find Cursor. Make sure Cursor is installed and added to PATH.'
                }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/odoo-config-path', methods=['GET'])
def get_odoo_config_path():
    settings = load_settings()
    return jsonify({'odoo_config_path': settings.get('odoo_config_path')}), 200

@app.route('/api/settings/odoo-config-path', methods=['POST'])
def set_odoo_config_path():
    data = request.json or {}
    path = data.get('odoo_config_path', '').strip()

    if not path:
        return jsonify({'error': 'odoo_config_path is required'}), 400

    # Normalize path (Windows-friendly)
    path = os.path.normpath(path)

    if not os.path.exists(path):
        return jsonify({'error': 'Odoo config file not found at the specified path'}), 404

    settings = load_settings()
    settings['odoo_config_path'] = path
    save_settings(settings)

    return jsonify({'message': 'Odoo config path saved', 'odoo_config_path': path}), 200

@app.route('/api/path/resolve', methods=['POST'])
def resolve_path():
    data = request.json
    folder_name = data.get('folder_name', '').strip()
    search_paths = data.get('search_paths', [])
    
    if not folder_name:
        return jsonify({'error': 'Folder name is required'}), 400
    
    found_paths = []
    
    # Default search locations if none provided
    if not search_paths:
        # Common Windows locations
        user_home = os.path.expanduser('~')
        search_paths = [
            user_home,
            os.path.join(user_home, 'Desktop'),
            os.path.join(user_home, 'Documents'),
            os.path.join(user_home, 'Downloads'),
            'C:\\',
            'D:\\',
        ]
    
    def search_directory(dir_path, max_depth=2, current_depth=0):
        if current_depth >= max_depth or len(found_paths) >= 10:
            return
        
        try:
            if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
                return
            
            # Check current directory first
            target_path = os.path.join(dir_path, folder_name)
            if os.path.exists(target_path) and os.path.isdir(target_path):
                found_paths.append(target_path)
                if len(found_paths) >= 10:
                    return
            
            # Only search subdirectories if we haven't found enough
            if current_depth < max_depth - 1:
                try:
                    items = os.listdir(dir_path)
                    for item in items:
                        if len(found_paths) >= 10:
                            break
                        item_path = os.path.join(dir_path, item)
                        try:
                            if os.path.isdir(item_path) and not item.startswith('.'):
                                search_directory(item_path, max_depth, current_depth + 1)
                        except (PermissionError, OSError):
                            continue
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError):
            pass
    
    # Search in provided paths (limit depth to avoid slow searches)
    for search_path in search_paths:
        if os.path.exists(search_path):
            search_directory(search_path, max_depth=2)
            if len(found_paths) >= 10:  # Limit results
                break
    
    return jsonify({
        'folder_name': folder_name,
        'found_paths': found_paths[:10]  # Return max 10 results
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
