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
            name: 'EXECUTION_MODE',
            choices: ['DOCKER', 'LOCAL_CHROME'],
            description: 'Run tests in Docker container or with local Chrome'
        )
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
                echo "║   Execution Mode: ${params.EXECUTION_MODE}    ║"
                echo "╚════════════════════════════════════════╝"
                checkout scm
            }
        }
        
        stage('Setup Docker') {
            when {
                expression { params.EXECUTION_MODE == 'DOCKER' }
            }
            steps {
                script {
                    echo "🐳 Setting up Docker environment..."
                    sh '''
                        docker pull selenium/standalone-chrome:latest
                        docker run -d \
                            --name selenium-chrome-${BUILD_NUMBER} \
                            --shm-size=2g \
                            -p 4444:4444 \
                            selenium/standalone-chrome:latest
                        sleep 5
                        docker ps | grep selenium-chrome-${BUILD_NUMBER}
                    '''
                }
            }
        }
        
        stage('Setup Python') {
            steps {
                script {
                    echo "📦 Installing Python dependencies..."
                    sh '''
                        # Install python packages globally for Docker mode
                        pip3 install --user selenium==4.16.0 requests==2.31.0 webdriver-manager==4.0.1
                    '''
                }
            }
        }
        
        stage('Create and Run Tests') {
            steps {
                script {
                    writeFile file: 'run_tests.py', text: '''
import os
import sys
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    if os.environ.get('EXECUTION_MODE') == 'DOCKER':
        from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
        return webdriver.Remote(
            command_executor='http://localhost:4444/wd/hub',
            desired_capabilities=DesiredCapabilities.CHROME,
            options=chrome_options
        )
    else:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=chrome_options)

def test_site(name, url):
    results = {"site_name": name, "site_url": url, "passed": 0, "failed": 0, "test_results": []}
    
    try:
        driver = get_driver()
        driver.get(url)
        results["test_results"].append({"test": "Page Load", "status": "PASS"})
        results["passed"] += 1
        
        if "NBC" in driver.title or "News" in driver.title:
            results["test_results"].append({"test": "Title Check", "status": "PASS"})
            results["passed"] += 1
        else:
            results["test_results"].append({"test": "Title Check", "status": "FAIL"})
            results["failed"] += 1
        
        driver.quit()
    except Exception as e:
        results["test_results"].append({"test": "Error", "status": "FAIL", "details": str(e)})
        results["failed"] += 1
    
    results["total_tests"] = results["passed"] + results["failed"]
    return results

# Main
sites = {"New York": "https://www.nbcnewyork.com/"}
if os.environ.get('SITES_TO_TEST') == 'ALL_SITES':
    sites.update({
        "Los Angeles": "https://www.nbclosangeles.com/",
        "Chicago": "https://www.nbcchicago.com/",
        "Philadelphia": "https://www.nbcphiladelphia.com/"
    })

start_time = datetime.now()
all_results = []

for site_name, site_url in sites.items():
    print(f"Testing {site_name}...")
    all_results.append(test_site(site_name, site_url))

duration = (datetime.now() - start_time).total_seconds()

summary = {
    "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
    "duration_seconds": round(duration, 2),
    "total_sites": len(all_results),
    "sites_passed": sum(1 for r in all_results if r["failed"] == 0),
    "sites_failed": sum(1 for r in all_results if r["failed"] > 0),
    "total_tests": sum(r["total_tests"] for r in all_results),
    "total_passed": sum(r["passed"] for r in all_results),
    "total_failed": sum(r["failed"] for r in all_results),
    "sites": all_results
}

with open('test_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)

# HTML Report
html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NBC Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ text-align: center; color: #333; }}
        .status {{ text-align: center; font-size: 24px; margin: 20px 0; }}
        .pass {{ color: #4CAF50; font-weight: bold; }}
        .fail {{ color: #f44336; font-weight: bold; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 30px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #f0f0f0; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #e0e0e0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>NBC Multi-Site Test Report</h1>
        <div class="status {'pass' if summary['sites_failed'] == 0 else 'fail'}">
            {'✅ ALL TESTS PASSED' if summary['sites_failed'] == 0 else '❌ TESTS FAILED'}
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{summary['total_sites']}</div>
                <div>Sites Tested</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['sites_passed']}</div>
                <div>Sites Passed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{summary['sites_failed']}</div>
                <div>Sites Failed</div>
            </div>
        </div>
        
        <table>
            <tr><th>Site</th><th>Tests</th><th>Passed</th><th>Failed</th><th>Status</th></tr>
"""

for site in summary['sites']:
    status = "✅" if site['failed'] == 0 else "❌"
    html += f"<tr><td>{site['site_name']}</td><td>{site['total_tests']}</td><td>{site['passed']}</td><td>{site['failed']}</td><td>{status}</td></tr>"

html += f"""
        </table>
        <p style="text-align: center; margin-top: 30px; color: #666;">
            Build #{os.environ.get('BUILD_NUMBER', 'N/A')} | Duration: {duration:.2f}s | {start_time.strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>
"""

with open('multi_site_report.html', 'w') as f:
    f.write(html)

print(f"Tests Complete: {summary['sites_passed']}/{summary['total_sites']} sites passed")
sys.exit(0 if summary['sites_failed'] == 0 else 1)
'''
                    
                    // Run the tests
                    def exitCode = sh(
                        script: """
                            export EXECUTION_MODE="${params.EXECUTION_MODE}"
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
                archiveArtifacts artifacts: 'multi_site_report.html, test_summary.json', 
                                 allowEmptyArchive: true
                
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: '.',
                    reportFiles: 'multi_site_report.html',
                    reportName: 'NBC Multi-Site Report',
                    reportTitles: 'Test Results'
                ])
            }
        }
        
        stage('Send Slack Notification') {
            steps {
                script {
                    def summary = readJSON file: 'test_summary.json'
                    def status = summary.sites_failed == 0 ? '✅ PASSED' : '❌ FAILED'
                    def color = summary.sites_failed == 0 ? 'good' : 'danger'
                    
                    try {
                        slackSend(
                            channel: env.SLACK_CHANNEL,
                            color: color,
                            attachments: [[
                                title: "NBC Test Results - Build #${BUILD_NUMBER}",
                                title_link: "${HTML_REPORT_URL}",
                                text: "${status}",
                                fields: [
                                    [title: "Sites", value: "${summary.sites_passed}/${summary.total_sites} passed", short: true],
                                    [title: "Tests", value: "${summary.total_passed}/${summary.total_tests} passed", short: true],
                                    [title: "Duration", value: "${summary.duration_seconds}s", short: true],
                                    [title: "Mode", value: "${params.EXECUTION_MODE}", short: true]
                                ],
                                footer: "NBC Automation",
                                ts: System.currentTimeMillis() / 1000
                            ]]
                        )
                    } catch (Exception e) {
                        echo "Slack notification failed: ${e.message}"
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                if (params.EXECUTION_MODE == 'DOCKER') {
                    sh "docker stop selenium-chrome-${BUILD_NUMBER} || true"
                    sh "docker rm selenium-chrome-${BUILD_NUMBER} || true"
                }
                echo "Pipeline completed with status: ${currentBuild.result}"
            }
        }
    }
} 
