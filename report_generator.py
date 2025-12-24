#!/usr/bin/env python3
"""
AlphaTest v2 - Report Generator
Creates beautiful HTML reports with glassmorphic design and PDF export support.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import shutil


def generate_report(data: Dict, output_dir: Path, project: Dict = None) -> str:
    """Generate a comprehensive HTML report with glassmorphic design."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy screenshots to report directory
    screenshots_dir = output_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    # Build screenshot lookup by filename
    screenshot_lookup = {}
    for ss in data.get('screenshots', []):
        src = Path(ss['path'])
        if src.exists():
            dst = screenshots_dir / src.name
            try:
                shutil.copy(src, dst)
                screenshot_lookup[ss['path']] = src.name
            except:
                pass

    # Calculate summary
    results = data.get('results', [])
    total_tests = len(results)
    passed = sum(1 for r in results if r.get('status') == 'passed')
    failed = sum(1 for r in results if r.get('status') == 'failed')
    incomplete = sum(1 for r in results if r.get('status') == 'incomplete')

    issues = data.get('issues', [])
    screenshots = data.get('screenshots', [])

    # Filter to only relevant issues (observed during test)
    relevant_issues = [i for i in issues if i.get('type') in ['observed_issue', 'action_error', 'dropdown_error']]

    # Generate HTML
    project_name = project.get('name', 'Test Report') if project else 'Test Report'
    project_url = project.get('url', '') if project else ''
    project_id = project.get('id', '') if project else ''

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AlphaTest Report - {project_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-500: #10b981;
            --primary-600: #059669;
            --bg-gradient-start: #0f172a;
            --bg-gradient-mid: #1e293b;
            --bg-gradient-end: #0f172a;
            --glass-bg: rgba(15, 23, 42, 0.6);
            --glass-border: rgba(255, 255, 255, 0.15);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --error: #ef4444;
        }}

        body {{
            font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, var(--bg-gradient-start) 0%, var(--bg-gradient-mid) 100%);
            background-attachment: fixed;
            min-height: 100vh;
            color: var(--text-primary);
            position: relative;
        }}

        /* Technical grid overlay */
        body::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image:
                linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            pointer-events: none;
            z-index: 0;
        }}

        .bg-pattern {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image:
                radial-gradient(circle at 20% 80%, rgba(16, 185, 129, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(16, 185, 129, 0.08) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }}

        .glass-card {{
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}

        .header-glass {{
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .btn-primary {{
            background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-600) 100%);
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
            border: none;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
            cursor: pointer;
        }}

        .btn-primary:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        }}

        .screenshot-img {{
            transition: transform 0.2s;
            cursor: pointer;
            border-radius: 8px;
        }}

        .screenshot-img:hover {{
            transform: scale(1.02);
        }}

        .step-card {{
            border-left: 3px solid rgba(255, 255, 255, 0.1);
            background: rgba(255, 255, 255, 0.03);
            border-radius: 0 8px 8px 0;
            padding: 1rem;
            margin-bottom: 0.75rem;
        }}

        .step-card.success {{
            border-left-color: var(--success);
        }}

        .step-card.failed {{
            border-left-color: var(--error);
        }}

        .modal {{
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0, 0, 0, 0.9);
            z-index: 1000;
        }}

        .modal.active {{
            display: flex;
            justify-content: center;
            align-items: center;
        }}

        .modal img {{
            max-width: 95%;
            max-height: 95%;
            object-fit: contain;
            border-radius: 8px;
        }}

        .timeline-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            flex-shrink: 0;
        }}

        .timeline-dot.success {{
            background: var(--success);
            box-shadow: 0 0 8px var(--success);
        }}

        .timeline-dot.failed {{
            background: var(--error);
            box-shadow: 0 0 8px var(--error);
        }}

        .badge {{
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
        }}

        .badge-success {{
            background: rgba(34, 197, 94, 0.15);
            color: var(--success);
            border: 1px solid rgba(34, 197, 94, 0.3);
        }}

        .badge-error {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--error);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}

        .badge-warning {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--warning);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}

        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }}

        @media print {{
            body {{
                background: white !important;
                color: #1f2937 !important;
            }}
            .glass-card, .stat-card, .header-glass {{
                background: white !important;
                border: 1px solid #e5e7eb !important;
                box-shadow: none !important;
            }}
            .btn-primary, .no-print {{
                display: none !important;
            }}
            .text-white {{
                color: #1f2937 !important;
            }}
            .text-slate-400, .text-slate-300 {{
                color: #6b7280 !important;
            }}
        }}
    </style>
</head>
<body>
    <!-- Background Pattern -->
    <div class="bg-pattern"></div>

    <!-- Content Wrapper -->
    <div class="relative z-10" id="report-content">
        <!-- Header -->
        <header class="header-glass py-8">
            <div class="container mx-auto px-6">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="flex items-center space-x-3 mb-2">
                            <span class="text-3xl">🧪</span>
                            <h1 class="text-2xl font-bold text-white">AlphaTest Report</h1>
                        </div>
                        <p class="text-green-300 font-medium">{project_name}</p>
                        <p class="text-slate-400 text-sm">{project_url}</p>
                    </div>
                    <div class="text-right">
                        <p class="text-slate-400 text-sm">Generated</p>
                        <p class="font-semibold text-white">{datetime.now().strftime('%B %d, %Y')}</p>
                        <p class="text-slate-400 text-sm">{datetime.now().strftime('%I:%M %p')}</p>
                        <button onclick="downloadPDF()" class="btn-primary mt-4 no-print flex items-center space-x-2">
                            <span>📄</span>
                            <span>Download PDF</span>
                        </button>
                    </div>
                </div>
            </div>
        </header>

        <main class="container mx-auto px-6 py-8">
            <!-- Summary Cards -->
            <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                <div class="stat-card">
                    <div class="text-3xl font-bold text-white">{total_tests}</div>
                    <div class="text-slate-400 text-sm mt-1">Tests Run</div>
                </div>
                <div class="stat-card">
                    <div class="text-3xl font-bold text-green-400">{passed}</div>
                    <div class="text-slate-400 text-sm mt-1">Passed</div>
                </div>
                <div class="stat-card">
                    <div class="text-3xl font-bold text-red-400">{failed}</div>
                    <div class="text-slate-400 text-sm mt-1">Failed</div>
                </div>
                <div class="stat-card">
                    <div class="text-3xl font-bold text-orange-400">{incomplete}</div>
                    <div class="text-slate-400 text-sm mt-1">Incomplete</div>
                </div>
                <div class="stat-card">
                    <div class="text-3xl font-bold text-yellow-400">{len(relevant_issues)}</div>
                    <div class="text-slate-400 text-sm mt-1">Issues Found</div>
                </div>
            </div>

            <!-- Test Results with Step-by-Step -->
            {generate_test_results_html(results, screenshot_lookup)}

            <!-- Issues Found -->
            {generate_issues_html(relevant_issues)}

            <!-- All Screenshots Gallery -->
            {generate_screenshots_gallery(screenshots, screenshot_lookup)}
        </main>

        <!-- Footer -->
        <footer class="py-8 border-t border-white/10 mt-8">
            <div class="container mx-auto px-6 text-center">
                <p class="text-slate-500 text-sm">Generated by AlphaTest - AI-Powered UAT Testing</p>
                <p class="text-slate-600 text-xs mt-1">Report ID: {output_dir.name}</p>
            </div>
        </footer>
    </div>

    <!-- Screenshot Modal -->
    <div id="modal" class="modal" onclick="closeModal()">
        <img id="modal-img" src="" alt="Screenshot">
    </div>

    <script>
        function openModal(src) {{
            document.getElementById('modal-img').src = src;
            document.getElementById('modal').classList.add('active');
        }}

        function closeModal() {{
            document.getElementById('modal').classList.remove('active');
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});

        function downloadPDF() {{
            const element = document.getElementById('report-content');
            const opt = {{
                margin: [10, 10],
                filename: 'alphatest-report-{output_dir.name}.pdf',
                image: {{ type: 'jpeg', quality: 0.98 }},
                html2canvas: {{
                    scale: 2,
                    useCORS: true,
                    logging: false
                }},
                jsPDF: {{
                    unit: 'mm',
                    format: 'a4',
                    orientation: 'portrait'
                }},
                pagebreak: {{ mode: 'avoid-all', before: '.page-break' }}
            }};

            // Hide buttons during PDF generation
            document.querySelectorAll('.no-print').forEach(el => el.style.display = 'none');

            html2pdf().set(opt).from(element).save().then(() => {{
                document.querySelectorAll('.no-print').forEach(el => el.style.display = '');
            }});
        }}
    </script>
</body>
</html>"""

    # Save HTML report
    report_path = output_dir / "report.html"
    report_path.write_text(html)

    # Save JSON data
    json_path = output_dir / "report.json"
    json_data = {
        'date': datetime.now().isoformat(),
        'project': project,
        'summary': {
            'total': total_tests,
            'passed': passed,
            'failed': failed,
            'incomplete': incomplete,
            'issues': len(relevant_issues)
        },
        'results': results,
        'issues': relevant_issues,
        'screenshots': [{'filename': v, 'original': k} for k, v in screenshot_lookup.items()]
    }
    json_path.write_text(json.dumps(json_data, indent=2))

    return str(report_path)


def generate_test_results_html(results: List[Dict], screenshot_lookup: Dict) -> str:
    """Generate HTML for test results with step-by-step screenshots."""
    if not results:
        return '''
        <div class="glass-card p-8 mb-8">
            <p class="text-slate-400 text-center">No tests run yet.</p>
        </div>'''

    html = ""

    for test_idx, result in enumerate(results):
        status = result.get('status', 'unknown')
        command = result.get('command', 'Unknown test')
        spec_name = result.get('spec_name', '')
        steps = result.get('steps', [])

        # Status styling
        if status == 'passed':
            status_class = 'badge-success'
            status_icon = '✓'
            border_class = 'border-green-500'
        elif status == 'failed':
            status_class = 'badge-error'
            status_icon = '✗'
            border_class = 'border-red-500'
        else:
            status_class = 'badge-warning'
            status_icon = '?'
            border_class = 'border-yellow-500'

        display_name = spec_name if spec_name else command

        html += f"""
        <section class="glass-card mb-8 overflow-hidden">
            <div class="p-6 border-b border-white/10">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-4">
                        <span class="badge {status_class} text-sm font-bold">
                            {status_icon} {status.upper()}
                        </span>
                        <h2 class="text-xl font-bold text-white">{display_name}</h2>
                    </div>
                    <span class="text-slate-500 text-sm">{len(steps)} steps</span>
                </div>
                {f'<p class="text-slate-400 text-sm mt-2">{command}</p>' if spec_name and command != spec_name else ''}
            </div>

            <div class="p-6">
                <h3 class="font-semibold text-slate-300 mb-4 flex items-center space-x-2">
                    <span>📝</span>
                    <span>Test Steps</span>
                </h3>
                <div class="space-y-2">
        """

        for step in steps:
            step_num = step.get('step', 0)
            thinking = step.get('thinking', '')
            action = step.get('action', {})
            step_result = step.get('result', {})
            success = step_result.get('success', False)

            # Get screenshots for this step
            before_shot = step.get('screenshot_before', '')
            after_shot = step.get('screenshot_after', '')

            before_filename = screenshot_lookup.get(before_shot, '')
            after_filename = screenshot_lookup.get(after_shot, '')

            step_status = 'success' if success else 'failed'
            action_type = action.get('type', 'analyze')
            action_desc = step_result.get('message', '')

            html += f"""
                    <div class="step-card {step_status}">
                        <div class="flex items-start justify-between">
                            <div class="flex items-start space-x-3 flex-1">
                                <div class="timeline-dot {step_status} mt-1.5"></div>
                                <div class="flex-1">
                                    <div class="flex items-center space-x-2 mb-1">
                                        <span class="font-medium text-white">Step {step_num}</span>
                                        <span class="text-xs text-slate-500 px-2 py-0.5 bg-white/5 rounded">{action_type}</span>
                                    </div>
                                    <p class="text-slate-400 text-sm">{thinking[:200]}{'...' if len(thinking) > 200 else ''}</p>
                                    {f'<p class="text-slate-500 text-xs mt-1">{action_desc}</p>' if action_desc else ''}
                                </div>
                            </div>
            """

            # Add screenshot thumbnails if available
            if before_filename or after_filename:
                html += '<div class="flex space-x-2 ml-4 flex-shrink-0">'
                if before_filename:
                    html += f'''
                        <div class="text-center">
                            <img src="screenshots/{before_filename}" alt="Before"
                                class="screenshot-img w-20 h-14 object-cover border border-white/10"
                                onclick="openModal('screenshots/{before_filename}')">
                            <span class="text-xs text-slate-500">Before</span>
                        </div>
                    '''
                if after_filename:
                    html += f'''
                        <div class="text-center">
                            <img src="screenshots/{after_filename}" alt="After"
                                class="screenshot-img w-20 h-14 object-cover border border-white/10"
                                onclick="openModal('screenshots/{after_filename}')">
                            <span class="text-xs text-slate-500">After</span>
                        </div>
                    '''
                html += '</div>'

            html += """
                        </div>
                    </div>
            """

        html += """
                </div>
            </div>
        </section>
        """

    return html


def generate_issues_html(issues: List[Dict]) -> str:
    """Generate HTML for issues section."""
    if not issues:
        return """
        <section class="glass-card p-8 mb-8">
            <h2 class="text-xl font-bold text-white mb-4 flex items-center space-x-2">
                <span>✅</span>
                <span>No Issues Found</span>
            </h2>
            <p class="text-slate-400">No issues were observed during testing.</p>
        </section>
        """

    html = """
    <section class="glass-card p-6 mb-8">
        <h2 class="text-xl font-bold text-white mb-6 flex items-center space-x-2">
            <span>⚠️</span>
            <span>Issues Found During Testing</span>
        </h2>
        <div class="space-y-3">
    """

    for issue in issues:
        message = issue.get('message', '')
        severity = issue.get('severity', 'medium')
        url = issue.get('url', '')

        # Severity styling
        if severity == 'critical':
            bg_class = 'bg-red-500/10 border-red-500/30'
            icon = '🔴'
            text_class = 'text-red-400'
        elif severity == 'high':
            bg_class = 'bg-orange-500/10 border-orange-500/30'
            icon = '🟠'
            text_class = 'text-orange-400'
        else:
            bg_class = 'bg-yellow-500/10 border-yellow-500/30'
            icon = '🟡'
            text_class = 'text-yellow-400'

        html += f"""
        <div class="{bg_class} border rounded-lg p-4">
            <div class="flex items-start space-x-3">
                <span class="text-xl flex-shrink-0">{icon}</span>
                <div class="flex-1 min-w-0">
                    <p class="font-medium {text_class}">{message}</p>
                    {f'<p class="text-slate-500 text-sm mt-1 truncate">On: {url}</p>' if url else ''}
                </div>
                <span class="text-xs text-slate-500 uppercase flex-shrink-0">{severity}</span>
            </div>
        </div>
        """

    html += """
        </div>
    </section>
    """

    return html


def generate_screenshots_gallery(screenshots: List[Dict], screenshot_lookup: Dict) -> str:
    """Generate a gallery of all screenshots."""
    if not screenshots or not screenshot_lookup:
        return ""

    html = """
    <section class="glass-card p-6 mb-8">
        <h2 class="text-xl font-bold text-white mb-6 flex items-center space-x-2">
            <span>📸</span>
            <span>All Screenshots</span>
        </h2>
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
    """

    for ss in screenshots:
        path = ss.get('path', '')
        filename = screenshot_lookup.get(path, '')
        name = ss.get('name', 'Screenshot')
        step = ss.get('step', 0)

        if filename:
            html += f"""
            <div class="text-center">
                <img src="screenshots/{filename}" alt="{name}"
                    class="screenshot-img w-full h-24 object-cover border border-white/10 mb-2"
                    onclick="openModal('screenshots/{filename}')">
                <p class="text-xs text-slate-400 truncate">Step {step}</p>
            </div>
            """

    html += """
        </div>
    </section>
    """

    return html


if __name__ == "__main__":
    # Test report generation
    test_data = {
        'results': [{
            'command': 'Test login functionality',
            'status': 'passed',
            'steps': [
                {
                    'step': 1,
                    'thinking': 'Looking at login page, I can see email and password fields',
                    'action': {'type': 'type', 'selector': '#email'},
                    'result': {'success': True, 'message': 'Typed email'},
                }
            ]
        }],
        'issues': [{'type': 'observed_issue', 'message': 'Login button has low contrast', 'severity': 'medium'}],
        'screenshots': []
    }

    output = Path("./test_report")
    generate_report(test_data, output, {'name': 'Test Project', 'url': 'https://example.com'})
    print(f"Report generated at {output}/report.html")
