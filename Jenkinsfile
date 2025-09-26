pipeline {
    agent { label 'Jenkins 2' }
    
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
        
        stage('Check Chrome Installation') {
            steps {
                script {
                    echo "Checking for Chrome browser..."
                    
                    def chromeFound = sh(
                        script: '''
                            if which google-chrome-stable > /dev/null 2>&1; then
                                echo "found"
                            elif which google-chrome > /dev/null 2>&1; then
                                echo "found"
                            elif which chromium-browser > /dev/null 2>&1; then
                                echo "found"
                            elif which chromium > /dev/null 2>&1; then
                                echo "found"
                            else
                                echo "not_found"
                            fi
                        ''',
                        returnStdout: true
                    ).trim()
                    
                    if (chromeFound == "not_found") {
                        echo "WARNING: Chrome is not installed on this Jenkins server"
                        echo "Tests will fail due to missing Chrome browser"
                        env.CHROME_STATUS = "NOT_INSTALLED"
                    } else {
                        echo "Chrome browser found"
                        env.CHROME_STATUS = "INSTALLED"
                    }
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    echo "Running NBC Tests..."
                    
                    // Determine which sites to test
                    def sitesParam = ""
                    if (params.SITES_TO_TEST == 'NBC_NEW_YORK_ONLY') {
                        sitesParam = '--sites "New York"'
                    }
                    
                    // Run the actual tests (they will fail if Chrome is missing, but that's the truth)
                    def exitCode = sh(
                        script: """
                            . ${VENV}/bin/activate
                            python nbc_multi_site_tester.py --workers ${params.PARALLEL_WORKERS} ${sitesParam} || true
                        """,
                        returnStatus: true
                    )
                    
                    // If the test script doesn't exist or fails completely, create accurate error report
                    if (!fileExists('test_summary.json')) {
                        echo "Test script failed. Creating error report..."
                        
                        writeFile file: 'test_summary.json', text: """
{
    "timestamp": "${new Date().format('yyyy-MM-dd HH:mm:ss')}",
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
            "test": "Driver Setup",
            "status": "ERROR",
            "details": "Chrome browser not installed on Jenkins server"
        }],
        "duration": 0
    }]
}
"""
                        
                        writeFile file: 'multi_site_report.html', text: """
<!DOCTYPE html>
<html>
<head>
    <title>NBC Test Report - ERROR</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .error { color: red; font-weight: bold; }
        .warning { background: #fffacd; padding: 10px; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <h1>NBC Multi-Site Test Report</h1>
    <p class="error">❌ TEST EXECUTION FAILED</p>
    
    <div class="warning">
        <h2>Error Details:</h2>
        <p><strong>Problem:</strong> Chrome browser is not installed on Jenkins server</p>
        <p><strong>Impact:</strong> Cannot run Selenium tests</p>
        <p><strong>Solution:</strong> Install Chrome or Chromium on the Jenkins server</p>
    </div>
    
    <h3>Test Summary:</h3>
    <ul>
        <li>Sites Tested: 1</li>
        <li>Sites Passed: 0</li>
        <li>Sites Failed: 1</li>
        <li>Error: Chrome driver cannot be initialized</li>
    </ul>
    
    <p>Build: #${BUILD_NUMBER}</p>
    <p>Time: ${new Date()}</p>
</body>
</html>
"""
                    }
                    
                    // Set build status based on actual results
                    def summary = readJSON file: 'test_summary.json'
                    if (summary.sites_failed > 0) {
                        currentBuild.result = 'FAILURE'
                    }
                }
            }
        }
        
        stage('Archive Reports') {
            steps {
                script {
                    echo "Archiving test reports..."
                    
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
        
        stage('Send Slack Notification') {
            steps {
                script {
                    echo "Attempting to send Slack notification to ${SLACK_CHANNEL}..."
                    
                    // Read actual test results
                    def summary = readJSON file: 'test_summary.json'
                    
                    // Build accurate message
                    def testStatus = summary.sites_failed > 0 ? 'FAILED' : 'PASSED'
                    def emoji = summary.sites_failed > 0 ? '❌' : '✅'
                    def color = summary.sites_failed > 0 ? 'danger' : 'good'
                    
                    def message = """${emoji} NBC Tests ${testStatus} - Build #${BUILD_NUMBER}
Sites Tested: ${summary.total_sites}
Sites Passed: ${summary.sites_passed}
Sites Failed: ${summary.sites_failed}
Tests Run: ${summary.total_tests}
Tests Passed: ${summary.total_passed}
Tests Failed: ${summary.total_failed}"""
                    
                    if (env.CHROME_STATUS == 'NOT_INSTALLED') {
                        message += "\n⚠️ Chrome not installed on Jenkins server"
                    }
                    
                    message += "\nView Report: ${HTML_REPORT_URL}"
                    
                    // Method 1: Try using slackSend with global configuration
                    try {
                        slackSend(
                            channel: env.SLACK_CHANNEL,
                            color: color,
                            message: message
                        )
                        echo "Slack notification sent successfully!"
                    } catch (Exception e1) {
                        echo "slackSend failed: ${e1.message}"
                        echo "Trying alternative method..."
                        
                        // Method 2: Try with botUser flag
                        try {
                            slackSend(
                                channel: env.SLACK_CHANNEL,
                                color: color,
                                message: message,
                                botUser: true
                            )
                            echo "Slack notification sent via bot user!"
                        } catch (Exception e2) {
                            echo "Bot user method failed: ${e2.message}"
                            
                            // Method 3: Manual webhook if credential exists
                            try {
                                withCredentials([string(credentialsId: 'Jenkins-Slack-Integration', variable: 'WEBHOOK')]) {
                                    sh """
                                        echo "Sending to Slack via webhook..."
                                        curl -X POST \
                                             -H 'Content-type: application/json' \
                                             --data '{"channel":"${env.SLACK_CHANNEL}","text":"${message}"}' \
                                             "\${WEBHOOK}"
                                    """
                                }
                            } catch (Exception e3) {
                                echo "ERROR: Could not send Slack notification"
                                echo "Please check your Slack configuration in Jenkins"
                                echo "Go to: Manage Jenkins > Configure System > Slack"
                                echo "Ensure you have:"
                                echo "1. Team Subdomain or Workspace configured"
                                echo "2. Integration Token Credential selected"
                                echo "3. Test Connection works"
                            }
                        }
                    }
                }
            }
        }
    }
    
    post {
        always {
            script {
                // Clean up
                sh """
                    if [ -d "${VENV}" ]; then
                        rm -rf ${VENV}
                    fi
                """
                
                echo "========================================="
                echo "Pipeline Status: ${currentBuild.result ?: 'UNKNOWN'}"
                echo "Chrome Status: ${env.CHROME_STATUS}"
                echo "========================================="
            }
        }
        
        success {
            echo '✅ Tests passed successfully!'
        }
        
        failure {
            echo '❌ Tests failed. Check the report for details.'
            echo 'Most likely cause: Chrome is not installed on Jenkins server'
        }
    }
}
