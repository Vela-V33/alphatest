#!/usr/bin/env python3
"""
AlphaTest - AI-Powered UAT Testing
Main server application
"""

import os
import json
import asyncio
import threading
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, session
from flask_socketio import SocketIO, emit
from functools import wraps
import yaml

# Import our modules
from crawler import AppCrawler
from agent import AlphaTestAgent
from report_generator import generate_report
import auth

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'alphatest-secret-key-2024-change-in-production')
# Allow CORS from environment variable or default to all in development
allowed_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '*')
socketio = SocketIO(app, cors_allowed_origins=allowed_origins, async_mode='threading')

# Data directories
DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = Path(__file__).parent / "reports"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Store active test sessions
active_sessions = {}

def load_projects():
    """Load all saved projects."""
    projects_file = DATA_DIR / "projects.json"
    if projects_file.exists():
        return json.loads(projects_file.read_text())
    return {}

def save_projects(projects):
    """Save projects to file."""
    projects_file = DATA_DIR / "projects.json"
    projects_file.write_text(json.dumps(projects, indent=2))

def load_config():
    """Load main config with API key."""
    config_file = Path(__file__).parent / "config.yaml"
    if config_file.exists():
        return yaml.safe_load(config_file.read_text())
    return {}

def save_config(config):
    """Save config to file."""
    config_file = Path(__file__).parent / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

def is_api_key_configured():
    """Check if a valid API key is configured."""
    config = load_config()
    api_key = config.get('anthropic_api_key', '')
    return api_key and 'YOUR-API-KEY' not in api_key and len(api_key) > 20

def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get the current logged-in user."""
    if 'user_id' in session:
        return auth.get_user_by_id(session['user_id'])
    return None

# ============================================
# AUTHENTICATION ROUTES
# ============================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """User signup page."""
    if request.method == 'POST':
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        name = data.get('name', '').strip()

        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password required'})

        if len(password) < 8:
            return jsonify({'success': False, 'error': 'Password must be at least 8 characters'})

        result = auth.create_user(email, password, name)

        if result['success']:
            # Auto-login after signup
            user = auth.get_user_by_email(email)
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']

        return jsonify(result)

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if request.method == 'POST':
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        user = auth.authenticate_user(email, password)

        if user:
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Invalid email or password'})

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout the current user."""
    session.clear()
    return redirect('/login')

@app.route('/api/user')
@login_required
def get_user():
    """Get current user info."""
    user = get_current_user()
    return jsonify(user)

@app.route('/api/generate-acceptance-criteria', methods=['POST'])
@login_required
def generate_acceptance_criteria():
    """Generate acceptance criteria for a test command."""
    data = request.json
    test_command = data.get('test_command', '')
    context = data.get('context', '')

    if not test_command:
        return jsonify({'success': False, 'error': 'Test command required'})

    config = load_config()
    api_key = config.get('anthropic_api_key')

    if not api_key:
        return jsonify({'success': False, 'error': 'API key not configured'})

    # Create a temporary agent to generate criteria
    def generate_criteria_sync():
        async def generate():
            agent = AlphaTestAgent(api_key=api_key)
            criteria = await agent.generate_acceptance_criteria(test_command, context)
            return criteria

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(generate())
        loop.close()
        return result

    try:
        criteria = generate_criteria_sync()
        return jsonify({'success': True, 'criteria': criteria})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# ROUTES
# ============================================

@app.route('/')
def home():
    """Landing page - always show for public access."""
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - redirects to setup if needed."""
    if not is_api_key_configured():
        return redirect('/setup')

    user = get_current_user()
    all_projects = load_projects()

    # Filter projects for current user
    user_projects = {k: v for k, v in all_projects.items() if v.get('owner_id') == user['id']}

    return render_template('dashboard.html', projects=user_projects, user=user)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """First-time setup wizard."""
    if request.method == 'POST':
        data = request.json
        api_key = data.get('api_key', '').strip()
        
        if not api_key or not api_key.startswith('sk-ant-'):
            return jsonify({'success': False, 'error': 'Invalid API key. It should start with sk-ant-'})
        
        # Load existing config and update
        config = load_config()
        config['anthropic_api_key'] = api_key
        
        # Ensure other defaults exist
        if 'model' not in config:
            config['model'] = 'claude-sonnet-4-20250514'
        
        save_config(config)
        
        return jsonify({'success': True})
    
    # Check if already configured
    if is_api_key_configured():
        return redirect('/')
    
    return render_template('setup.html')

@app.route('/project/new', methods=['GET', 'POST'])
@login_required
def new_project():
    """Create a new project."""
    if request.method == 'POST':
        try:
            data = request.get_json()

            if not data:
                return jsonify({'success': False, 'error': 'No data provided'}), 400

            if 'name' not in data or not data['name'].strip():
                return jsonify({'success': False, 'error': 'Project name is required'}), 400

            if 'url' not in data or not data['url'].strip():
                return jsonify({'success': False, 'error': 'Project URL is required'}), 400

            user = get_current_user()
            projects = load_projects()

            project_id = data['name'].lower().replace(' ', '-')
            # Add timestamp to ensure uniqueness
            import time
            project_id = f"{project_id}-{int(time.time())}"

            projects[project_id] = {
                'id': project_id,
                'name': data['name'].strip(),
                'url': data['url'].strip(),
                'login_url': data.get('login_url', '').strip(),
                'email': data.get('email', '').strip(),
                'password': data.get('password', '').strip(),
                'owner_id': user['id'],
                'owner_email': user['email'],
                'created_at': datetime.now().isoformat(),
                'crawl_data': None,
                'test_specs': [],
                'test_history': []
            }

            save_projects(projects)

            # Add project to user's project list
            auth.add_project_to_user(user['id'], project_id)

            return jsonify({'success': True, 'project_id': project_id})

        except Exception as e:
            print(f"Error creating project: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    user = get_current_user()
    return render_template('new_project.html', user=user)

@app.route('/project/<project_id>')
def view_project(project_id):
    """View a specific project."""
    projects = load_projects()
    project = projects.get(project_id)
    if not project:
        return "Project not found", 404
    return render_template('project.html', project=project)

@app.route('/project/<project_id>/delete', methods=['POST'])
def delete_project(project_id):
    """Delete a project."""
    projects = load_projects()
    if project_id in projects:
        del projects[project_id]
        save_projects(projects)
    return jsonify({'success': True})

@app.route('/project/<project_id>/update', methods=['POST'])
def update_project(project_id):
    """Update project settings."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'success': False, 'error': 'Project not found'}), 404
    
    data = request.json
    projects[project_id].update({
        'name': data.get('name', projects[project_id]['name']),
        'url': data.get('url', projects[project_id]['url']),
        'login_url': data.get('login_url', projects[project_id]['login_url']),
        'email': data.get('email', projects[project_id]['email']),
        'password': data.get('password', projects[project_id]['password']),
    })
    save_projects(projects)
    return jsonify({'success': True})

@app.route('/project/<project_id>/crawl')
def crawl_project(project_id):
    """Show crawl interface for a project."""
    projects = load_projects()
    project = projects.get(project_id)
    if not project:
        return "Project not found", 404
    return render_template('crawl.html', project=project)

@app.route('/project/<project_id>/test')
def test_project(project_id):
    """Show test interface for a project."""
    projects = load_projects()
    project = projects.get(project_id)
    if not project:
        return "Project not found", 404
    return render_template('test.html', project=project)

@app.route('/project/<project_id>/reports')
def project_reports(project_id):
    """Show test reports for a project."""
    projects = load_projects()
    project = projects.get(project_id)
    if not project:
        return "Project not found", 404
    
    # Get reports for this project
    project_reports_dir = REPORTS_DIR / project_id
    reports = []
    if project_reports_dir.exists():
        for report_dir in sorted(project_reports_dir.iterdir(), reverse=True):
            if report_dir.is_dir():
                report_file = report_dir / "report.json"
                if report_file.exists():
                    report_data = json.loads(report_file.read_text())
                    reports.append({
                        'id': report_dir.name,
                        'date': report_data.get('date', report_dir.name),
                        'summary': report_data.get('summary', {}),
                        'path': str(report_dir)
                    })
    
    return render_template('reports.html', project=project, reports=reports)

@app.route('/reports/<project_id>/<report_id>')
def view_report(project_id, report_id):
    """View a specific report."""
    report_dir = REPORTS_DIR / project_id / report_id
    report_file = report_dir / "report.html"
    if report_file.exists():
        return report_file.read_text()
    return "Report not found", 404

@app.route('/reports/<project_id>/<report_id>/screenshots/<filename>')
def report_screenshot(project_id, report_id, filename):
    """Serve report screenshots."""
    return send_from_directory(REPORTS_DIR / project_id / report_id / "screenshots", filename)

@app.route('/project/<project_id>/specs', methods=['GET', 'POST'])
def manage_specs(project_id):
    """Manage test specifications."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'success': False, 'error': 'Project not found'}), 404

    if request.method == 'POST':
        data = request.json
        projects[project_id]['test_specs'] = data.get('specs', [])
        save_projects(projects)
        return jsonify({'success': True})

    return jsonify({'specs': projects[project_id].get('test_specs', [])})


@app.route('/issues')
def issues_dashboard():
    """View all issues across projects."""
    projects = load_projects()

    # Collect all issues from all reports
    issues_by_project = {}
    total_issues = 0
    critical_count = 0
    high_count = 0
    medium_count = 0

    for project_id, project in projects.items():
        project_reports_dir = REPORTS_DIR / project_id
        project_issues = []

        if project_reports_dir.exists():
            for report_dir in sorted(project_reports_dir.iterdir(), reverse=True):
                if report_dir.is_dir():
                    report_file = report_dir / "report.json"
                    if report_file.exists():
                        report_data = json.loads(report_file.read_text())
                        for issue in report_data.get('issues', []):
                            issue['report_id'] = report_dir.name
                            issue['report_date'] = report_data.get('date', '')[:10]
                            project_issues.append(issue)

                            severity = issue.get('severity', 'medium')
                            if severity == 'critical':
                                critical_count += 1
                            elif severity == 'high':
                                high_count += 1
                            else:
                                medium_count += 1

        if project_issues:
            issues_by_project[project_id] = {
                'name': project['name'],
                'issues': project_issues
            }
            total_issues += len(project_issues)

    return render_template('issues.html',
        projects=projects,
        issues_by_project=issues_by_project,
        total_issues=total_issues,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count
    )


@app.route('/project/<project_id>/team', methods=['GET', 'POST', 'DELETE'])
def manage_team(project_id):
    """Manage team members for a project."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'success': False, 'error': 'Project not found'}), 404

    project = projects[project_id]

    # Initialize team array if not exists
    if 'team' not in project:
        project['team'] = []

    if request.method == 'POST':
        data = request.json
        email = data.get('email', '').strip().lower()
        role = data.get('role', 'viewer')

        if not email:
            return jsonify({'success': False, 'error': 'Email is required'}), 400

        # Check if already in team
        for member in project['team']:
            if member['email'] == email:
                return jsonify({'success': False, 'error': 'User already in team'}), 400

        # Add team member
        project['team'].append({
            'email': email,
            'role': role,
            'invited_at': datetime.now().isoformat()
        })
        save_projects(projects)

        return jsonify({'success': True, 'team': project['team']})

    elif request.method == 'DELETE':
        data = request.json
        email = data.get('email', '').strip().lower()

        project['team'] = [m for m in project['team'] if m['email'] != email]
        save_projects(projects)

        return jsonify({'success': True, 'team': project['team']})

    return jsonify({'team': project['team']})


# ============================================
# COLLABORATION DASHBOARD
# ============================================

@app.route('/project/<project_id>/collaboration')
@login_required
def collaboration_dashboard(project_id):
    """Collaboration dashboard with issue triage."""
    projects = load_projects()
    if project_id not in projects:
        return "Project not found", 404
    return render_template('collaboration.html', project_id=project_id)


@app.route('/api/project/<project_id>/collaborators')
@login_required
def get_collaborators(project_id):
    """Get project collaborators."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    project = projects[project_id]
    users_db = load_users()

    # Get owner info
    owner_id = project.get('owner_id', session.get('user_id'))
    owner = users_db.get(owner_id, {})

    collaborators = [{
        'id': owner_id,
        'name': owner.get('username', 'Owner'),
        'email': owner.get('email', ''),
        'avatar': owner.get('username', 'U')[:2].upper(),
        'role': 'owner'
    }]

    # Add team members
    for member in project.get('team', []):
        collaborators.append({
            'id': member.get('email'),
            'name': member.get('email', '').split('@')[0],
            'email': member.get('email', ''),
            'avatar': member.get('email', 'U')[:2].upper(),
            'role': member.get('role', 'viewer')
        })

    return jsonify({'collaborators': collaborators})


@app.route('/api/project/<project_id>/issues')
@login_required
def get_project_issues(project_id):
    """Get all issues for a project."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    project = projects[project_id]
    project_reports_dir = REPORTS_DIR / project_id
    all_issues = []

    if project_reports_dir.exists():
        # Get the most recent report
        report_dirs = sorted(project_reports_dir.iterdir(), reverse=True)
        if report_dirs:
            latest_report = report_dirs[0]
            report_file = latest_report / "report.json"

            if report_file.exists():
                report_data = json.loads(report_file.read_text())

                # Convert issues to the format expected by React
                for idx, issue in enumerate(report_data.get('issues', [])):
                    all_issues.append({
                        'id': f"{latest_report.name}_{idx}",
                        'title': issue.get('message', 'Unknown issue'),
                        'description': issue.get('message', ''),
                        'severity': issue.get('severity', 'medium'),
                        'category': categorize_issue(issue),
                        'screenshot': None,  # Will be populated if available
                        'step': issue.get('step', 0),
                        'timestamp': issue.get('timestamp', datetime.now().isoformat()),
                        'status': 'open'
                    })

    return jsonify({
        'issues': all_issues,
        'project_name': project.get('name', 'Unknown Project')
    })


def categorize_issue(issue):
    """Categorize issue based on type."""
    issue_type = issue.get('type', '').lower()
    message = issue.get('message', '').lower()

    # Security-related
    if any(keyword in message for keyword in ['security', 'xss', 'sql', 'injection', 'validation', 'authentication']):
        return 'security'

    # UI/UX-related
    if any(keyword in message for keyword in ['ui', 'ux', 'button', 'dropdown', 'click', 'display', 'layout', 'visual']):
        return 'ui-ux'

    # Logic-related
    return 'logic'


@app.route('/api/project/<project_id>/invite', methods=['POST'])
@login_required
def invite_collaborator(project_id):
    """Invite a collaborator to the project."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    data = request.json
    email = data.get('email', '').strip().lower()
    role = data.get('role', 'viewer')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    project = projects[project_id]

    if 'team' not in project:
        project['team'] = []

    # Check if already in team
    for member in project['team']:
        if member['email'] == email:
            return jsonify({'error': 'User already in team'}), 400

    # Add team member
    new_member = {
        'email': email,
        'role': role,
        'invited_at': datetime.now().isoformat()
    }
    project['team'].append(new_member)
    save_projects(projects)

    # Return collaborator in expected format
    return jsonify({
        'collaborator': {
            'id': email,
            'name': email.split('@')[0],
            'email': email,
            'avatar': email[:2].upper(),
            'role': role
        }
    })


@app.route('/api/project/<project_id>/export-issues', methods=['POST'])
@login_required
def export_issues_pdf(project_id):
    """Export issues to PDF."""
    # This would use a PDF generation library
    # For now, return a placeholder
    return jsonify({'error': 'PDF export not yet implemented'}), 501


@app.route('/api/project/<project_id>/save', methods=['POST'])
@login_required
def save_project_state(project_id):
    """Save project state."""
    # Project is automatically saved when issues are updated
    # This is a placeholder for future enhancements
    return jsonify({'success': True})


@app.route('/api/project/<project_id>/scan/accessibility', methods=['POST'])
@login_required
def run_accessibility_scan(project_id):
    """Run WCAG 2.1 accessibility scan on project URL."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    project = projects[project_id]
    config = load_config()

    async def scan_async():
        from agent import AlphaTestAgent
        agent = AlphaTestAgent(config.get('anthropic_api_key'))
        try:
            await agent.initialize()
            await agent.page.goto(project['url'], wait_until='networkidle')
            result = await agent.run_accessibility_scan()
            await agent.close()
            return result
        except Exception as e:
            await agent.close()
            return {'error': str(e)}

    # Run async scan
    import asyncio
    result = asyncio.run(scan_async())

    return jsonify(result)


@app.route('/api/project/<project_id>/scan/security', methods=['POST'])
@login_required
def run_security_scan(project_id):
    """Run security headers check on project URL."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    project = projects[project_id]
    config = load_config()

    async def scan_async():
        from agent import AlphaTestAgent
        agent = AlphaTestAgent(config.get('anthropic_api_key'))
        try:
            await agent.initialize()
            response = await agent.page.goto(project['url'], wait_until='networkidle')
            result = await agent.check_security_headers(response)
            await agent.close()
            return result
        except Exception as e:
            await agent.close()
            return {'error': str(e)}

    # Run async scan
    import asyncio
    result = asyncio.run(scan_async())

    return jsonify(result)


@app.route('/api/project/<project_id>/scan/performance', methods=['POST'])
@login_required
def run_performance_scan(project_id):
    """Run Lighthouse performance audit on project URL."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    project = projects[project_id]
    config = load_config()

    async def scan_async():
        from agent import AlphaTestAgent
        agent = AlphaTestAgent(config.get('anthropic_api_key'))
        try:
            await agent.initialize()
            await agent.page.goto(project['url'], wait_until='networkidle')
            result = await agent.run_lighthouse_audit()
            await agent.close()
            return result
        except Exception as e:
            await agent.close()
            return {'error': str(e)}

    # Run async scan
    import asyncio
    result = asyncio.run(scan_async())

    return jsonify(result)


@app.route('/api/project/<project_id>/scan/all', methods=['POST'])
@login_required
def run_all_scans(project_id):
    """Run all scans (accessibility, security, performance) on project URL."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    project = projects[project_id]
    config = load_config()

    async def scan_async():
        from agent import AlphaTestAgent
        agent = AlphaTestAgent(config.get('anthropic_api_key'))
        try:
            await agent.initialize()
            response = await agent.page.goto(project['url'], wait_until='networkidle')

            # Run all scans
            accessibility = await agent.run_accessibility_scan()
            security = await agent.check_security_headers(response)
            performance = await agent.run_lighthouse_audit()

            await agent.close()

            return {
                'accessibility': accessibility,
                'security': security,
                'performance': performance,
                'url': project['url'],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            await agent.close()
            return {'error': str(e)}

    # Run async scan
    import asyncio
    result = asyncio.run(scan_async())

    return jsonify(result)


# ============================================
# SOCKET.IO EVENTS
# ============================================

@socketio.on('connect')
def handle_connect():
    emit('status', {'message': 'Connected to AlphaTest'})

@socketio.on('start_crawl')
def handle_crawl(data):
    """Start crawling an app."""
    project_id = data.get('project_id')
    projects = load_projects()
    project = projects.get(project_id)
    
    if not project:
        emit('crawl_error', {'message': 'Project not found'})
        return
    
    config = load_config()
    
    def run_crawl():
        async def crawl_async():
            crawler = AppCrawler(
                config.get('anthropic_api_key'),
                lambda msg: socketio.emit('crawl_progress', {'message': msg})
            )
            
            try:
                result = await crawler.crawl(
                    url=project['url'],
                    login_url=project.get('login_url'),
                    email=project.get('email'),
                    password=project.get('password')
                )
                
                # Save crawl data
                projects = load_projects()
                projects[project_id]['crawl_data'] = result
                projects[project_id]['test_specs'] = result.get('suggested_tests', [])
                save_projects(projects)
                
                socketio.emit('crawl_complete', {'result': result})
                
            except Exception as e:
                socketio.emit('crawl_error', {'message': str(e)})
            finally:
                await crawler.close()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(crawl_async())
        loop.close()
    
    thread = threading.Thread(target=run_crawl)
    thread.start()

@socketio.on('run_test')
def handle_test(data):
    """Run a test command."""
    project_id = data.get('project_id')
    command = data.get('command')
    
    projects = load_projects()
    project = projects.get(project_id)
    
    if not project:
        emit('test_error', {'message': 'Project not found'})
        return
    
    config = load_config()
    session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_dir = REPORTS_DIR / project_id / session_id

    def run_test():
        async def test_async():
            agent = AlphaTestAgent(
                api_key=config.get('anthropic_api_key'),
                status_callback=lambda msg: socketio.emit('test_progress', {'message': msg}),
                screenshot_callback=lambda path: socketio.emit('test_screenshot', {'path': path})
            )

            try:
                await agent.initialize(session_dir=report_dir)
                
                # Navigate and login
                await agent.page.goto(project['url'], wait_until='networkidle')
                
                if project.get('email') and project.get('password'):
                    login_url = project.get('login_url') or project['url']
                    await agent.login(
                        login_url=login_url,
                        email=project['email'],
                        password=project['password']
                    )
                
                # Run the test
                result = await agent.run_command(command)

                # Generate report
                report_data = agent.get_report_data()
                report_path = generate_report(report_data, report_dir, project)

                socketio.emit('test_complete', {
                    'result': result,
                    'status': result.get('status', 'completed'),
                    'report_url': f'/reports/{project_id}/{session_id}'
                })

            except Exception as e:
                import traceback
                error_msg = str(e)
                print(f"Test error: {error_msg}")
                print(traceback.format_exc())
                socketio.emit('test_error', {'message': error_msg})
            finally:
                await agent.close()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(test_async())
        loop.close()
    
    thread = threading.Thread(target=run_test)
    thread.start()

@socketio.on('run_spec')
def handle_run_spec(data):
    """Run a full test specification."""
    project_id = data.get('project_id')
    spec_ids = data.get('spec_ids', [])  # List of spec IDs to run
    
    projects = load_projects()
    project = projects.get(project_id)
    
    if not project:
        emit('test_error', {'message': 'Project not found'})
        return
    
    config = load_config()
    session_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_dir = REPORTS_DIR / project_id / session_id

    # Get specs to run
    all_specs = project.get('test_specs', [])
    if spec_ids:
        specs_to_run = [s for s in all_specs if s.get('id') in spec_ids]
    else:
        specs_to_run = [s for s in all_specs if s.get('enabled', True)]

    def run_specs():
        async def specs_async():
            agent = AlphaTestAgent(
                api_key=config.get('anthropic_api_key'),
                status_callback=lambda msg: socketio.emit('test_progress', {'message': msg}),
                screenshot_callback=lambda path: socketio.emit('test_screenshot', {'path': path})
            )

            try:
                await agent.initialize(session_dir=report_dir)
                
                # Navigate and login
                await agent.page.goto(project['url'], wait_until='networkidle')
                
                if project.get('email') and project.get('password'):
                    login_url = project.get('login_url') or project['url']
                    await agent.login(
                        login_url=login_url,
                        email=project['email'],
                        password=project['password']
                    )
                
                # Run each spec
                results = []
                for spec in specs_to_run:
                    socketio.emit('spec_start', {'spec': spec})
                    result = await agent.run_command(spec['description'])
                    result['spec_name'] = spec['name']
                    results.append(result)
                    socketio.emit('spec_complete', {'spec': spec, 'result': result})

                # Generate report
                report_data = agent.get_report_data()
                report_data['specs_results'] = results
                report_path = generate_report(report_data, report_dir, project)
                
                socketio.emit('all_specs_complete', {
                    'results': results,
                    'report_url': f'/reports/{project_id}/{session_id}'
                })

            except Exception as e:
                import traceback
                error_msg = str(e)
                print(f"Spec test error: {error_msg}")
                print(traceback.format_exc())
                socketio.emit('test_error', {'message': error_msg})
            finally:
                await agent.close()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(specs_async())
        loop.close()
    
    thread = threading.Thread(target=run_specs)
    thread.start()

# ============================================
# MAIN
# ============================================

def main():
    import webbrowser

    # Get port from environment variable (for cloud deployment) or default to 8080
    port = int(os.environ.get('PORT', 8080))
    is_production = os.environ.get('ENV') == 'production'

    print("")
    print("=" * 50)
    print("  🧪 AlphaTest - AI-Powered UAT Testing")
    print("=" * 50)
    print("")

    if not is_production:
        print("  Opening in your browser...")
        print(f"  URL: http://127.0.0.1:{port}")
        print("")
        print("  Press Ctrl+C to stop")
        print("=" * 50)
        print("")

        # Open browser after a short delay (only in local mode)
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f'http://127.0.0.1:{port}')

        threading.Thread(target=open_browser, daemon=True).start()
    else:
        print(f"  Starting in production mode on port {port}")
        print("=" * 50)
        print("")

    # Run server
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()
