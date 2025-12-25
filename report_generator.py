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
import xml.etree.ElementTree as ET


def generate_report(data: Dict, output_dir: Path, project: Dict = None) -> str:
    """Generate a comprehensive HTML report with glassmorphic design."""

    print(f"\n[DEBUG] ===== REPORT GENERATION STARTED =====")
    print(f"[DEBUG] Data keys: {list(data.keys())}")
    print(f"[DEBUG] Results count: {len(data.get('results', []))}")
    print(f"[DEBUG] Screenshots count: {len(data.get('screenshots', []))}")

    # Check first result structure
    results = data.get('results', [])
    if results:
        first_result = results[0]
        print(f"[DEBUG] First result keys: {list(first_result.keys())}")
        print(f"[DEBUG] First result has steps: {'steps' in first_result}")
        if 'steps' in first_result:
            steps = first_result.get('steps', [])
            print(f"[DEBUG] First result steps count: {len(steps)}")
            if steps:
                print(f"[DEBUG] First step structure: {list(steps[0].keys()) if steps else 'No steps'}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy screenshots to report directory
    screenshots_dir = output_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    # Build screenshot lookup by filename
    screenshot_lookup = {}
    print(f"\n[DEBUG] ===== SCREENSHOT PROCESSING =====")
    print(f"[DEBUG] Total screenshots in data: {len(data.get('screenshots', []))}")
    print(f"[DEBUG] Total results in data: {len(data.get('results', []))}")

    for ss in data.get('screenshots', []):
        src_path = ss.get('path', '')
        if not src_path:
            print(f"[WARNING] Screenshot entry has no path: {ss}")
            continue

        src = Path(src_path)
        if src.exists():
            dst = screenshots_dir / src.name
            try:
                shutil.copy(src, dst)
                # Store multiple path variations to ensure matching
                screenshot_lookup[src_path] = src.name  # Original path
                screenshot_lookup[str(src)] = src.name  # Path object as string
                screenshot_lookup[str(src.resolve())] = src.name  # Absolute resolved path
                print(f"[DEBUG] ✓ Copied screenshot: {src.name}")
                print(f"[DEBUG]   - Registered paths: {src_path}, {str(src)}")
            except Exception as e:
                print(f"[WARNING] Failed to copy screenshot {src}: {e}")
        else:
            print(f"[WARNING] Screenshot file not found: {src} (from path: {src_path})")

    print(f"[DEBUG] Total screenshots copied: {len(screenshot_lookup)}")
    print(f"[DEBUG] Screenshot lookup keys (first 3): {list(screenshot_lookup.keys())[:3] if screenshot_lookup else 'None'}")
    print(f"[DEBUG] Screenshot lookup values (first 3): {list(screenshot_lookup.values())[:3] if screenshot_lookup else 'None'}")
    print(f"[DEBUG] ===== END SCREENSHOT PROCESSING =====\n")

    # Calculate summary
    results = data.get('results', [])
    total_tests = len(results)
    passed = sum(1 for r in results if r.get('status') == 'passed')
    failed = sum(1 for r in results if r.get('status') == 'failed')
    incomplete = sum(1 for r in results if r.get('status') == 'incomplete')

    issues = data.get('issues', [])
    screenshots = data.get('screenshots', [])
    suggestions = data.get('suggestions', [])

    # Filter to only relevant issues (observed during test)
    relevant_issues = [i for i in issues if i.get('type') in ['observed_issue', 'action_error', 'dropdown_error', 'action_failed']]

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
            cursor: pointer;
            transition: background 0.2s;
        }}

        .step-card:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}

        .step-card.success {{
            border-left-color: var(--success);
        }}

        .step-card.failed {{
            border-left-color: var(--error);
        }}

        .step-screenshots {{
            display: none;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }}

        .step-screenshots.active {{
            display: grid;
        }}

        .step-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .expand-icon {{
            transition: transform 0.3s;
            font-size: 1.2em;
        }}

        .expanded .expand-icon {{
            transform: rotate(90deg);
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
                            <img src="/static/images/alphatest-logo.svg" alt="AlphaTest Logo" style="width: 48px; height: 48px;">
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

            <!-- Compliance & Performance Metrics -->
            {generate_metrics_dashboard(data)}

            <!-- Test Results with Step-by-Step -->
            {generate_test_results_html(results, screenshot_lookup)}

            <!-- Issues Found -->
            {generate_issues_html(relevant_issues)}

            <!-- Improvement Suggestions -->
            {generate_suggestions_html(suggestions)}

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

        function toggleStep(stepId) {{
            const stepEl = document.getElementById(stepId);
            const card = stepEl.parentElement;

            if (stepEl.classList.contains('active')) {{
                stepEl.classList.remove('active');
                card.classList.remove('expanded');
            }} else {{
                stepEl.classList.add('active');
                card.classList.add('expanded');
            }}
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
        }});

        function downloadPDF() {{
            const element = document.getElementById('report-content');

            // Expand all step screenshots before PDF generation
            const allStepScreenshots = document.querySelectorAll('.step-screenshots');
            const allStepCards = document.querySelectorAll('.step-card');
            allStepScreenshots.forEach(ss => ss.classList.add('active'));
            allStepCards.forEach(card => card.classList.add('expanded'));

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
                // Collapse screenshots after PDF is generated
                allStepScreenshots.forEach(ss => ss.classList.remove('active'));
                allStepCards.forEach(card => card.classList.remove('expanded'));
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

    # Generate JUnit XML for CI/CD integration
    junit_path = output_dir / "junit.xml"
    generate_junit_xml(data, junit_path, project)
    print(f"[INFO] JUnit XML report generated: {junit_path}")

    return str(report_path)


def generate_metrics_dashboard(data: Dict) -> str:
    """Generate HTML for compliance and performance metrics dashboard."""
    # Extract metrics from data
    accessibility = data.get('accessibility_results', {})
    security = data.get('security_results', {})
    performance = data.get('performance_results', {})

    # If no metrics available, return empty
    if not accessibility and not security and not performance:
        return ""

    html = '''
    <section class="glass-card p-6 mb-8">
        <h2 class="text-xl font-bold text-white mb-6 flex items-center space-x-3">
            <svg class="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span>Compliance & Performance Dashboard</span>
        </h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
    '''

    # Accessibility Section
    if accessibility:
        wcag_level = accessibility.get('wcag_level', 'Unknown')
        total_violations = accessibility.get('total_violations', 0)
        critical_count = accessibility.get('critical_count', 0)
        serious_count = accessibility.get('serious_count', 0)

        # Determine color based on compliance
        if 'Non-compliant' in wcag_level or critical_count > 0:
            level_color = 'text-red-400'
            border_color = 'border-red-500/30'
        elif 'AA' in wcag_level and 'issues' not in wcag_level:
            level_color = 'text-green-400'
            border_color = 'border-green-500/30'
        else:
            level_color = 'text-yellow-400'
            border_color = 'border-yellow-500/30'

        html += f'''
            <div class="bg-white/5 border {border_color} rounded-lg p-4">
                <div class="flex items-center space-x-3 mb-3">
                    <svg class="w-5 h-5 {level_color}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                    <h3 class="font-semibold text-white">Accessibility</h3>
                </div>
                <div class="space-y-2">
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">WCAG Compliance</span>
                        <span class="{level_color} font-semibold">{wcag_level}</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">Total Violations</span>
                        <span class="text-white font-semibold">{total_violations}</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">Critical Issues</span>
                        <span class="text-red-400 font-semibold">{critical_count}</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">Serious Issues</span>
                        <span class="text-orange-400 font-semibold">{serious_count}</span>
                    </div>
                </div>
            </div>
        '''

    # Security Section
    if security:
        present = security.get('present', [])
        missing = security.get('missing', [])
        compliance_pct = security.get('compliance_percentage', 0)

        # Determine color based on compliance
        if compliance_pct >= 80:
            compliance_color = 'text-green-400'
            border_color = 'border-green-500/30'
        elif compliance_pct >= 50:
            compliance_color = 'text-yellow-400'
            border_color = 'border-yellow-500/30'
        else:
            compliance_color = 'text-red-400'
            border_color = 'border-red-500/30'

        html += f'''
            <div class="bg-white/5 border {border_color} rounded-lg p-4">
                <div class="flex items-center space-x-3 mb-3">
                    <svg class="w-5 h-5 {compliance_color}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <h3 class="font-semibold text-white">Security Headers</h3>
                </div>
                <div class="space-y-2">
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">Compliance</span>
                        <span class="{compliance_color} font-semibold">{compliance_pct:.0f}%</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">Present Headers</span>
                        <span class="text-green-400 font-semibold">{len(present)}</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">Missing Headers</span>
                        <span class="text-red-400 font-semibold">{len(missing)}</span>
                    </div>
                    <div class="text-xs text-slate-500 mt-2">
                        Missing: {', '.join(missing[:3]) if missing else 'None'}{'...' if len(missing) > 3 else ''}
                    </div>
                </div>
            </div>
        '''

    # Performance Section
    if performance:
        scores = performance.get('scores', {})
        perf_score = scores.get('performance', 0) * 100
        accessibility_score = scores.get('accessibility', 0) * 100
        best_practices_score = scores.get('bestPractices', 0) * 100
        seo_score = scores.get('seo', 0) * 100
        grade = performance.get('performanceGrade', 'Unknown')

        # Determine color based on grade
        if perf_score >= 90:
            grade_color = 'text-green-400'
            border_color = 'border-green-500/30'
        elif perf_score >= 50:
            grade_color = 'text-yellow-400'
            border_color = 'border-yellow-500/30'
        else:
            grade_color = 'text-red-400'
            border_color = 'border-red-500/30'

        # Core Web Vitals
        cwv = performance.get('coreWebVitals', {})
        lcp = cwv.get('lcp', 0)
        cls = cwv.get('cls', 0)
        fcp = cwv.get('fcp', 0)

        html += f'''
            <div class="bg-white/5 border {border_color} rounded-lg p-4">
                <div class="flex items-center space-x-3 mb-3">
                    <svg class="w-5 h-5 {grade_color}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <h3 class="font-semibold text-white">Performance</h3>
                </div>
                <div class="space-y-2">
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">Overall Grade</span>
                        <span class="{grade_color} font-semibold">{grade}</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">Performance</span>
                        <span class="text-white font-semibold">{perf_score:.0f}/100</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">Best Practices</span>
                        <span class="text-white font-semibold">{best_practices_score:.0f}/100</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-400 text-sm">SEO</span>
                        <span class="text-white font-semibold">{seo_score:.0f}/100</span>
                    </div>
                    <div class="text-xs text-slate-500 mt-2 space-y-1">
                        <div>LCP: {lcp:.0f}ms | CLS: {cls:.3f}</div>
                        <div>FCP: {fcp:.0f}ms</div>
                    </div>
                </div>
            </div>
        '''

    html += '''
        </div>
    </section>
    '''

    return html


def generate_test_results_html(results: List[Dict], screenshot_lookup: Dict) -> str:
    """Generate HTML for test results with step-by-step screenshots."""
    if not results:
        return '''
        <div class="glass-card p-8 mb-8">
            <p class="text-slate-400 text-center">No tests run yet.</p>
        </div>'''

    print(f"\n[DEBUG] ===== TEST RESULTS HTML GENERATION =====")
    print(f"[DEBUG] Number of test results: {len(results)}")
    print(f"[DEBUG] Screenshot lookup has {len(screenshot_lookup)} entries")

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

        print(f"[DEBUG] Test {test_idx + 1}: {display_name}")
        print(f"[DEBUG]   - Status: {status}")
        print(f"[DEBUG]   - Steps: {len(steps)}")

        # Debug: Check if steps have screenshot data
        if steps:
            first_step = steps[0]
            print(f"[DEBUG]   - First step keys: {list(first_step.keys())}")
            print(f"[DEBUG]   - First step has screenshot_before: {'screenshot_before' in first_step}")
            print(f"[DEBUG]   - First step has screenshot_after: {'screenshot_after' in first_step}")

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
                <h3 class="font-semibold text-slate-300 mb-4 flex items-center space-x-3">
                    <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                    <span>Test Steps</span>
                </h3>
                <div class="space-y-2">
        """

        for step_idx, step in enumerate(steps):
            step_num = step.get('step', 0)
            thinking = step.get('thinking', '')
            action = step.get('action', {})
            step_result = step.get('result', {})
            success = step_result.get('success', False)

            # Get screenshots for this step
            before_shot = step.get('screenshot_before', '')
            after_shot = step.get('screenshot_after', '')

            # Try multiple path formats for screenshot lookup
            before_filename = ''
            if before_shot:
                before_filename = screenshot_lookup.get(before_shot, '')
                if not before_filename:
                    # Try as Path object string
                    before_filename = screenshot_lookup.get(str(Path(before_shot)), '')
                if not before_filename:
                    # Try resolved absolute path
                    try:
                        before_filename = screenshot_lookup.get(str(Path(before_shot).resolve()), '')
                    except:
                        pass

            after_filename = ''
            if after_shot:
                after_filename = screenshot_lookup.get(after_shot, '')
                if not after_filename:
                    # Try as Path object string
                    after_filename = screenshot_lookup.get(str(Path(after_shot)), '')
                if not after_filename:
                    # Try resolved absolute path
                    try:
                        after_filename = screenshot_lookup.get(str(Path(after_shot).resolve()), '')
                    except:
                        pass

            # Debug logging
            has_before = bool(before_shot)
            has_after = bool(after_shot)
            print(f"[DEBUG]   Step {step_num}: before={has_before}, after={has_after}")

            if before_shot:
                print(f"[DEBUG]     - Before path from step: {before_shot}")
                if not before_filename:
                    print(f"[WARNING]     - Before screenshot NOT FOUND in lookup!")
                    print(f"[WARNING]     - Available paths: {list(screenshot_lookup.keys())[:2]}")
                else:
                    print(f"[DEBUG]     - Before filename resolved: {before_filename}")

            if after_shot:
                print(f"[DEBUG]     - After path from step: {after_shot}")
                if not after_filename:
                    print(f"[WARNING]     - After screenshot NOT FOUND in lookup!")
                    print(f"[WARNING]     - Available paths: {list(screenshot_lookup.keys())[:2]}")
                else:
                    print(f"[DEBUG]     - After filename resolved: {after_filename}")

            step_status = 'success' if success else 'failed'
            action_type = action.get('type', 'analyze')
            action_desc = step_result.get('message', '')

            step_id = f"step-{test_idx}-{step_idx}"
            has_screenshots = bool(before_filename or after_filename)

            # Build onclick handler without backslashes in f-string
            if has_screenshots:
                onclick_handler = f"toggleStep('{step_id}')"
                expanded_class = ""
                expand_icon_html = '<span class="expand-icon text-green-400">►</span>'
            else:
                onclick_handler = "return false"
                expanded_class = "expanded"
                expand_icon_html = ""

            html += f"""
                    <div class="step-card {step_status} {expanded_class}"
                         onclick="{onclick_handler}">
                        <div class="step-header">
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
                            {expand_icon_html}
                        </div>
            """

            # Add expandable screenshots section
            if has_screenshots:
                html += f'''
                        <div class="step-screenshots" id="{step_id}">
                '''
                if before_filename:
                    html += f'''
                            <div>
                                <p class="text-xs text-slate-500 mb-2">Before Action</p>
                                <img src="screenshots/{before_filename}" alt="Before"
                                    class="screenshot-img w-full border border-white/10 rounded-lg"
                                    onclick="event.stopPropagation(); openModal('screenshots/{before_filename}')">
                            </div>
                    '''
                if after_filename:
                    html += f'''
                            <div>
                                <p class="text-xs text-slate-500 mb-2">After Action</p>
                                <img src="screenshots/{after_filename}" alt="After"
                                    class="screenshot-img w-full border border-white/10 rounded-lg"
                                    onclick="event.stopPropagation(); openModal('screenshots/{after_filename}')">
                            </div>
                    '''
                html += '''
                        </div>
                '''

            html += """
                    </div>
            """

        html += """
                </div>
            </div>
        </section>
        """

    print(f"[DEBUG] ===== END TEST RESULTS HTML GENERATION =====\n")
    return html


def generate_issues_html(issues: List[Dict]) -> str:
    """Generate HTML for issues section."""
    if not issues:
        return """
        <section class="glass-card p-8 mb-8">
            <h2 class="text-xl font-bold text-white mb-4 flex items-center space-x-3">
                <svg class="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>No Issues Detected</span>
            </h2>
            <p class="text-slate-400">All checks passed without issues.</p>
        </section>
        """

    html = """
    <section class="glass-card p-6 mb-8">
        <h2 class="text-xl font-bold text-white mb-6 flex items-center space-x-3">
            <svg class="w-6 h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
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


def generate_suggestions_html(suggestions: List[Dict]) -> str:
    """Generate HTML for improvement suggestions section."""
    if not suggestions:
        return ""

    html = """
    <section class="glass-card p-6 mb-8">
        <h2 class="text-xl font-bold text-white mb-6 flex items-center space-x-3">
            <svg class="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            <span>Improvement Suggestions</span>
        </h2>
        <div class="space-y-3">
    """

    for suggestion in suggestions:
        message = suggestion.get('message', '')
        url = suggestion.get('url', '')

        html += f"""
        <div class="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
            <div class="flex items-start space-x-3">
                <svg class="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <div class="flex-1 min-w-0">
                    <p class="font-medium text-blue-400">{message}</p>
                    {f'<p class="text-slate-500 text-sm mt-1 truncate">On: {url}</p>' if url else ''}
                </div>
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
        <h2 class="text-xl font-bold text-white mb-6 flex items-center space-x-3">
            <svg class="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
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


def generate_junit_xml(data: Dict, output_path: Path, project: Dict = None) -> str:
    """Generate JUnit XML report for CI/CD integration.

    JUnit XML format is compatible with:
    - Jenkins
    - GitLab CI
    - GitHub Actions
    - CircleCI
    - Azure DevOps
    - TeamCity
    """
    results = data.get('results', [])
    project_name = project.get('name', 'AlphaTest') if project else 'AlphaTest'

    # Calculate totals
    total_tests = len(results)
    failures = sum(1 for r in results if r.get('status') == 'failed')
    errors = sum(1 for r in results if r.get('status') == 'incomplete')
    skipped = 0

    # Calculate total time (sum of all test durations)
    total_time = sum(r.get('duration', 0) for r in results)

    # Create root element
    testsuite = ET.Element('testsuite', {
        'name': project_name,
        'tests': str(total_tests),
        'failures': str(failures),
        'errors': str(errors),
        'skipped': str(skipped),
        'time': f"{total_time:.2f}",
        'timestamp': datetime.now().isoformat()
    })

    # Add test cases
    for result in results:
        test_name = result.get('spec_name', result.get('command', 'Unknown test'))
        status = result.get('status', 'unknown')
        duration = result.get('duration', 0)
        steps = result.get('steps', [])

        # Create testcase element
        testcase = ET.SubElement(testsuite, 'testcase', {
            'name': test_name,
            'classname': f'{project_name}.UAT',
            'time': f"{duration:.2f}"
        })

        # Add failure/error details
        if status == 'failed':
            failure = ET.SubElement(testcase, 'failure', {
                'message': f'Test failed after {len(steps)} steps',
                'type': 'AssertionError'
            })

            # Add failure details from steps
            failure_details = []
            for step in steps:
                if not step.get('result', {}).get('success', True):
                    step_num = step.get('step', 0)
                    thinking = step.get('thinking', '')
                    result_msg = step.get('result', {}).get('message', '')
                    failure_details.append(f"Step {step_num}: {thinking}\nResult: {result_msg}")

            failure.text = '\n\n'.join(failure_details) if failure_details else 'Test failed'

        elif status == 'incomplete':
            error = ET.SubElement(testcase, 'error', {
                'message': f'Test incomplete after {len(steps)} steps',
                'type': 'TestIncompleteError'
            })
            error.text = f'Test did not complete successfully. Last step: {len(steps)}'

        # Add system-out with step details
        system_out = ET.SubElement(testcase, 'system-out')
        step_output = []
        for step in steps:
            step_num = step.get('step', 0)
            thinking = step.get('thinking', '')
            action = step.get('action', {})
            action_type = action.get('type', 'analyze')
            step_output.append(f"[Step {step_num}] {action_type}: {thinking[:100]}")

        system_out.text = '\n'.join(step_output)

    # Create tree and write to file
    tree = ET.ElementTree(testsuite)
    ET.indent(tree, space='  ')  # Pretty print (Python 3.9+)

    output_path = Path(output_path)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)

    return str(output_path)


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
