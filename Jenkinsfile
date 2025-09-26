pipeline {
    agent { label 'QA-Agent' }
    
    environment {
        SLACK_CHANNEL = '#automation_test_results'
        VENV = "${WORKSPACE}/venv"
        HTML_REPORT_URL = "${BUILD_URL}NBC_20Multi-Site_20Report/"
    }
    
    options {
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }
    
    parameters {
        choice(
            name: 'TEST_SCOPE',
            choices: ['NBC_NEW_YORK', 'TOP_5_SITES', 'ALL_SITES'],
            description: 'Testing scope'
        )
    }
    
    stages {
        stage('Setup') {
            steps {
                script {
                    sh '''
                        python3 -m venv ${VENV}
                        . ${VENV}/bin/activate
                        pip install selenium==4.16.0
                        pip install webdriver-manager==4.0.1
                        pip install requests==2.31.0
                    '''
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    // Create test that works with your Chromium installation
                    writeFile file: 'test_nbc.py', text: '''
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Configure for Chromium (not Chrome)
options = Options()
options.binary_location = '/usr/bin/chromium-browser'
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')

# Test NBC sites
sites = {
    "NBC New York": "https://www.nbcnewyork.com/",
    "NBC Los Angeles": "https://www.nbclosangeles.com/",
    "NBC Chicago": "https://www.nbcchicago.com/",
    "NBC Philadelphia": "https://www.nbcphiladelphia.com/",
    "NBC Boston": "https://www.nbcboston.com/"
}

results = {
    "timestamp": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
    "sites_tested": 0,
    "sites_passed": 0,
    "sites_failed": 0,
    "details": []
}

# Use system chromedriver
service = Service('/usr/bin/chromedriver')

for name, url in list(sites.items())[:1]:  # Test 1 site for now
    try:
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        title = driver.title
        driver.quit()
        
        results["sites_tested"] += 1
        results["sites_passed"] += 1
        results["details"].append({
            "site": name,
            "status": "PASSED",
            "title": title
        })
        print(f"✅ {name}: PASSED")
        
    except Exception as e:
        results["sites_tested"] += 1
        results["sites_failed"] += 1
        results["details"].append({
            "site": name,
            "status": "FAILED",
            "error": str(e)[:100]
        })
        print(f"❌ {name}: FAILED - {str(e)[:50]}")

# Save results
with open("test_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Generate HTML report
html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NBC Digital Properties Test Report</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric {{ font-size: 2em; font-weight: bold; }}
        .label {{ color: #666; font-size: 0.9em; }}
        .passed {{ color: #10b981; }}
        .failed {{ color: #ef4444; }}
        table {{
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        th {{ 
            background: #f9fafb;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{ 
            padding: 12px;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NBC Digital Properties Test Report</h1>
        <p>Executive Dashboard - {results["timestamp"]}</p>
    </div>
    
    <div class="summary">
        <div class="card">
            <div class="metric">{results["sites_tested"]}</div>
            <div class="label">SITES TESTED</div>
        </div>
        <div class="card">
            <div class="metric passed">{results["sites_passed"]}</div>
            <div class="label">OPERATIONAL</div>
        </div>
        <div class="card">
            <div class="metric failed">{results["sites_failed"]}</div>
            <div class="label">ISSUES DETECTED</div>
        </div>
        <div class="card">
            <div class="metric">{int(results["sites_passed"]/max(results["sites_tested"],1)*100)}%</div>
            <div class="label">SUCCESS RATE</div>
        </div>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>Property</th>
                <th>Status</th>
                <th>Details</th>
            </tr>
        </thead>
        <tbody>
"""

for detail in results["details"]:
    status_color = "passed" if detail["status"] == "PASSED" else "failed"
    html += f"""
            <tr>
                <td>{detail["site"]}</td>
                <td><span class="{status_color}">● {detail["status"]}</span></td>
                <td>{detail.get("title", detail.get("error", ""))}</td>
            </tr>
    """

html += """
        </tbody>
    </table>
</body>
</html>
"""

with open("multi_site_report.html", "w") as f:
    f.write(html)

print(f"\\nSummary: {results['sites_passed']}/{results['sites_tested']} sites operational")
'''
                    
                    sh '''
                        . ${VENV}/bin/activate
                        python test_nbc.py
                    '''
                }
            }
        }
        
        stage('Archive Reports') {
            steps {
                archiveArtifacts artifacts: 'multi_site_report.html, test_results.json', 
                                 allowEmptyArchive: true
                
                publishHTML([
                    reportDir: '.',
                    reportFiles: 'multi_site_report.html',
                    reportName: 'NBC Multi-Site Report'
                ])
            }
        }
        
        stage('Send Slack Notification') {
            steps {
                script {
                    def results = readJSON file: 'test_results.json'
                    def status = results.sites_failed == 0 ? 'OPERATIONAL' : 'ISSUES DETECTED'
                    def emoji = results.sites_failed == 0 ? '🟢' : '🔴'
                    def color = results.sites_failed == 0 ? 'good' : 'danger'
                    
                    // Professional Slack message
                    def message = """
╔════════════════════════════════════════╗
║     NBC DIGITAL PROPERTIES STATUS      ║
╚════════════════════════════════════════╝

${emoji} Status: ${status}
📅 ${results.timestamp}
🔢 Build: #${BUILD_NUMBER}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Properties Tested:    ${results.sites_tested}
Fully Operational:    ${results.sites_passed}
Requiring Attention:  ${results.sites_failed}
System Health:        ${(results.sites_passed/results.sites_tested*100).intValue()}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                    
                    // Add site details
                    if (results.details) {
                        message += "PROPERTY STATUS\\n"
                        message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
                        results.details.each { site ->
                            def icon = site.status == "PASSED" ? "✅" : "❌"
                            message += "${icon} ${site.site}\\n"
                        }
                        message += "\\n"
                    }
                    
                    message += """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Detailed Report: ${HTML_REPORT_URL}
📋 Build Details: ${BUILD_URL}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NBC Quality Assurance Team
Ensuring Digital Excellence
"""
                    
                    slackSend(
                        channel: env.SLACK_CHANNEL,
                        color: color,
                        message: message
                    )
                }
            }
        }
    }
    
    post {
        always {
            sh "rm -rf ${VENV}"
        }
    }
}
