const API_BASE = 'http://localhost:5000/api';

let currentProjectId = null;
let projects = [];

// Load projects on page load
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
});

// Load all projects
async function loadProjects() {
    try {
        const response = await fetch(`${API_BASE}/projects`);
        projects = await response.json();
        renderProjects();
    } catch (error) {
        console.error('Error loading projects:', error);
        showNotification('Failed to load projects', 'error');
    }
}

// Render projects as cards
function renderProjects() {
    const container = document.getElementById('projects-container');
    
    if (projects.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: white; font-size: 1.2rem; grid-column: 1 / -1;">No projects added yet. Click "Add Project" to get started!</p>';
        return;
    }
    
    container.innerHTML = projects.map((project, index) => `
        <div class="project-card" onclick="openProjectActions(${index})">
            <div class="project-menu" onclick="event.stopPropagation(); showProjectMenu(${index}, event)">⋯</div>
            <div class="project-icon">📁</div>
            <div class="project-name">${escapeHtml(project.name)}</div>
            <div class="project-path">${escapeHtml(project.path)}</div>
        </div>
    `).join('');
}

// Show project menu (delete option)
function showProjectMenu(projectId, event) {
    event.stopPropagation();
    
    // Remove existing menu if any
    const existingMenu = document.querySelector('.project-menu-dropdown');
    if (existingMenu) {
        existingMenu.remove();
        return;
    }
    
    // Get project data
    const project = projects[projectId];
    const hasGitRemote = project.git_remote_url && project.git_remote_url.trim() !== '';
    
    // Determine the Git hosting platform for display
    let gitPlatformName = 'Git';
    if (project.git_remote_url) {
        if (project.git_remote_url.includes('github.com')) {
            gitPlatformName = 'GitHub';
        } else if (project.git_remote_url.includes('gitlab.com') || project.git_remote_url.includes('gitlab')) {
            gitPlatformName = 'GitLab';
        } else if (project.git_remote_url.includes('bitbucket.org')) {
            gitPlatformName = 'Bitbucket';
        }
    }
    
    // Create menu dropdown
    const menu = document.createElement('div');
    menu.className = 'project-menu-dropdown';
    menu.innerHTML = `
        <div class="menu-item" onclick="openCursor(${projectId})">
            <span>💻</span>
            <span>Open Cursor</span>
        </div>
        ${hasGitRemote ? `
        <div class="menu-item" onclick="openGitRepository(${projectId})">
            <span>🔗</span>
            <span>Open on ${gitPlatformName}</span>
        </div>
        ` : ''}
        <div class="menu-item" onclick="deleteProject(${projectId})">
            <span>🗑️</span>
            <span>Delete</span>
        </div>
    `;
    
    // Position menu
    const card = event.target.closest('.project-card');
    const rect = card.getBoundingClientRect();
    menu.style.top = (rect.top + 40) + 'px';
    menu.style.left = (rect.right - 120) + 'px';
    
    document.body.appendChild(menu);
    
    // Close menu when clicking outside
    setTimeout(() => {
        const closeMenu = (e) => {
            if (!menu.contains(e.target) && !card.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        };
        document.addEventListener('click', closeMenu);
    }, 10);
}

// Open Git repository in browser (GitHub, GitLab, Bitbucket, etc.)
function openGitRepository(projectId) {
    // Remove menu if open
    const menu = document.querySelector('.project-menu-dropdown');
    if (menu) menu.remove();
    
    const project = projects[projectId];
    
    if (project && project.git_remote_url) {
        // Open Git repository URL in browser
        window.open(project.git_remote_url, '_blank');
        
        // Determine platform for notification
        let platformName = 'repository';
        if (project.git_remote_url.includes('github.com')) {
            platformName = 'GitHub';
        } else if (project.git_remote_url.includes('gitlab.com') || project.git_remote_url.includes('gitlab')) {
            platformName = 'GitLab';
        } else if (project.git_remote_url.includes('bitbucket.org')) {
            platformName = 'Bitbucket';
        }
        
        showNotification(`Opening ${platformName}...`, 'success');
    } else {
        showNotification('Git repository URL not found for this project', 'error');
    }
}

// Open Cursor at project path
async function openCursor(projectId) {
    // Remove menu if open
    const menu = document.querySelector('.project-menu-dropdown');
    if (menu) menu.remove();
    
    try {
        const response = await fetch(`${API_BASE}/projects/${projectId}/open-cursor`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Opening Cursor...', 'success');
        } else {
            showNotification(data.error || 'Failed to open Cursor', 'error');
        }
    } catch (error) {
        console.error('Error opening Cursor:', error);
        showNotification('Failed to open Cursor', 'error');
    }
}

// Delete project
async function deleteProject(projectId) {
    // Remove menu if open
    const menu = document.querySelector('.project-menu-dropdown');
    if (menu) menu.remove();
    
    try {
        const response = await fetch(`${API_BASE}/projects/${projectId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            showNotification(error.error || 'Failed to delete project', 'error');
            return;
        }
        
        showNotification('Project deleted successfully', 'success');
        loadProjects();
    } catch (error) {
        console.error('Error deleting project:', error);
        showNotification('Failed to delete project', 'error');
    }
}

// Show add project modal
function showAddProjectModal() {
    document.getElementById('addProjectModal').style.display = 'block';
    document.getElementById('projectPath').value = '';
}

// Close add project modal
function closeAddProjectModal() {
    document.getElementById('addProjectModal').style.display = 'none';
}

// Add new project
async function addProject(event) {
    event.preventDefault();
    const path = document.getElementById('projectPath').value.trim();
    
    if (!path) {
        showNotification('Please enter a project path', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/projects`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ path })
        });
        
        if (!response.ok) {
            const error = await response.json();
            showNotification(error.error || 'Failed to add project', 'error');
            return;
        }
        
        closeAddProjectModal();
        showNotification('Project added successfully', 'success');
        loadProjects();
    } catch (error) {
        console.error('Error adding project:', error);
        showNotification('Failed to add project', 'error');
    }
}

// Open project actions modal
function openProjectActions(projectId) {
    currentProjectId = projectId;
    const project = projects[projectId];
    document.getElementById('projectNameTitle').textContent = project.name;
    document.getElementById('actionsModal').style.display = 'block';
    document.getElementById('gitOutput').classList.remove('show', 'success', 'error');
    document.getElementById('gitOutput').textContent = '';
}

// Close actions modal
function closeActionsModal() {
    document.getElementById('actionsModal').style.display = 'none';
    currentProjectId = null;
}

// Show git status
async function showGitStatus() {
    if (currentProjectId === null) return;
    
    const output = document.getElementById('gitOutput');
    output.textContent = 'Loading...';
    output.classList.add('show');
    output.classList.remove('success', 'error');
    
    try {
        const response = await fetch(`${API_BASE}/projects/${currentProjectId}/git-status`);
        const data = await response.json();
        
        if (response.ok) {
            output.textContent = `Current Branch: ${data.branch}\n\n${data.status}`;
            output.classList.add('success');
        } else {
            output.textContent = `Error: ${data.error || 'Failed to get git status'}`;
            output.classList.add('error');
        }
    } catch (error) {
        output.textContent = `Error: ${error.message}`;
        output.classList.add('error');
    }
}

// Show checkout modal
function showCheckoutModal() {
    document.getElementById('checkoutModal').style.display = 'block';
    document.getElementById('branchName').value = '';
}

// Close checkout modal
function closeCheckoutModal() {
    document.getElementById('checkoutModal').style.display = 'none';
}

// Checkout branch
async function checkoutBranch(event) {
    event.preventDefault();
    const branchName = document.getElementById('branchName').value.trim();
    
    if (!branchName) {
        showNotification('Please enter a branch name', 'error');
        return;
    }
    
    if (currentProjectId === null) return;
    
    const output = document.getElementById('gitOutput');
    output.textContent = 'Switching branch...';
    output.classList.add('show');
    output.classList.remove('success', 'error');
    
    closeCheckoutModal();
    
    try {
        const response = await fetch(`${API_BASE}/projects/${currentProjectId}/checkout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ branch: branchName })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            output.textContent = `${data.message}\n\n${data.output || ''}`;
            output.classList.add('success');
        } else {
            output.textContent = `Error: ${data.error || data.message || 'Failed to switch branch'}`;
            output.classList.add('error');
        }
    } catch (error) {
        output.textContent = `Error: ${error.message}`;
        output.classList.add('error');
    }
}

// Git pull
async function gitPull() {
    if (currentProjectId === null) return;
    
    const output = document.getElementById('gitOutput');
    output.textContent = 'Pulling changes...';
    output.classList.add('show');
    output.classList.remove('success', 'error');
    
    try {
        const response = await fetch(`${API_BASE}/projects/${currentProjectId}/pull`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            output.textContent = `${data.message}\n\n${data.output || ''}`;
            output.classList.add('success');
        } else {
            output.textContent = `Error: ${data.error || data.message || 'Failed to pull changes'}`;
            output.classList.add('error');
        }
    } catch (error) {
        output.textContent = `Error: ${error.message}`;
        output.classList.add('error');
    }
}

// Close modals when clicking outside
window.onclick = function(event) {
    const modals = document.getElementsByClassName('modal');
    for (let modal of modals) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    }
}


// Show custom notification
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Open Odoo config file in Cursor
async function openOdooConfig() {
    try {
        const response = await fetch(`${API_BASE}/open-odoo-config`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Opening Odoo config in Cursor...', 'success');
        } else {
            showNotification(data.error || 'Failed to open Odoo config', 'error');
        }
    } catch (error) {
        console.error('Error opening Odoo config:', error);
        showNotification('Failed to open Odoo config', 'error');
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
