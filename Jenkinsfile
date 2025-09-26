pipeline {
    agent { label 'QA-Agent' }
    
    environment {
        // Slack Configuration
        SLACK_CHANNEL = '#automation_test_results'
        
        // Python environment
        VENV = "${WORKSPACE}/venv"
        
        // Report URL
        HTML_REPORT_URL = "${BUILD_URL}NBC_20Multi-Site_20Report/"
        
        // Chrome paths to check
        CHROME_PATHS = '/usr/bin/google-chrome-stable:/usr/bin/google-chrome:/usr/bin/chromium-browser:/usr/bin/chromium:/usr/local/bin/google-chrome'
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
        choice(
            name: 'PARALLEL_WORKERS',
            choices: ['1', '3', '5'],
            description: 'Number of parallel workers'
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
        
        stage('Setup Environment') {
            parallel {
                stage('Python Setup') {
                    steps {
                        script {
                            echo "📦 Setting up Python environment..."
                            
                            sh '''
                                python3 --version
                                python3 -m venv ${VENV}
                                . ${VENV}/bin/activate
                                pip install --upgrade pip
                                pip install selenium==4.16.0
                                pip install webdriver-manager==4.0.1
                                pip install requests==2.31.0
                                pip install pytest==7.4.3
                                pip install pytest-html==4.1.1
                            '''
                        }
                    }
                }
                
                stage('Chrome/Docker Setup') {
                    steps {
                        script {
                            if (params.EXECUTION_MODE == 'DOCKER') {
                                echo "🐳 Setting up Docker environment..."
                                
                                // Check if Docker is available
                                def dockerStatus = sh(
                                    script: 'docker --version',
                                    returnStatus: true
                                )
                                
                                if (dockerStatus != 0) {
                                    error("Docker is not installed or not accessible")
                                }
                                
                                // Pull Selenium Chrome image
                                sh '''
                                    echo "Pulling Selenium Chrome Docker image..."
                                    docker pull selenium/standalone-chrome:latest
                                '''
                                
                                // Start Selenium container
                                sh '''
                                    echo "Starting Selenium Chrome container..."
                                    docker run -d \
                                        --name selenium-chrome-${BUILD_NUMBER} \
                                        --shm-size=2g \
                                        -p 4444:4444 \
                                        -p 7900:7900 \
                                        selenium/standalone-chrome:latest
                                    
                                    # Wait for container to be ready
                                    sleep 5
                                    
                                    # Check if container is running
                                    docker ps | grep selenium-chrome-${BUILD_NUMBER}
                                '''
                                
                                env.SELENIUM_URL = "http://localhost:4444"
                                env.USE_DOCKER = "true"
                                
                            } else {
                                echo "🔍 Checking local Chrome installation..."
                                
                                // More thorough Chrome detection
                                def chromeCheck = sh(
                                    script: '''
                                        # Check multiple possible Chrome locations
                                        for chrome_path in $(echo $CHROME_PATHS | tr ':' ' '); do
                                            if [ -f "$chrome_path" ]; then
                                                echo "Found Chrome at: $chrome_path"
                                                $chrome_path --version
                                                exit 0
                                            fi
                                        done
                                        
                                        # Also check with which command
                                        if which google-chrome-stable > /dev/null 2>&1; then
                                            google-chrome-stable --version
                                            exit 0
                                        elif which google-chrome > /dev/null 2>&1; then
                                            google-chrome --version
                                            exit 0
                                        elif which chromium-browser > /dev/null 2>&1; then
                                            chromium-browser --version
                                            exit 0
                                        elif which chromium > /dev/null 2>&1; then
                                            chromium --version
                                            exit 0
                                        fi
                                        
                                        echo "Chrome not found in any expected location"
                                        exit 1
                                    ''',
                                    returnStatus: true
                                )
                                
                                if (chromeCheck != 0) {
                                    echo "⚠️ Chrome not found. Attempting to use ChromeDriver Manager..."
                                    env.USE_CHROME_MANAGER = "true"
                                }
                                
                                env.USE_DOCKER = "false"
                            }
                        }
                    }
                }
            }
        }
        
        stage('Create Test Runner') {
            steps {
                script {
                    // Create an enhanced test runner that handles both Docker and local execution
                    writeFile file: 'run_nbc_tests.py', text: '''
import os
import sys
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    """Get Chrome driver based on environment configuration"""
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    
    use_docker = os.environ.get('USE_DOCKER', 'false').lower() == 'true'
    
    if use_docker:
        # Connect to Selenium Grid in Docker
        selenium_url = os.environ.get('SELENIUM_URL', 'http://localhost:4444')
        print(f"Connecting to Selenium Grid at {selenium_url}")
        
        from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
        driver = webdriver.Remote(
            command_executor=f'{selenium_url}/wd/hub',
            desired_capabilities=DesiredCapabilities.CHROME,
            options=chrome_options
        )
    else:
        # Use local Chrome with ChromeDriver Manager
        print("Using local Chrome with ChromeDriver Manager")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"Failed to initialize Chrome: {e}")
            raise
    
    return driver

def test_nbc_site(site_name, site_url):
    """Test a single NBC site"""
    results = {
        "site_name": site_name,
        "site_url": site_url,
        "test_results": [],
        "passed": 0,
        "failed": 0
    }
    
    try:
        driver = get_driver()
        
        # Test 1: Load page
        try:
            driver.get(site_url)
            results["test_results"].append({
                "test": "Page Load",
                "status": "PASS",
                "details": "Page loaded successfully"
            })
            results["passed"] += 1
        except Exception as e:
            results["test_results"].append({
                "test": "Page Load",
                "status": "FAIL",
                "details": str(e)
            })
            results["failed"] += 1
        
        # Test 2: Check title
        try:
            title = driver.title
            assert "NBC" in title or "News" in title
            results["test_results"].append({
                "test": "Title Check",
                "status": "PASS",
                "details": f"Title: {title}"
            })
            results["passed"] += 1
        except Exception as e:
            results["test_results"].append({
                "test": "Title Check",
                "status": "FAIL",
                "details": str(e)
            })
            results["failed"] += 1
        
        driver.quit()
        
    except Exception as e:
        results["test_results"].append({
            "test": "Driver Setup",
            "status": "ERROR",
            "details": str(e)
        })
        results["failed"] += 1
    
    results["total_tests"] = len(results["test_results"])
    results["success_rate"] = (results["passed"] / results["total_tests"] * 100) if results["total_tests"] > 0 else 0
    
    return results

# Main execution
if __name__ == "__main__":
    sites_to_test = os.environ.get('SITES_TO_TEST', 'NBC_NEW_YORK_ONLY')
    
    sites = {
        "New York": "https://www.nbcnewyork.com/"
    }
    
    if sites_to_test == 'ALL_SITES':
        sites.update({
            "Los Angeles": "https://www.nbclosangeles.com/",
            "Chicago": "https://www.nbcchicago.com/",
            "Philadelphia": "https://www.nbcphiladelphia.com/"
        })
    
    start_time = datetime.now()
    all_results = []
    
    for site_name, site_url in sites.items():
        print(f"\\nTesting {site_name}...")
        result = test_nbc_site(site_name, site_url)
        all_results.append(result)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Generate summary
    summary = {
        "timestamp": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": duration,
        "total_sites": len(all_results),
        "sites_passed": sum(1 for r in all_results if r["failed"] == 0),
        "sites_failed": sum(1 for r in all_results if r["failed"] > 0),
        "total_tests": sum(r["total_tests"] for r in all_results),
        "total_passed": sum(r["passed"] for r in all_results),
        "total_failed": sum(r["failed"] for r in all_results),
        "sites": all_results
    }
    
    # Save results
    with open('test_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Generate HTML report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>NBC Multi-Site Test Report</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            h1 {{ color: #333; margin: 0; }}
            .status-badge {{ display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin: 10px; }}
            .pass {{ background: #4CAF50; color: white; }}
            .fail {{ background: #f44336; color: white; }}
            .warning {{ background: #ff9800; color: white; }}
            .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0; }}
            .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
            .stat-value {{ font-size: 2em; font-weight: bold; color: #333; }}
            .stat-label {{ color: #666; margin-top: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background: #f0f0f0; padding: 12px; text-align: left; font-weight: 600; }}
            td {{ padding: 12px; border-bottom: 1px solid #e0e0e0; }}
            tr:hover {{ background: #f8f8f8; }}
            .test-pass {{ color: #4CAF50; font-weight: bold; }}
            .test-fail {{ color: #f44336; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 NBC Multi-Site Test Report</h1>
                <div class="status-badge {'pass' if summary['sites_failed'] == 0 else 'fail'}">
                    {'✅ ALL TESTS PASSED' if summary['sites_failed'] == 0 else '❌ TESTS FAILED'}
                </div>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{summary['total_sites']}</div>
                    <div class="stat-label">Sites Tested</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{summary['sites_passed']}</div>
                    <div class="stat-label">Sites Passed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{summary['sites_failed']}</div>
                    <div class="stat-label">Sites Failed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{summary['total_tests']}</div>
                    <div class="stat-label">Total Tests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{summary['total_passed']}</div>
                    <div class="stat-label">Tests Passed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{summary['total_failed']}</div>
                    <div class="stat-label">Tests Failed</div>
                </div>
            </div>
            
            <h2>📊 Detailed Results</h2>
            <table>
                <tr>
                    <th>Site</th>
                    <th>URL</th>
                    <th>Tests Run</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Success Rate</th>
                    <th>Status</th>
                </tr>
    """
    
    for site in summary['sites']:
        status = "✅ PASS" if site['failed'] == 0 else "❌ FAIL"
        status_class = "test-pass" if site['failed'] == 0 else "test-fail"
        html_content += f"""
                <tr>
                    <td><strong>{site['site_name']}</strong></td>
                    <td>{site['site_url']}</td>
                    <td>{site['total_tests']}</td>
                    <td class="test-pass">{site['passed']}</td>
                    <td class="test-fail">{site['failed']}</td>
                    <td>{site['success_rate']:.1f}%</td>
                    <td class="{status_class}">{status}</td>
                </tr>
        """
    
    html_content += f"""
            </table>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center; color: #666;">
                <p>Build: #{os.environ.get('BUILD_NUMBER', 'N/A')} | Duration: {duration:.2f}s | Generated: {start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open('multi_site_report.html', 'w') as f:
        f.write(html_content)
    
    print(f"\\n{'='*50}")
    print(f"Test Summary: {summary['sites_passed']}/{summary['total_sites']} sites passed")
    print(f"Total Tests: {summary['total_passed']}/{summary['total_tests']} passed")
    print(f"{'='*50}")
    
    sys.exit(0 if summary['sites_failed'] == 0 else 1)
'''
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    echo "🚀 Running NBC Tests (Mode: ${params.EXECUTION_MODE})..."
                    
                    def exitCode = sh(
                        script: """
                            . ${VENV}/bin/activate
                            export SITES_TO_TEST="${params.SITES_TO_TEST}"
                            export USE_DOCKER="${env.USE_DOCKER}"
                            export SELENIUM_URL="${env.SELENIUM_URL ?: ''}"
                            export BUILD_NUMBER="${BUILD_NUMBER}"
                            
                            python run_nbc_tests.py
                        """,
                        returnStatus: true
                    )
                    
                    if (exitCode != 0) {
                        currentBuild.result = 'FAILURE'
                    } else {
                        currentBuild.result = 'SUCCESS'
                    }
                }
            }
        }
        
        stage('Archive Reports') {
            steps {
                script {
                    echo "📁 Archiving test reports..."
                    
                    archiveArtifacts artifacts: 'multi_site_report.html, test_summary.json', 
                                     allowEmptyArchive: true,
                                     fingerprint: true
                    
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
        }
        
        stage('Send Notifications') {
            steps {
                script {
                    echo "📬 Sending notifications..."
                    
                    // Read test results
                    def summary = readJSON file: 'test_summary.json'
                    
                    // Calculate pass percentage
                    def passPercentage = summary.total_tests > 0 ? 
                        Math.round((summary.total_passed / summary.total_tests) * 100) : 0
                    
                    // Determine status and styling
                    def overallStatus = summary.sites_failed == 0 ? 'SUCCESS' : 'FAILURE'
                    def statusEmoji = summary.sites_failed == 0 ? '✅' : '❌'
                    def color = summary.sites_failed == 0 ? 'good' : 'danger'
                    
                    // Create rich Slack message
                    def slackMessage = [
                        channel: env.SLACK_CHANNEL,
                        color: color,
                        attachments: [[
                            fallback: "NBC Test Results - ${overallStatus}",
                            author_name: "NBC Automation Suite",
                            author_icon: "https://cdn-icons-png.flaticon.com/512/4712/4712109.png",
                            title: "${statusEmoji} NBC Multi-Site Test Results - Build #${BUILD_NUMBER}",
                            title_link: "${HTML_REPORT_URL}",
                            text: "Test execution completed with ${passPercentage}% success rate",
                            fields: [
                                [
                                    title: "📊 Sites Coverage",
                                    value: "${summary.sites_passed}/${summary.total_sites} passed",
                                    short: true
                                ],
                                [
                                    title: "🧪 Test Results",
                                    value: "${summary.total_passed}/${summary.total_tests} passed",
                                    short: true
                                ],
                                [
                                    title: "⏱️ Duration",
                                    value: "${summary.duration_seconds}s",
                                    short: true
                                ],
                                [
                                    title: "🔧 Execution Mode",
                                    value: "${params.EXECUTION_MODE}",
                                    short: true
                                ],
                                [
                                    title: "📈 Success Rate",
                                    value: "${passPercentage}%",
                                    short: true
                                ],
                                [
                                    title: "🏗️ Build",
                                    value: "#${BUILD_NUMBER}",
                                    short: true
                                ]
                            ],
                            footer: "NBC Test Automation",
                            footer_icon: "https://cdn-icons-png.flaticon.com/512/888/888882.png",
                            ts: System.currentTimeMillis() / 1000
                        ]]
                    ]
                    
                    // Add site-specific details if there are failures
                    if (summary.sites_failed > 0) {
                        def failedSites = summary.sites.findAll { it.failed > 0 }
                        def failedSitesList = failedSites.collect { it.site_name }.join(", ")
                        
                        slackMessage.attachments[0].fields << [
                            title: "⚠️ Failed Sites",
                            value: failedSitesList,
                            short: false
                        ]
                    }
                    
                    // Send to Slack
                    try {
                        slackSend(slackMessage)
                        echo "✅ Slack notification sent successfully!"
                    } catch (Exception e) {
                        echo "Failed to send Slack notification: ${e.message}"
                        
                        // Fallback to simple message
                        try {
                            slackSend(
                                channel: env.SLACK_CHANNEL,
                                color: color,
                                message: """
${statusEmoji} NBC Tests ${overallStatus} - Build #${BUILD_NUMBER}
Sites: ${summary.sites_passed}/${summary.total_sites} passed
Tests: ${summary.total_passed}/${summary.total_tests} passed
Duration: ${summary.duration_seconds}s
Mode: ${params.EXECUTION_MODE}
Report: ${HTML_REPORT_URL}
                                """
                            )
                        } catch (Exception e2) {
                            echo "Slack notification failed completely. Please check Slack integration."
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                // Clean up Docker container if used
                if (params.EXECUTION_MODE == 'DOCKER') {
                    sh """
                        echo "Cleaning up Docker containers..."
                        docker stop selenium-chrome-${BUILD_NUMBER} || true
                        docker rm selenium-chrome-${BUILD_NUMBER} || true
                    """
                }
                
                // Clean up Python environment
                sh """
                    if [ -d "${VENV}" ]; then
                        rm -rf ${VENV}
                    fi
                """
                
                echo "╔════════════════════════════════════════╗"
                echo "║   PIPELINE EXECUTION COMPLETED        ║"
                echo "║   Status: ${currentBuild.result ?: 'UNKNOWN'}                    ║"
                echo "║   Mode: ${params.EXECUTION_MODE}                     ║"
                echo "╚════════════════════════════════════════╝"
            }
        }
        
        success {
            echo '🎉 All tests passed successfully!'
        }
        
        failure {
            echo '❌ Some tests failed. Check the detailed report for more information.'
        }
    }
}
