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
from issue_tracker import IssueTracker
from screenshot_generator import ScreenshotGenerator, generate_ai_description
import auth

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'alphatest-secret-key-2024-change-in-production')
# Allow CORS from environment variable or default to all in development
allowed_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '*')
socketio = SocketIO(app, cors_allowed_origins=allowed_origins, async_mode='threading')

# Data directories
DATA_DIR = Path(__file__).parent / "data"
REPORTS_DIR = Path(__file__).parent / "reports"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"
DATA_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Store active test sessions and screenshot jobs
active_sessions = {}
active_screenshot_jobs = {}

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
        'browser_type': data.get('browser_type', projects[project_id].get('browser_type', 'chromium')),
        'slack_webhook_url': data.get('slack_webhook_url', projects[project_id].get('slack_webhook_url', '')),
        'slack_notifications_enabled': data.get('slack_notifications_enabled', projects[project_id].get('slack_notifications_enabled', False)),
        'slack_notify_on': data.get('slack_notify_on', projects[project_id].get('slack_notify_on', 'failures')),  # all, failures, or daily
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

@app.route('/project/<project_id>/screenshots/discover', methods=['POST'])
@login_required
def discover_pages(project_id):
    """Discover pages using AI agent - same as Run Test."""
    projects = load_projects()
    project = projects.get(project_id)
    if not project:
        return jsonify({'success': False, 'error': 'Project not found'}), 404

    async def discover_async():
        from agent import AlphaTestAgent

        discovered_pages = []

        print(f"\n" + "="*80)
        print(f"[DISCOVERY] AI-POWERED PAGE DISCOVERY")
        print(f"[DISCOVERY] Project: {project.get('name', 'Unknown')}")
        print(f"[DISCOVERY] URL: {project['url']}")
        print(f"[DISCOVERY] Using AlphaTestAgent (proven to work)")
        print(f"="*80 + "\n")

        config = load_config()
        api_key = config.get('anthropic_api_key')

        if not api_key:
            print("[DISCOVERY] ERROR: No Anthropic API key")
            return []

        agent = AlphaTestAgent(
            api_key=api_key,
            status_callback=lambda msg: print(f"[DISCOVERY] {msg}"),
            browser_type=project.get('browser_type', 'chromium')
        )

        try:
            await agent.initialize()

            # Navigate to URL using agent's method (adds to breadcrumbs)
            await agent.navigate(project['url'])

            # Login
            if project.get('email') and project.get('password'):
                print(f"[DISCOVERY] Logging in...")
                await agent.login(
                    login_url=project.get('login_url') or project['url'],
                    email=project['email'],
                    password=project['password']
                )

            # AI explores app
            print(f"[DISCOVERY] AI exploring entire app...")
            await agent.run_command(
                """Thoroughly explore this web application. Navigate through ALL navigation menus,
                sidebar items, and main features. Click through every section to discover all pages.
                Visit dashboard, projects, reports, settings, and any other pages you find.
                Do NOT logout or modify data.""",
                max_steps=30
            )

            # Extract discovered URLs from navigation tracker
            visited_urls = list(set(agent.nav_tracker.get_current_path()))
            print(f"\n[DISCOVERY] Found {len(visited_urls)} unique pages")

            # If no pages discovered, at least return the homepage
            if len(visited_urls) == 0:
                print(f"[DISCOVERY] WARNING: No pages discovered via navigation, adding homepage")
                visited_urls = [project['url']]

            # Get titles for each page
            for url in visited_urls:
                try:
                    await agent.page.goto(url, wait_until='networkidle', timeout=10000)
                    title = await agent.page.title()
                    path = url.replace(project['url'].rstrip('/'), '') or '/'

                    discovered_pages.append({
                        'url': url,
                        'path': path,
                        'title': title or path
                    })
                    print(f"[DISCOVERY] ✓ {title}")
                except:
                    discovered_pages.append({
                        'url': url,
                        'path': url.replace(project['url'].rstrip('/'), '') or '/',
                        'title': url.split('/')[-1] or 'Page'
                    })

            # Score pages for marketing value
            def score_page(pg):
                score = 50
                url, title, path = pg['url'].lower(), pg.get('title', '').lower(), pg.get('path', '').lower()

                high_value = {'dashboard': 30, 'home': 25, 'overview': 25, 'analytics': 20,
                             'report': 20, 'project': 15, 'workspace': 15, 'features': 25}
                low_value = ['login', 'logout', 'signup', 'auth', 'select', 'error', '404']

                for kw, pts in high_value.items():
                    if kw in url or kw in title or kw in path:
                        score += pts

                for kw in low_value:
                    if kw in url or kw in title or kw in path:
                        score -= 15

                if path.count('/') <= 1:
                    score += 10

                return max(0, min(100, score))

            for pg in discovered_pages:
                pg['marketing_score'] = score_page(pg)
                pg['suggested'] = pg['marketing_score'] >= 50

            discovered_pages.sort(key=lambda p: p['marketing_score'], reverse=True)

            print(f"\n[DISCOVERY] TOP PAGES:")
            for i, pg in enumerate(discovered_pages[:10], 1):
                emoji = "⭐" if pg['marketing_score'] >= 70 else "✨"
                print(f"[DISCOVERY]   {i}. {emoji} {pg['title']} (Score: {pg['marketing_score']})")

        except Exception as e:
            print(f"[DISCOVERY] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await agent.close()

        return discovered_pages

    # Run
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    discovered_pages = loop.run_until_complete(discover_async())
    loop.close()

    return jsonify({'success': True, 'pages': discovered_pages})

@app.route('/project/<project_id>/screenshots/generate', methods=['POST'])
@login_required
def generate_screenshots(project_id):
    """Generate marketing screenshots with device frames."""
    projects = load_projects()
    project = projects.get(project_id)
    if not project:
        return jsonify({'success': False, 'error': 'Project not found'}), 404

    # Get request data
    data = request.json
    devices = data.get('devices', [])
    mode = data.get('mode', 'auto')
    instructions = data.get('instructions', '')
    selected_pages = data.get('selected_pages', [])

    if not devices:
        return jsonify({'success': False, 'error': 'No devices selected'}), 400

    # Generate job ID
    job_id = f"screenshot_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Start screenshot generation in background thread
    thread = threading.Thread(
        target=run_screenshot_generation,
        args=(project_id, job_id, project, devices, mode, instructions, selected_pages)
    )
    thread.start()

    # Store job info
    active_screenshot_jobs[job_id] = {
        'project_id': project_id,
        'status': 'running',
        'thread': thread
    }

    return jsonify({'success': True, 'job_id': job_id})

@app.route('/project/<project_id>/screenshots/<job_id>/download')
@login_required
def download_screenshots(project_id, job_id):
    """Download screenshot ZIP file."""
    zip_path = SCREENSHOTS_DIR / f"{job_id}.zip"

    if not zip_path.exists():
        return "Screenshot package not found", 404

    return send_from_directory(
        SCREENSHOTS_DIR,
        f"{job_id}.zip",
        as_attachment=True,
        download_name=f"alphatest_screenshots_{project_id}.zip"
    )

@app.route('/project/<project_id>/pulse')
def project_pulse_dashboard(project_id):
    """Show quality trends dashboard for a project."""
    projects = load_projects()
    project = projects.get(project_id)
    if not project:
        return "Project not found", 404

    # Get historical reports for trend analysis
    project_reports_dir = REPORTS_DIR / project_id
    reports_data = []
    if project_reports_dir.exists():
        for report_dir in sorted(project_reports_dir.iterdir(), reverse=False):  # Chronological order
            if report_dir.is_dir():
                report_file = report_dir / "report.json"
                if report_file.exists():
                    try:
                        report_data = json.loads(report_file.read_text())
                        reports_data.append({
                            'id': report_dir.name,
                            'date': report_data.get('date', ''),
                            'summary': report_data.get('summary', {}),
                        })
                    except:
                        pass

    # Get issue tracking trend data
    tracker = IssueTracker(project_reports_dir)
    trend_data = tracker.get_trend_data(limit=10)

    return render_template('pulse_dashboard.html',
                          project=project,
                          reports=reports_data,
                          trend_data=trend_data)

@app.route('/project/<project_id>/triage')
def project_triage_board(project_id):
    """Show Kanban triage board for issue management."""
    projects = load_projects()
    project = projects.get(project_id)
    if not project:
        return "Project not found", 404

    # Get issues from tracker
    project_reports_dir = REPORTS_DIR / project_id
    tracker = IssueTracker(project_reports_dir)

    # Load triage state (separate from issue_tracker for workflow management)
    triage_file = project_reports_dir / "triage_state.json"
    triage_state = {}
    if triage_file.exists():
        try:
            triage_state = json.loads(triage_file.read_text())
        except:
            triage_state = {}

    # Get all tracked issues and enrich with triage data
    all_issues = []
    for fingerprint, issue_data in tracker.database.get('issues', {}).items():
        issue = issue_data['issue_data'].copy()
        issue['fingerprint'] = fingerprint
        issue['status'] = issue_data.get('status', 'active')
        issue['seen_count'] = issue_data.get('seen_count', 1)
        issue['first_seen'] = issue_data.get('first_seen', '')

        # Add triage metadata
        triage_meta = triage_state.get(fingerprint, {})
        issue['triage_status'] = triage_meta.get('triage_status', 'new')  # new, investigating, confirmed, fixed, closed
        issue['assignee'] = triage_meta.get('assignee', '')
        issue['priority'] = triage_meta.get('priority', 'medium')  # low, medium, high, critical
        issue['notes'] = triage_meta.get('notes', [])

        all_issues.append(issue)

    return render_template('triage_board.html',
                          project=project,
                          issues=all_issues)

@app.route('/reports/<project_id>/<report_id>')
@app.route('/reports/<project_id>/<report_id>/report.html')
def view_report(project_id, report_id):
    """View a specific report."""
    report_dir = REPORTS_DIR / project_id / report_id
    report_file = report_dir / "report.html"
    if report_file.exists():
        return send_from_directory(report_dir, "report.html")
    return "Report not found", 404

@app.route('/reports/<project_id>/<report_id>/screenshots/<filename>')
def report_screenshot(project_id, report_id, filename):
    """Serve report screenshots."""
    screenshot_dir = REPORTS_DIR / project_id / report_id / "screenshots"
    if not screenshot_dir.exists():
        return "Screenshots directory not found", 404
    return send_from_directory(screenshot_dir, filename)

@app.route('/reports/<project_id>/<report_id>/videos/<filename>')
def report_video(project_id, report_id, filename):
    """Serve report videos."""
    video_dir = REPORTS_DIR / project_id / report_id / "videos"
    if not video_dir.exists():
        return "Videos directory not found", 404
    return send_from_directory(video_dir, filename)

@app.route('/api/project/<project_id>/compare')
def compare_reports_api(project_id):
    """Compare two test reports."""
    report1_id = request.args.get('report1')
    report2_id = request.args.get('report2')

    if not report1_id or not report2_id:
        return jsonify({'error': 'Both report1 and report2 parameters required'}), 400

    project_reports_dir = REPORTS_DIR / project_id

    # Load both reports
    report1_file = project_reports_dir / report1_id / "report.json"
    report2_file = project_reports_dir / report2_id / "report.json"

    if not report1_file.exists() or not report2_file.exists():
        return jsonify({'error': 'One or both reports not found'}), 404

    report1 = json.loads(report1_file.read_text())
    report2 = json.loads(report2_file.read_text())

    # Calculate comparison
    comparison = {
        'report1': {
            'id': report1_id,
            'date': report1.get('generated_at', report1_id),
            'summary': report1.get('summary', {}),
            'issues': report1.get('issues', [])
        },
        'report2': {
            'id': report2_id,
            'date': report2.get('generated_at', report2_id),
            'summary': report2.get('summary', {}),
            'issues': report2.get('issues', [])
        },
        'changes': {
            'tests_passed_delta': report2.get('summary', {}).get('passed', 0) - report1.get('summary', {}).get('passed', 0),
            'tests_failed_delta': report2.get('summary', {}).get('failed', 0) - report1.get('summary', {}).get('failed', 0),
            'issues_delta': len(report2.get('issues', [])) - len(report1.get('issues', [])),
        }
    }

    # Find new, resolved, and persisting issues
    report1_fingerprints = {issue.get('fingerprint'): issue for issue in report1.get('issues', []) if issue.get('fingerprint')}
    report2_fingerprints = {issue.get('fingerprint'): issue for issue in report2.get('issues', []) if issue.get('fingerprint')}

    new_issues = [issue for fp, issue in report2_fingerprints.items() if fp not in report1_fingerprints]
    resolved_issues = [issue for fp, issue in report1_fingerprints.items() if fp not in report2_fingerprints]
    persisting_issues = [issue for fp, issue in report2_fingerprints.items() if fp in report1_fingerprints]

    comparison['changes']['new_issues'] = new_issues
    comparison['changes']['resolved_issues'] = resolved_issues
    comparison['changes']['persisting_issues'] = persisting_issues

    return jsonify(comparison)

@app.route('/project/<project_id>/compare')
def compare_reports_page(project_id):
    """Show comparison page."""
    projects = load_projects()
    project = projects.get(project_id)
    if not project:
        return "Project not found", 404

    report1_id = request.args.get('report1')
    report2_id = request.args.get('report2')

    if not report1_id or not report2_id:
        return "Missing report IDs", 400

    return render_template('compare.html',
                         project=project,
                         project_id=project_id,
                         report1_id=report1_id,
                         report2_id=report2_id)

@app.route('/api/project/<project_id>/trends')
def get_trends(project_id):
    """Get trend data for charts."""
    days = int(request.args.get('days', 30))

    project_reports_dir = REPORTS_DIR / project_id
    if not project_reports_dir.exists():
        return jsonify({'data': []})

    # Collect all reports
    reports = []
    for report_dir in sorted(project_reports_dir.iterdir()):
        if report_dir.is_dir():
            report_file = report_dir / "report.json"
            if report_file.exists():
                try:
                    report_data = json.loads(report_file.read_text())
                    reports.append({
                        'id': report_dir.name,
                        'date': report_data.get('generated_at', report_dir.name),
                        'summary': report_data.get('summary', {}),
                        'issues': len(report_data.get('issues', []))
                    })
                except:
                    pass

    # Sort by date
    reports.sort(key=lambda r: r['date'])

    # Get recent reports based on days parameter
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_reports = []

    for report in reports:
        try:
            report_date = datetime.fromisoformat(report['date'].replace('Z', '+00:00'))
            if report_date >= cutoff_date:
                recent_reports.append(report)
        except:
            # If can't parse date, include it anyway
            recent_reports.append(report)

    # Format for charts
    trend_data = {
        'labels': [],
        'passed': [],
        'failed': [],
        'total': [],
        'issues': [],
        'success_rate': []
    }

    for report in recent_reports[-50:]:  # Limit to last 50 reports
        # Format date for label
        try:
            dt = datetime.fromisoformat(report['date'].replace('Z', '+00:00'))
            label = dt.strftime('%m/%d %H:%M')
        except:
            label = report['id'][:10]

        trend_data['labels'].append(label)

        summary = report['summary']
        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        total = summary.get('total', 0)

        trend_data['passed'].append(passed)
        trend_data['failed'].append(failed)
        trend_data['total'].append(total)
        trend_data['issues'].append(report['issues'])

        # Calculate success rate
        success_rate = int((passed / total * 100)) if total > 0 else 0
        trend_data['success_rate'].append(success_rate)

    return jsonify(trend_data)

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

    return jsonify({'specs': projects[project_id].get('test_specs', [])}

)

@app.route('/api/project/<project_id>/visual/baselines', methods=['GET'])
def get_visual_baselines(project_id):
    """Get list of visual regression baselines."""
    from visual_regression import VisualRegressionTester

    project_dir = REPORTS_DIR / project_id
    vrt = VisualRegressionTester(project_dir)
    baselines = vrt.get_baselines()

    return jsonify({'baselines': baselines})

@app.route('/api/project/<project_id>/visual/baseline/<baseline_name>', methods=['DELETE'])
def delete_visual_baseline(project_id, baseline_name):
    """Delete a visual regression baseline."""
    from visual_regression import VisualRegressionTester

    project_dir = REPORTS_DIR / project_id
    vrt = VisualRegressionTester(project_dir)
    success = vrt.delete_baseline(baseline_name)

    return jsonify({'success': success})

@app.route('/project/<project_id>/baselines/<filename>')
def serve_baseline(project_id, filename):
    """Serve baseline images."""
    baselines_dir = REPORTS_DIR / project_id / "baselines"
    if not baselines_dir.exists():
        return "Baselines directory not found", 404
    return send_from_directory(baselines_dir, filename)

@app.route('/project/<project_id>/diffs/<filename>')
def serve_diff(project_id, filename):
    """Serve diff images."""
    diffs_dir = REPORTS_DIR / project_id / "diffs"
    if not diffs_dir.exists():
        return "Diffs directory not found", 404
    return send_from_directory(diffs_dir, filename)


# Test Data Management Endpoints
@app.route('/api/project/<project_id>/fixtures', methods=['GET'])
def get_fixtures(project_id):
    """Get list of all fixtures."""
    from test_data import TestDataManager

    project_dir = REPORTS_DIR / project_id
    tdm = TestDataManager(project_dir)
    fixtures = tdm.list_fixtures()

    # Get fixture data for each
    fixture_list = []
    for fixture_name in fixtures:
        fixture_data = tdm.get_fixture(fixture_name)
        fixture_list.append({
            'name': fixture_name,
            'type': type(fixture_data).__name__,
            'count': len(fixture_data) if isinstance(fixture_data, list) else 1
        })

    return jsonify({'fixtures': fixture_list})

@app.route('/api/project/<project_id>/fixtures/<fixture_name>', methods=['GET'])
def get_fixture(project_id, fixture_name):
    """Get a specific fixture."""
    from test_data import TestDataManager

    project_dir = REPORTS_DIR / project_id
    tdm = TestDataManager(project_dir)
    fixture_data = tdm.get_fixture(fixture_name)

    if fixture_data is None:
        return jsonify({'error': 'Fixture not found'}), 404

    return jsonify({'name': fixture_name, 'data': fixture_data})

@app.route('/api/project/<project_id>/fixtures', methods=['POST'])
def save_fixture(project_id):
    """Save a new fixture."""
    from test_data import TestDataManager

    data = request.get_json()
    fixture_name = data.get('name')
    fixture_data = data.get('data')

    if not fixture_name or not fixture_data:
        return jsonify({'error': 'Name and data are required'}), 400

    project_dir = REPORTS_DIR / project_id
    tdm = TestDataManager(project_dir)
    success = tdm.save_fixture(fixture_name, fixture_data)

    return jsonify({'success': success, 'name': fixture_name})

@app.route('/api/project/<project_id>/fixtures/<fixture_name>', methods=['DELETE'])
def delete_fixture(project_id, fixture_name):
    """Delete a fixture."""
    from test_data import TestDataManager

    project_dir = REPORTS_DIR / project_id
    tdm = TestDataManager(project_dir)
    success = tdm.delete_fixture(fixture_name)

    return jsonify({'success': success})

@app.route('/api/project/<project_id>/test-data/generate', methods=['POST'])
def generate_test_data(project_id):
    """Generate test data on-demand."""
    from test_data import TestDataManager

    data = request.get_json()
    entity_type = data.get('entity_type')
    count = data.get('count', 1)
    save_as_fixture = data.get('save_as_fixture', False)
    fixture_name = data.get('fixture_name')

    if not entity_type:
        return jsonify({'error': 'entity_type is required'}), 400

    project_dir = REPORTS_DIR / project_id
    tdm = TestDataManager(project_dir)

    try:
        if count == 1:
            # Generate single item
            generators = {
                'user': tdm.generate_user,
                'address': tdm.generate_address,
                'company': tdm.generate_company,
                'product': tdm.generate_product,
                'credit_card': tdm.generate_credit_card
            }
            generator = generators.get(entity_type)
            if not generator:
                return jsonify({'error': f'Unknown entity type: {entity_type}'}), 400

            generated_data = generator()
        else:
            # Generate multiple items
            generated_data = tdm.create_seed_data(entity_type, count)

        # Optionally save as fixture
        if save_as_fixture and fixture_name:
            tdm.save_fixture(fixture_name, generated_data)

        return jsonify({
            'success': True,
            'entity_type': entity_type,
            'count': count,
            'data': generated_data,
            'saved_as_fixture': save_as_fixture
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# API Testing Endpoints
@app.route('/api/project/<project_id>/api-test/request', methods=['POST'])
def api_test_request(project_id):
    """Make an API test request."""
    from api_testing import APITester

    data = request.get_json()
    method = data.get('method', 'GET')
    endpoint = data.get('endpoint')
    headers = data.get('headers', {})
    query_params = data.get('query_params', {})
    json_body = data.get('json_body')
    base_url = data.get('base_url', '')

    if not endpoint:
        return jsonify({'error': 'endpoint is required'}), 400

    try:
        # Create API tester
        api_tester = APITester(base_url=base_url, default_headers=headers)

        # Make request (without page for now - would need active session)
        # This endpoint is for standalone API testing
        import asyncio
        from aiohttp import ClientSession

        async def make_request():
            async with ClientSession() as session:
                url = endpoint if endpoint.startswith('http') else f"{base_url}/{endpoint.lstrip('/')}"

                if query_params:
                    from urllib.parse import urlencode
                    url = f"{url}?{urlencode(query_params)}"

                kwargs = {'headers': headers}
                if json_body:
                    import json
                    kwargs['json'] = json_body

                async with session.request(method, url, **kwargs) as resp:
                    response_body = await resp.text()
                    try:
                        response_body = json.loads(response_body)
                    except:
                        pass

                    return {
                        'status_code': resp.status,
                        'headers': dict(resp.headers),
                        'body': response_body
                    }

        # Run async request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(make_request())
        loop.close()

        return jsonify({
            'success': True,
            'response': result
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


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
# TRIAGE BOARD API
# ============================================

@app.route('/api/project/<project_id>/triage/update', methods=['POST'])
@login_required
def update_triage_status(project_id):
    """Update triage status for an issue."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()
    fingerprint = data.get('fingerprint')
    updates = data.get('updates', {})

    if not fingerprint:
        return jsonify({'error': 'Fingerprint required'}), 400

    # Load and update triage state
    project_reports_dir = REPORTS_DIR / project_id
    project_reports_dir.mkdir(parents=True, exist_ok=True)
    triage_file = project_reports_dir / "triage_state.json"

    triage_state = {}
    if triage_file.exists():
        try:
            triage_state = json.loads(triage_file.read_text())
        except:
            triage_state = {}

    # Get existing or create new entry
    if fingerprint not in triage_state:
        triage_state[fingerprint] = {
            'triage_status': 'new',
            'assignee': '',
            'priority': 'medium',
            'notes': [],
            'updated_at': datetime.now().isoformat(),
            'updated_by': session.get('username', 'unknown')
        }

    # Apply updates
    if 'triage_status' in updates:
        triage_state[fingerprint]['triage_status'] = updates['triage_status']
    if 'assignee' in updates:
        triage_state[fingerprint]['assignee'] = updates['assignee']
    if 'priority' in updates:
        triage_state[fingerprint]['priority'] = updates['priority']

    triage_state[fingerprint]['updated_at'] = datetime.now().isoformat()
    triage_state[fingerprint]['updated_by'] = session.get('username', 'unknown')

    # Save updated state
    triage_file.write_text(json.dumps(triage_state, indent=2))

    return jsonify({'success': True, 'triage_state': triage_state[fingerprint]})


@app.route('/api/project/<project_id>/triage/note', methods=['POST'])
@login_required
def add_triage_note(project_id):
    """Add a note/comment to an issue."""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()
    fingerprint = data.get('fingerprint')
    note_text = data.get('note', '').strip()

    if not fingerprint or not note_text:
        return jsonify({'error': 'Fingerprint and note required'}), 400

    # Load triage state
    project_reports_dir = REPORTS_DIR / project_id
    project_reports_dir.mkdir(parents=True, exist_ok=True)
    triage_file = project_reports_dir / "triage_state.json"

    triage_state = {}
    if triage_file.exists():
        try:
            triage_state = json.loads(triage_file.read_text())
        except:
            triage_state = {}

    # Ensure issue entry exists
    if fingerprint not in triage_state:
        triage_state[fingerprint] = {
            'triage_status': 'new',
            'assignee': '',
            'priority': 'medium',
            'notes': [],
            'updated_at': datetime.now().isoformat(),
            'updated_by': session.get('username', 'unknown')
        }

    # Add note
    note = {
        'text': note_text,
        'author': session.get('username', 'unknown'),
        'timestamp': datetime.now().isoformat()
    }
    if 'notes' not in triage_state[fingerprint]:
        triage_state[fingerprint]['notes'] = []
    triage_state[fingerprint]['notes'].append(note)

    # Save updated state
    triage_file.write_text(json.dumps(triage_state, indent=2))

    return jsonify({'success': True, 'note': note})


# ============================================
# SOCKET.IO EVENTS
# ============================================

@socketio.on('connect')
def handle_connect():
    emit('status', {'message': 'Connected to AlphaTest'})

@socketio.on('join')
def handle_join(data):
    """Join a Socket.IO room for real-time updates."""
    from flask_socketio import join_room
    room = data.get('job_id') or data.get('project_id')
    if room:
        join_room(room)
        emit('joined', {'room': room})

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

def run_screenshot_generation(project_id, job_id, project, devices, mode, instructions, selected_pages=None):
    """Background task for screenshot generation."""
    print(f"[SCREENSHOT] Starting job {job_id} for project {project_id}")
    print(f"[SCREENSHOT] Devices: {devices}, Mode: {mode}")
    if selected_pages:
        print(f"[SCREENSHOT] Selected pages: {len(selected_pages)}")

    async def generate_async():
        from playwright.async_api import async_playwright

        print(f"[SCREENSHOT] Initializing generator for job {job_id}")
        generator = ScreenshotGenerator(project_id, output_dir=str(SCREENSHOTS_DIR / job_id))
        config = load_config()
        api_key = config.get('anthropic_api_key')

        try:
            print(f"[SCREENSHOT] Starting async generation for job {job_id}")
            # Emit progress
            socketio.emit('screenshot_progress', {
                'progress': 10,
                'status': 'Initializing browser...'
            }, room=job_id)

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
                page = await context.new_page()

                # Navigate to app
                socketio.emit('screenshot_progress', {
                    'progress': 20,
                    'status': f'Loading {project["url"]}...'
                }, room=job_id)

                await page.goto(project['url'], wait_until='networkidle')

                # Login if credentials provided
                if project.get('email') and project.get('password'):
                    login_url = project.get('login_url') or project['url']
                    await page.goto(login_url, wait_until='networkidle')

                    # Try to find and fill email/password fields
                    try:
                        email_input = await page.query_selector('input[type="email"], input[name*="email" i], input[id*="email" i]')
                        if email_input:
                            await email_input.fill(project['email'])

                        password_input = await page.query_selector('input[type="password"]')
                        if password_input:
                            await password_input.fill(project['password'])

                        # Find and click submit button
                        submit_button = await page.query_selector('button[type="submit"], button:has-text("Log in"), button:has-text("Sign in")')
                        if submit_button:
                            await submit_button.click()
                            await page.wait_for_load_state('networkidle')

                            # After login, navigate to homepage to ensure we start discovery from authenticated state
                            await page.goto(project['url'], wait_until='networkidle')
                            await page.wait_for_timeout(2000)  # Let the app settle after login
                            print(f"[SCREENSHOT] Navigated to homepage after login: {page.url}")
                    except:
                        pass

                # Determine pages to capture
                pages_to_capture = []

                if mode == 'select' and selected_pages:
                    # Use selected pages from discovery
                    socketio.emit('screenshot_progress', {
                        'progress': 30,
                        'status': f'Preparing {len(selected_pages)} selected pages...'
                    }, room=job_id)

                    for sp in selected_pages:
                        pages_to_capture.append({
                            'url': sp['url'],
                            'name': sp['title']
                        })

                elif mode == 'auto':
                    socketio.emit('screenshot_progress', {
                        'progress': 30,
                        'status': 'Capturing current page...'
                    }, room=job_id)

                    # Simple auto mode - just capture the homepage/current page
                    # Users should use "Discover Pages" first for multi-page screenshots
                    pages_to_capture.append({
                        'url': page.url,
                        'name': await page.title() or 'Homepage'
                    })

                    print(f"[SCREENSHOT] Auto mode - capturing current page: {page.url}")

                else:  # Manual mode
                    # Parse instructions
                    if not instructions:
                        pages_to_capture.append({
                            'url': page.url,
                            'name': 'Current Page'
                        })
                    else:
                        # Parse URLs from instructions
                        lines = instructions.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line.startswith('/') or line.startswith('http'):
                                url = line if line.startswith('http') else project['url'].rstrip('/') + line
                                pages_to_capture.append({
                                    'url': url,
                                    'name': url.split('/')[-1] or 'Page'
                                })

                # Capture screenshots
                total_captures = len(pages_to_capture) * len(devices)
                total_pages = len(pages_to_capture)
                current_capture = 0
                current_page_num = 0
                all_screenshots = []

                print(f"[SCREENSHOT] Found {total_pages} pages to capture")
                print(f"[SCREENSHOT] Total captures: {total_captures}")

                # Device viewport configurations
                device_viewports = {
                    'macbook': {'width': 1920, 'height': 1080},
                    'iphone': {'width': 390, 'height': 844},  # iPhone 15 Pro dimensions
                    'android': {'width': 412, 'height': 915},  # Pixel 8 Pro dimensions
                    'ipad': {'width': 1024, 'height': 1366},  # iPad Pro 12.9"
                    'desktop': {'width': 1920, 'height': 1080}
                }

                for page_idx, page_info in enumerate(pages_to_capture):
                    current_page_num = page_idx + 1
                    try:
                        # Capture for each device type with proper viewport
                        for device_type in devices:
                            current_capture += 1
                            progress = 40 + int((current_capture / total_captures) * 50)

                            print(f"[SCREENSHOT] Capturing {page_info['name']} on {device_type} ({current_page_num}/{total_pages})")
                            socketio.emit('screenshot_progress', {
                                'progress': progress,
                                'status': f'Capturing {page_info["name"]} on {device_type}...',
                                'totalPages': total_pages,
                                'currentPage': current_page_num
                            }, room=job_id)

                            try:
                                # Set viewport for this device
                                viewport = device_viewports.get(device_type, {'width': 1920, 'height': 1080})
                                await page.set_viewport_size(viewport)
                                print(f"[SCREENSHOT] Set viewport to {viewport}")

                                # Navigate to page
                                print(f"[SCREENSHOT] Navigating to: {page_info['url']}")
                                await page.goto(page_info['url'], wait_until='networkidle', timeout=30000)
                                await page.wait_for_timeout(2000)  # Let page settle

                                # Capture screenshot with proper viewport
                                print(f"[SCREENSHOT] Capturing screenshot of {page_info['name']} at {viewport}")
                                screenshot_bytes = await page.screenshot(full_page=True, type='png')
                                print(f"[SCREENSHOT] Screenshot captured, size: {len(screenshot_bytes)} bytes")

                                # Send live preview (only for first device)
                                if devices.index(device_type) == 0:
                                    import base64
                                    preview_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                                    socketio.emit('screenshot_preview', {
                                        'page': page_info['name'],
                                        'url': page_info['url'],
                                        'device': device_type,
                                        'preview': f'data:image/png;base64,{preview_b64[:1000]}...',
                                    }, room=job_id)

                                # Generate AI description (only once per page, not per device)
                                ai_desc = "Screenshot captured"
                                if devices.index(device_type) == 0 and api_key:
                                    try:
                                        print(f"[SCREENSHOT] Generating AI description for {page_info['name']}")
                                        ai_desc = generate_ai_description(screenshot_bytes, api_key)
                                        print(f"[SCREENSHOT] AI description: {ai_desc[:100]}...")
                                    except Exception as ai_error:
                                        print(f"[SCREENSHOT] AI description failed: {ai_error}")

                                # Apply device frame
                                frame_image, spec = generator.apply_device_frame(screenshot_bytes, device_type)
                                print(f"[SCREENSHOT] Frame applied: {device_type}, size: {frame_image.size}")

                                # Generate metadata
                                metadata = generator.generate_metadata(
                                    url=page_info['url'],
                                    description=page_info['name'],
                                    ai_description=ai_desc
                                )

                                # Save screenshot
                                file_path = generator.save_screenshot(
                                    frame_image,
                                    metadata,
                                    device_type,
                                    page_info['name']
                                )
                                print(f"[SCREENSHOT] Saved to: {file_path}")

                                all_screenshots.append({
                                    'device': device_type,
                                    'page': page_info['name'],
                                    'preview_url': f'/project/{project_id}/screenshots/{job_id}/preview/{Path(file_path).name}',
                                    'metadata': metadata
                                })
                            except Exception as frame_error:
                                print(f"[SCREENSHOT] Error applying {device_type} frame: {frame_error}")
                                import traceback
                                traceback.print_exc()
                                # Continue with next device

                    except Exception as e:
                        print(f"[SCREENSHOT] ERROR capturing {page_info['url']}: {e}")
                        import traceback
                        traceback.print_exc()

                        # Notify user of page failure
                        socketio.emit('screenshot_page_error', {
                            'page': page_info['name'],
                            'url': page_info['url'],
                            'error': str(e)
                        }, room=job_id)
                        continue

                print(f"[SCREENSHOT] Captured {len(all_screenshots)} total screenshots")
                await browser.close()

            # Create ZIP
            socketio.emit('screenshot_progress', {
                'progress': 95,
                'status': 'Creating download package...'
            }, room=job_id)

            zip_path = generator.create_zip_archive(output_filename=f"{job_id}.zip")

            # Complete
            socketio.emit('screenshot_complete', {
                'screenshots': all_screenshots,
                'zip_url': f'/project/{project_id}/screenshots/{job_id}/download'
            }, room=job_id)

            # Update job status
            if job_id in active_screenshot_jobs:
                active_screenshot_jobs[job_id]['status'] = 'completed'

        except Exception as e:
            error_msg = f"Screenshot generation error: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()

            # Log to console for Cloud Run logs
            import sys
            print(f"SCREENSHOT ERROR for job {job_id}:", file=sys.stderr)
            print(f"  Error: {str(e)}", file=sys.stderr)
            print(f"  Type: {type(e).__name__}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

            socketio.emit('screenshot_error', {
                'error': str(e),
                'details': traceback.format_exc()
            }, room=job_id)

            if job_id in active_screenshot_jobs:
                active_screenshot_jobs[job_id]['status'] = 'failed'

    # Run async task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(generate_async())
    loop.close()

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
                screenshot_callback=lambda path: socketio.emit('test_screenshot', {'path': path}),
                browser_type=project.get('browser_type', 'chromium')
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
                
                # Run the test with step limit
                result = await agent.run_command(command, max_steps=10)

                # Check if test hit step limit and needs continuation
                if result.get('status') == 'running' and len(result.get('steps', [])) >= 10:
                    # Test paused at step limit - ask user if they want to continue
                    socketio.emit('test_progress', {'message': '⏸️ Reached 10 steps. Ready to continue?'})

                    # Generate intermediate report
                    report_data = agent.get_report_data()
                    report_path = generate_report(report_data, report_dir, project)

                    # Emit continuation request
                    socketio.emit('test_complete', {
                        'status': 'needs_continuation',
                        'result': result,
                        'steps_completed': len(result.get('steps', [])),
                        'report_url': f'/reports/{project_id}/{session_id}'
                    })

                    # Keep browser open for continuation - don't close yet
                    return

                # Run compliance scans after test
                socketio.emit('test_progress', {'message': '[Query] Running compliance scans...'})

                # Get current response for security headers
                response = await agent.page.goto(agent.page.url, wait_until='domcontentloaded')

                # Run all scans
                accessibility_results = await agent.run_accessibility_scan()
                security_results = await agent.check_security_headers(response)
                performance_results = await agent.run_lighthouse_audit()

                # Close browser and capture video
                video_path = await agent.close()
                if video_path:
                    agent.video_path = video_path

                # Generate report with scan data
                report_data = agent.get_report_data()
                report_data['accessibility_results'] = accessibility_results
                report_data['security_results'] = security_results
                report_data['performance_results'] = performance_results

                # Track issues for regression detection
                project_reports_dir = REPORTS_DIR / project_id
                tracker = IssueTracker(project_reports_dir)
                tracking_results = tracker.process_test_run(session_id, report_data.get('issues', []))

                # Add tracking data to report
                report_data['issue_tracking'] = tracking_results
                report_path = generate_report(report_data, report_dir, project)

                # Send Slack notification if enabled
                if project.get('slack_notifications_enabled') and project.get('slack_webhook_url'):
                    try:
                        from integrations.slack import send_slack_notification
                        report_url_full = f"{request.url_root.rstrip('/')}/reports/{project_id}/{session_id}"
                        send_slack_notification(
                            project.get('slack_webhook_url'),
                            project.get('name', 'Unknown Project'),
                            report_data,
                            report_url_full
                        )
                    except Exception as e:
                        print(f"Failed to send Slack notification: {e}")

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
                # Ensure browser is closed even on error
                try:
                    await agent.close()
                except:
                    pass
        
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
                screenshot_callback=lambda path: socketio.emit('test_screenshot', {'path': path}),
                browser_type=project.get('browser_type', 'chromium')
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

                # Run compliance scans after all tests
                socketio.emit('test_progress', {'message': '[Query] Running compliance scans...'})

                # Get current response for security headers
                response = await agent.page.goto(agent.page.url, wait_until='domcontentloaded')

                # Run all scans
                accessibility_results = await agent.run_accessibility_scan()
                security_results = await agent.check_security_headers(response)
                performance_results = await agent.run_lighthouse_audit()

                # Close browser and capture video
                video_path = await agent.close()
                if video_path:
                    agent.video_path = video_path

                # Generate report with scan data
                report_data = agent.get_report_data()
                report_data['specs_results'] = results
                report_data['accessibility_results'] = accessibility_results
                report_data['security_results'] = security_results
                report_data['performance_results'] = performance_results

                # Track issues for regression detection
                project_reports_dir = REPORTS_DIR / project_id
                tracker = IssueTracker(project_reports_dir)
                tracking_results = tracker.process_test_run(session_id, report_data.get('issues', []))

                # Add tracking data to report
                report_data['issue_tracking'] = tracking_results
                report_path = generate_report(report_data, report_dir, project)

                # Send Slack notification if enabled
                if project.get('slack_notifications_enabled') and project.get('slack_webhook_url'):
                    try:
                        from integrations.slack import send_slack_notification
                        report_url_full = f"{request.url_root.rstrip('/')}/reports/{project_id}/{session_id}"
                        send_slack_notification(
                            project.get('slack_webhook_url'),
                            project.get('name', 'Unknown Project'),
                            report_data,
                            report_url_full
                        )
                    except Exception as e:
                        print(f"Failed to send Slack notification: {e}")

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
                # Ensure browser is closed even on error
                try:
                    await agent.close()
                except:
                    pass
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(specs_async())
        loop.close()
    
    thread = threading.Thread(target=run_specs)
    thread.start()

# ============================================
# API v1 - For Integrations (GitHub Actions, CLI, etc.)
# ============================================

# In-memory storage for active test runs (in production, use Redis)
active_runs = {}

def require_api_key(f):
    """Decorator to require API key for API routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401

        api_key = auth_header.replace('Bearer ', '')

        # Load user by API key
        user = auth.get_user_by_api_key(api_key)
        if not user:
            return jsonify({'error': 'Invalid API key'}), 401

        # Attach user to request
        request.api_user = user
        return f(*args, **kwargs)

    return decorated_function

@app.route('/api/v1/run', methods=['POST'])
@require_api_key
def api_trigger_run():
    """Trigger a test run via API"""
    try:
        data = request.json
        project_id = data.get('project_id')
        base_url = data.get('base_url')
        specs = data.get('specs')  # List of spec IDs or None for all
        metadata = data.get('metadata', {})  # GitHub context

        if not project_id:
            return jsonify({'error': 'project_id is required'}), 400

        # Load project
        projects = load_projects()
        if project_id not in projects:
            return jsonify({'error': 'Project not found'}), 404

        project = projects[project_id]

        # Check user has access to project
        if project.get('owner_id') != request.api_user['id']:
            return jsonify({'error': 'Access denied'}), 403

        # Generate run ID
        run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_dir = REPORTS_DIR / project_id / run_id
        report_dir.mkdir(parents=True, exist_ok=True)

        # Store metadata
        metadata_file = report_dir / "metadata.json"
        metadata_file.write_text(json.dumps({
            'run_id': run_id,
            'project_id': project_id,
            'triggered_by': 'api',
            'user_id': request.api_user['id'],
            'metadata': metadata,
            'started_at': datetime.now().isoformat()
        }, indent=2))

        # Load test specs
        test_specs = project.get('test_specs', [])
        if specs:
            # Filter to requested specs
            test_specs = [s for s in test_specs if s['id'] in specs]
        else:
            # Only run enabled specs
            test_specs = [s for s in test_specs if s.get('enabled', True)]

        if not test_specs:
            return jsonify({'error': 'No specs to run'}), 400

        # Initialize run status
        active_runs[run_id] = {
            'project_id': project_id,
            'status': 'running',
            'progress': f'Starting {len(test_specs)} test(s)...',
            'total': len(test_specs),
            'completed': 0,
            'passed': 0,
            'failed': 0,
            'started_at': datetime.now().isoformat()
        }

        # Run tests in background thread
        def run_tests_api():
            async def tests_async():
                from agent import AlphaTestAgent

                agent = AlphaTestAgent(
                    api_key=config.get('anthropic_api_key'),
                    browser_type=project.get('browser_type', 'chromium')
                )
                await agent.initialize(session_dir=report_dir)

                try:
                    results = []
                    test_url = base_url or project.get('url')

                    for idx, spec in enumerate(test_specs):
                        active_runs[run_id]['progress'] = f'Running test {idx + 1}/{len(test_specs)}: {spec["name"]}'

                        try:
                            result = await agent.run_spec_test(test_url, spec)
                            results.append(result)

                            if result.get('success'):
                                active_runs[run_id]['passed'] += 1
                            else:
                                active_runs[run_id]['failed'] += 1

                            active_runs[run_id]['completed'] = idx + 1
                        except Exception as e:
                            results.append({
                                'spec_name': spec['name'],
                                'success': False,
                                'error': str(e)
                            })
                            active_runs[run_id]['failed'] += 1
                            active_runs[run_id]['completed'] = idx + 1

                    # Close browser and capture video
                    video_path = await agent.close()
                    if video_path:
                        agent.video_path = video_path

                    # Generate report
                    report_data = agent.get_report_data()
                    report_data['results'] = results
                    report_data['metadata'] = metadata

                    generate_report(report_data, report_dir, project)

                    # Send Slack notification if enabled
                    if project.get('slack_notifications_enabled') and project.get('slack_webhook_url'):
                        try:
                            from integrations.slack import send_slack_notification
                            base_url = os.environ.get('BASE_URL', 'http://localhost:8080')
                            report_url_full = f"{base_url}/reports/{project_id}/{run_id}"
                            send_slack_notification(
                                project.get('slack_webhook_url'),
                                project.get('name', 'Unknown Project'),
                                report_data,
                                report_url_full
                            )
                        except Exception as e:
                            print(f"Failed to send Slack notification: {e}")

                    # Update final status
                    active_runs[run_id]['status'] = 'completed'
                    active_runs[run_id]['completed'] = True
                    active_runs[run_id]['finished_at'] = datetime.now().isoformat()
                    active_runs[run_id]['report_url'] = f'/reports/{project_id}/{run_id}'

                except Exception as e:
                    active_runs[run_id]['status'] = 'failed'
                    active_runs[run_id]['error'] = str(e)
                    # Ensure browser is closed even on error
                    try:
                        await agent.close()
                    except:
                        pass

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(tests_async())
            loop.close()

        thread = threading.Thread(target=run_tests_api, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'run_id': run_id,
            'project_id': project_id,
            'report_url': f'/reports/{project_id}/{run_id}',
            'status_url': f'/api/v1/run/{run_id}/status'
        }), 202

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/run/<run_id>/status', methods=['GET'])
@require_api_key
def api_run_status(run_id):
    """Get status of a test run"""
    if run_id not in active_runs:
        return jsonify({'error': 'Run not found'}), 404

    run_data = active_runs[run_id].copy()
    return jsonify(run_data)

@app.route('/api/v1/projects', methods=['GET'])
@require_api_key
def api_list_projects():
    """List all projects for the authenticated user"""
    projects = load_projects()
    user_projects = {
        k: {
            'id': k,
            'name': v.get('name'),
            'url': v.get('url'),
            'created_at': v.get('created_at')
        }
        for k, v in projects.items()
        if v.get('owner_id') == request.api_user['id']
    }
    return jsonify({'projects': list(user_projects.values())})

@app.route('/api/v1/projects/<project_id>', methods=['GET'])
@require_api_key
def api_get_project(project_id):
    """Get project details"""
    projects = load_projects()
    if project_id not in projects:
        return jsonify({'error': 'Project not found'}), 404

    project = projects[project_id]
    if project.get('owner_id') != request.api_user['id']:
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'project': {
            'id': project_id,
            'name': project.get('name'),
            'url': project.get('url'),
            'specs': project.get('test_specs', []),
            'created_at': project.get('created_at')
        }
    })

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
