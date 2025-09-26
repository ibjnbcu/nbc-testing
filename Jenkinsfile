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
            name: 'SITES_TO_TEST',
            choices: ['NBC_NEW_YORK_ONLY', 'ALL_SITES'],
            description: 'Test scope'
        )
        choice(
            name: 'PARALLEL_WORKERS',
            choices: ['1', '3', '5'],
            description: 'Parallel workers'
        )
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Python Environment') {
            steps {
                sh '''
                    python3 -m venv ${VENV}
                    . ${VENV}/bin/activate
                    pip install --upgrade pip
                    pip install selenium==4.16.0
                    pip install webdriver-manager==4.0.1
                    pip install requests==2.31.0
                    pip install pandas==2.1.4
                    pip install openpyxl==3.1.2
                '''
            }
        }
        
        stage('Create Working Test Script') {
            steps {
                script {
                    // Create a test script that uses Chromium correctly
                    writeFile file: 'run_nbc_test.py', text: '''
import os
import sys
import json
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NBCTester:
    def __init__(self, site_name, site_url):
        self.site_name = site_name
        self.site_url = site_url
        self.results = []
        self.driver = None
        
    def create_driver(self):
        """Create Chromium driver that works on Ubuntu"""
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            # Try to find Chromium
            chromium_paths = [
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
                '/snap/bin/chromium'
            ]
            
            chromium_found = None
            for path in chromium_paths:
                if os.path.exists(path):
                    chromium_found = path
                    logger.info(f"Found Chromium at: {path}")
                    break
                    
            if chromium_found:
                options.binary_location = chromium_found
            else:
                logger.warning("Chromium not found, trying default")
            
            # Try to find chromedriver
            driver_paths = [
                '/usr/bin/chromedriver',
                '/usr/local/bin/chromedriver',
                '/snap/bin/chromium.chromedriver'
            ]
            
            driver_found = None
            for path in driver_paths:
                if os.path.exists(path):
                    driver_found = path
                    logger.info(f"Found chromedriver at: {path}")
                    break
            
            if driver_found:
                service = Service(driver_found)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                # Try webdriver-manager
                from webdriver_manager.chrome import ChromeDriverManager
                from webdriver_manager.core.os_manager import ChromeType
                
                service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
                self.driver = webdriver.Chrome(service=service, options=options)
                
            self.driver.set_page_load_timeout(20)
            return True
            
        except Exception as e:
            logger.error(f"Failed to create driver: {e}")
            self.results.append({
                "test": "Driver Setup",
                "status": "ERROR",
                "details": str(e)[:100]
            })
            return False
    
    def run_tests(self):
        """Run actual tests on the NBC website"""
        if not self.create_driver():
            return {
                "site_name": self.site_name,
                "site_url": self.site_url,
                "total_tests": 1,
                "passed": 0,
                "failed": 1,
                "test_results": self.results
            }
        
        try:
            # Test 1: Homepage loads
            logger.info(f"Testing {self.site_name} homepage...")
            self.driver.get(self.site_url)
            time.sleep(2)
            
            title = self.driver.title
            if title:
                self.results.append({
                    "test": "Homepage Load",
                    "status": "PASS",
                    "details": f"Page loaded: {title[:50]}"
                })
            else:
                self.results.append({
                    "test": "Homepage Load",
                    "status": "FAIL",
                    "details": "No title found"
                })
            
            # Test 2: Navigation check
            try:
                nav_elements = self.driver.find_elements(By.TAG_NAME, "nav")
                if nav_elements:
                    self.results.append({
                        "test": "Navigation",
                        "status": "PASS",
                        "details": f"Found {len(nav_elements)} nav elements"
                    })
                else:
                    self.results.append({
                        "test": "Navigation",
                        "status": "FAIL",
                        "details": "No navigation found"
                    })
            except Exception as e:
                self.results.append({
                    "test": "Navigation",
                    "status": "FAIL",
                    "details": str(e)[:50]
                })
            
            # Test 3: Content check
            try:
                articles = self.driver.find_elements(By.TAG_NAME, "article")
                headlines = self.driver.find_elements(By.CSS_SELECTOR, "h1, h2")
                
                if articles or headlines:
                    self.results.append({
                        "test": "Content",
                        "status": "PASS",
                        "details": f"{len(articles)} articles, {len(headlines)} headlines"
                    })
                else:
                    self.results.append({
                        "test": "Content",
                        "status": "FAIL",
                        "details": "No content found"
                    })
            except Exception as e:
                self.results.append({
                    "test": "Content",
                    "status": "FAIL",
                    "details": str(e)[:50]
                })
                
        except Exception as e:
            logger.error(f"Test execution error: {e}")
            self.results.append({
                "test": "Execution",
                "status": "ERROR",
                "details": str(e)[:100]
            })
            
        finally:
            if self.driver:
                self.driver.quit()
        
        # Calculate summary
        passed = len([r for r in self.results if r["status"] == "PASS"])
        failed = len([r for r in self.results if r["status"] in ["FAIL", "ERROR"]])
        
        return {
            "site_name": self.site_name,
            "site_url": self.site_url,
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "test_results": self.results
        }

def main():
    """Main execution"""
    logger.info("Starting NBC website testing...")
    
    # Sites to test
    sites_to_test = [
        ("New York", "https://www.nbcnewyork.com/")
    ]
    
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "total_sites": len(sites_to_test),
        "sites_passed": 0,
        "sites_failed": 0,
        "total_tests": 0,
        "total_passed": 0,
        "total_failed": 0,
        "duration_seconds": 0,
        "sites": []
    }
    
    start_time = time.time()
    
    for site_name, site_url in sites_to_test:
        logger.info(f"Testing {site_name}...")
        tester = NBCTester(site_name, site_url)
        result = tester.run_tests()
        
        all_results["sites"].append(result)
        all_results["total_tests"] += result["total_tests"]
        all_results["total_passed"] += result["passed"]
        all_results["total_failed"] += result["failed"]
        
        if result["failed"] == 0:
            all_results["sites_passed"] += 1
        else:
            all_results["sites_failed"] += 1
    
    all_results["duration_seconds"] = time.time() - start_time
    
    # Save JSON results
    with open("test_summary.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    # Generate HTML report
    generate_html_report(all_results)
    
    logger.info(f"Testing complete: {all_results['sites_passed']}/{all_results['total_sites']} sites passed")
    
    return 0 if all_results["sites_failed"] == 0 else 1

def generate_html_report(results):
    """Generate simple HTML report"""
    status = "PASSED" if results["sites_failed"] == 0 else "FAILED"
    color = "#28a745" if results["sites_failed"] == 0 else "#dc3545"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>NBC Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid {color}; padding-bottom: 10px; }}
        .status {{ font-size: 24px; color: {color}; font-weight: bold; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric {{ text-align: center; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #333; }}
        .metric-label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th {{ background: #f8f9fa; padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6; }}
        td {{ padding: 10px; border-bottom: 1px solid #dee2e6; }}
        .pass {{ color: #28a745; }}
        .fail {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>NBC Website Test Report</h1>
        <div class="status">Status: {status}</div>
        
        <div class="summary">
            <div class="metric">
                <div class="metric-value">{results['total_sites']}</div>
                <div class="metric-label">Sites Tested</div>
            </div>
            <div class="metric">
                <div class="metric-value">{results['sites_passed']}</div>
                <div class="metric-label">Sites Passed</div>
            </div>
            <div class="metric">
                <div class="metric-value">{results['total_tests']}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric">
                <div class="metric-value">{int(results['total_passed']/max(results['total_tests'],1)*100)}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
        </div>
        
        <h2>Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Site</th>
                    <th>Tests Run</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>"""
    
    for site in results["sites"]:
        site_status = "pass" if site["failed"] == 0 else "fail"
        html += f"""
                <tr>
                    <td>{site['site_name']}</td>
                    <td>{site['total_tests']}</td>
                    <td>{site['passed']}</td>
                    <td>{site['failed']}</td>
                    <td class="{site_status}">{'PASS' if site['failed'] == 0 else 'FAIL'}</td>
                </tr>"""
    
    html += f"""
            </tbody>
        </table>
        
        <p style="margin-top: 30px; color: #666;">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            Duration: {results['duration_seconds']:.1f} seconds
        </p>
    </div>
</body>
</html>"""
    
    with open("multi_site_report.html", "w") as f:
        f.write(html)
    
    logger.info("HTML report generated")

if __name__ == "__main__":
    sys.exit(main())
'''
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    sh '''
                        . ${VENV}/bin/activate
                        python run_nbc_test.py
                    '''
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
                    
                    def status = summary.sites_failed == 0 ? 'PASSED ✅' : 'FAILED ❌'
                    def color = summary.sites_failed == 0 ? 'good' : 'danger'
                    
                    // Simple, clean message - not a wall of text
                    def message = """NBC Test Results - Build #${BUILD_NUMBER}
Status: ${status}
Sites: ${summary.sites_passed}/${summary.total_sites} passed
Tests: ${summary.total_passed}/${summary.total_tests} passed
Report: ${HTML_REPORT_URL}"""
                    
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
