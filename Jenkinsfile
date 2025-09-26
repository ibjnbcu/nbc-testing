pipeline {
    agent { label 'QA-Agent' }
    
    environment {
        SLACK_CHANNEL = '#automation_test_results'
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
            name: 'SITES_TO_TEST',
            choices: ['NBC_NEW_YORK_ONLY', 'ALL_SITES'],
            description: 'Test NBC New York only or all sites'
        )
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo "╔════════════════════════════════════════╗"
                echo "║   NBC AUTOMATED TESTING PIPELINE      ║"
                echo "╚════════════════════════════════════════╝"
                checkout scm
            }
        }
        
        stage('Setup Docker') {
            steps {
                script {
                    echo "🐳 Setting up Docker with Selenium..."
                    sh '''
                        docker pull selenium/standalone-chrome:latest
                        docker stop selenium-chrome-${BUILD_NUMBER} 2>/dev/null || true
                        docker rm selenium-chrome-${BUILD_NUMBER} 2>/dev/null || true
                        docker run -d \
                            --name selenium-chrome-${BUILD_NUMBER} \
                            --shm-size=2g \
                            -p 4444:4444 \
                            selenium/standalone-chrome:latest
                        sleep 5
                    '''
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    writeFile file: 'run_tests.py', text: '''
import os
import sys
import json
from datetime import datetime

# Install packages inside the script
import subprocess
subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages", "selenium", "requests"], check=True)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    return webdriver.Remote(
        command_executor='http://localhost:4444/wd/hub',
        desired_capabilities=DesiredCapabilities.CHROME,
        options=chrome_options
    )

def test_site(name, url):
    results = {"site_name": name, "site_url": url, "passed": 0, "failed": 0}
    
    try:
        driver = get_driver()
        driver.get(url)
        results["passed"] += 1  # Page loaded
        
        if "NBC" in driver.title or "News" in driver.title:
            results["passed"] += 1  # Title check
        else:
            results["failed"] += 1
        
        driver.quit()
    except Exception as e:
        print(f"Error testing {name}: {e}")
        results["failed"] += 2
    
    return results

# Main execution
sites = {"New York": "https://www.nbcnewyork.com/"}
if os.environ.get('SITES_TO_TEST') == 'ALL_SITES':
    sites.update({
        "Los Angeles": "https://www.nbclosangeles.com/",
        "Chicago": "https://www.nbcchicago.com/",
        "Philadelphia": "https://www.nbcphiladelphia.com/"
    })

start = datetime.now()
results = []

for name, url in sites.items():
    print(f"Testing {name}...")
    results.append(test_site(name, url))

duration = (datetime.now() - start).total_seconds()

summary = {
    "duration_seconds": round(duration, 2),
    "total_sites": len(results),
    "sites_passed": sum(1 for r in results if r["failed"] == 0),
    "sites_failed": sum(1 for r in results if r["failed"] > 0),
    "total_passed": sum(r["passed"] for r in results),
    "total_failed": sum(r["failed"] for r in results),
    "sites": results
}

with open('test_summary.json', 'w') as f:
    json.dump(summary, f)

# Create HTML report
html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NBC Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>NBC Test Results - Build #{os.environ.get('BUILD_NUMBER', 'N/A')}</h1>
    <h2 class="{'pass' if summary['sites_failed'] == 0 else 'fail'}">
        {'✅ PASSED' if summary['sites_failed'] == 0 else '❌ FAILED'}
    </h2>
    <p>Sites: {summary['sites_passed']}/{summary['total_sites']} passed</p>
    <p>Tests: {summary['total_passed']}/{summary['total_passed'] + summary['total_failed']} passed</p>
    <p>Duration: {duration:.2f}s</p>
    
    <table>
        <tr><th>Site</th><th>Passed</th><th>Failed</th><th>Status</th></tr>
"""

for site in results:
    status = "✅" if site['failed'] == 0 else "❌"
    html += f"<tr><td>{site['site_name']}</td><td>{site['passed']}</td><td>{site['failed']}</td><td>{status}</td></tr>"

html += "</table></body></html>"

with open('report.html', 'w') as f:
    f.write(html)

print(f"Complete: {summary['sites_passed']}/{summary['total_sites']} sites passed")
sys.exit(0 if summary['sites_failed'] == 0 else 1)
'''
                    
                    def exitCode = sh(
                        script: """
                            export SITES_TO_TEST="${params.SITES_TO_TEST}"
                            export BUILD_NUMBER="${BUILD_NUMBER}"
                            python3 run_tests.py
                        """,
                        returnStatus: true
                    )
                    
                    currentBuild.result = exitCode == 0 ? 'SUCCESS' : 'FAILURE'
                }
            }
        }
        
        stage('Archive Reports') {
            steps {
                archiveArtifacts artifacts: 'report.html, test_summary.json', 
                                 allowEmptyArchive: true
                
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: '.',
                    reportFiles: 'report.html',
                    reportName: 'NBC Multi-Site Report'
                ])
            }
        }
        
        stage('Send Slack') {
            steps {
                script {
                    def summary = readJSON file: 'test_summary.json'
                    def status = summary.sites_failed == 0 ? '✅ PASSED' : '❌ FAILED'
                    def color = summary.sites_failed == 0 ? 'good' : 'danger'
                    
                    try {
                        slackSend(
                            channel: env.SLACK_CHANNEL,
                            color: color,
                            message: """
NBC Tests ${status} - Build #${BUILD_NUMBER}
Sites: ${summary.sites_passed}/${summary.total_sites} passed
Tests: ${summary.total_passed}/${summary.total_passed + summary.total_failed} passed
Duration: ${summary.duration_seconds}s
Report: ${HTML_REPORT_URL}
"""
                        )
                    } catch (e) {
                        echo "Slack failed: ${e.message}"
                    }
                }
            }
        }
    }
    
    post {
        always {
            sh "docker stop selenium-chrome-${BUILD_NUMBER} || true"
            sh "docker rm selenium-chrome-${BUILD_NUMBER} || true"
        }
    }
}
