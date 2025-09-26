
pipeline {
    agent { label 'QA-Agent' }
    
    environment {
        // Slack Configuration
        SLACK_CHANNEL = '#automation_test_results'
        
        // Python environment
        VENV = "${WORKSPACE}/venv"
        
        // Report URL
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
        choice(
            name: 'PARALLEL_WORKERS',
            choices: ['1', '3', '5'],
            description: 'Number of parallel workers'
        )
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo "========================================="
                echo "Starting NBC Testing Pipeline"
                echo "========================================="
                checkout scm
            }
        }
        
        stage('Setup Python Environment') {
            steps {
                script {
                    echo "Setting up Python environment..."
                    
                    sh '''
                        python3 --version
                        python3 -m venv ${VENV}
                        . ${VENV}/bin/activate
                        pip install --upgrade pip
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
                    echo "Running NBC Tests..."
                    
                    // Check if the main test script exists
                    def scriptExists = fileExists('nbc_multi_site_tester.py')
                    
                    if (scriptExists) {
                        // Determine which sites to test
                        def sitesParam = ""
                        if (params.SITES_TO_TEST == 'NBC_NEW_YORK_ONLY') {
                            sitesParam = '--sites "New York"'
                        }
                        
                        // Run the tests
                        sh """
                            . ${VENV}/bin/activate
                            python nbc_multi_site_tester.py --workers ${params.PARALLEL_WORKERS} ${sitesParam} || true
                        """
                    } else {
                        echo "Test script not found, creating basic test..."
                        
                        // Create a basic test file
                        writeFile file: 'basic_test.py', text: '''
import json
from datetime import datetime

results = {
    "timestamp": datetime.now().isoformat(),
    "duration_seconds": 0,
    "total_sites": 1,
    "sites_passed": 0,
    "sites_failed": 1,
    "sites_with_warnings": 0,
    "total_tests": 1,
    "total_passed": 0,
    "total_failed": 1,
    "total_warnings": 0,
    "sites": [{
        "site_name": "New York",
        "site_url": "https://www.nbcnewyork.com/",
        "total_tests": 1,
        "passed": 0,
        "failed": 1,
        "warnings": 0,
        "success_rate": 0,
        "test_results": [{
            "test": "Setup",
            "status": "ERROR",
            "details": "Test script not found"
        }],
        "duration": 0
    }]
}

with open("test_summary.json", "w") as f:
    json.dump(results, f, indent=2)

print("Basic test completed")
'''
                        
                        sh '''
                            . ${VENV}/bin/activate
                            python basic_test.py
                        '''
                    }
                    
                    // Ensure results files exist
                    if (!fileExists('test_summary.json')) {
                        writeFile file: 'test_summary.json', text: '''
{
    "timestamp": "''' + new Date().format("yyyy-MM-dd'T'HH:mm:ss") + '''",
    "duration_seconds": 0,
    "total_sites": 1,
    "sites_passed": 0,
    "sites_failed": 1,
    "sites_with_warnings": 0,
    "total_tests": 1,
    "total_passed": 0,
    "total_failed": 1,
    "total_warnings": 0,
    "sites": []
}'''
                    }
                    
                    if (!fileExists('multi_site_report.html')) {
                        writeFile file: 'multi_site_report.html', text: '''
<!DOCTYPE html>
<html>
<head>
    <title>NBC Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>NBC Test Report</h1>
    <p class="error">Test execution issue - check Jenkins logs</p>
    <p>Build: #''' + env.BUILD_NUMBER + '''</p>
</body>
</html>'''
                    }
                }
            }
        }
        
        stage('Archive Reports') {
            steps {
                script {
                    echo "Archiving test reports..."
                    
                    // Archive artifacts
                    archiveArtifacts artifacts: 'multi_site_report.html, test_summary.json', 
                                     allowEmptyArchive: true,
                                     fingerprint: true
                    
                    // Publish HTML report
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
        
        stage('Send Slack Notification') {
            steps {
                script {
                    echo "Sending Slack notification..."
                    
                    try {
                        // Read test results
                        def summaryContent = readFile('test_summary.json')
                        def summary = readJSON text: summaryContent
                        
                        // Determine status
                        def testStatus = summary.sites_failed == 0 ? 'PASSED' : 'FAILED'
                        def emoji = summary.sites_failed == 0 ? '✅' : '❌'
                        def color = summary.sites_failed == 0 ? 'good' : 'danger'
                        
                        // Create formatted message
                        def message = """
════════════════════════════════════════
        NBC TEST EXECUTION REPORT        
════════════════════════════════════════

${emoji} Status: ${testStatus}
📅 Date: ${new Date().format('yyyy-MM-dd HH:mm:ss')}
🔢 Build: #${BUILD_NUMBER}

────────────────────────────────────────
RESULTS SUMMARY
────────────────────────────────────────
Sites Tested: ${summary.total_sites}
Sites Passed: ${summary.sites_passed}
Sites Failed: ${summary.sites_failed}
Tests Run: ${summary.total_tests}
Tests Passed: ${summary.total_passed}
Tests Failed: ${summary.total_failed}
Success Rate: ${summary.total_tests > 0 ? (summary.total_passed * 100 / summary.total_tests).intValue() : 0}%

────────────────────────────────────────
📊 Full Report: ${HTML_REPORT_URL}
📋 Build Details: ${BUILD_URL}
────────────────────────────────────────
"""
                        
                        // Send to Slack
                        slackSend(
                            channel: env.SLACK_CHANNEL,
                            color: color,
                            message: message
                        )
                        
                        echo "Slack notification sent successfully"
                        
                    } catch (Exception e) {
                        echo "Warning: Failed to send Slack notification: ${e.message}"
                        echo "This is not critical - build will continue"
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                // Clean up virtual environment
                sh '''
                    if [ -d "${VENV}" ]; then
                        rm -rf ${VENV}
                    fi
                '''
                
                echo "========================================="
                echo "Pipeline completed"
                echo "========================================="
            }
        }
        
        success {
            echo 'Pipeline completed successfully'
        }
        
        failure {
            echo 'Pipeline failed - check logs for details'
        }
    }
}
