pipeline {
    agent any
    
    parameters {
        choice(
            name: 'SLACK_CHANNEL',
            choices: ['#ops-realtime-monitoring', '#automation_test_results'],
            description: 'Slack channel to send notifications'
        )
        choice(
            name: 'TEST_ENVIRONMENT',
            choices: ['PRODUCTION', 'STAGING', 'DEV'],
            description: 'Environment to test'
        )
        choice(
            name: 'PARALLEL_WORKERS',
            choices: ['5', '10', '3', '20'],
            description: 'Number of parallel test workers'
        )
        choice(
            name: 'SITES_TO_TEST',
            choices: ['ALL', 'TOP_10', 'CRITICAL', 'CUSTOM'],
            description: 'Which sites to test'
        )
        string(
            name: 'CUSTOM_SITES',
            defaultValue: '',
            description: 'Comma-separated list of sites (if CUSTOM selected)'
        )
    }
    
    environment {
        // Python virtual environment
        VENV = "${WORKSPACE}/venv"
        
        // Slack webhook from Jenkins credentials
        SLACK_WEBHOOK = credentials('slack-webhook-qa')
        
        // Test configuration
        WORKERS = "${params.PARALLEL_WORKERS}"
        
        // Report URLs
        HTML_REPORT_URL = "${BUILD_URL}NBC_20Multi-Site_20Report/"
        
        // Git info
        GIT_BRANCH = sh(returnStdout: true, script: 'git rev-parse --abbrev-ref HEAD').trim()
        GIT_COMMIT = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
    }
    
    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30'))
        disableConcurrentBuilds()
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                
                script {
                    echo "Branch: ${env.GIT_BRANCH}"
                    echo "Commit: ${env.GIT_COMMIT}"
                    echo "Workspace: ${env.WORKSPACE}"
                }
            }
        }
        
        stage('Setup Environment') {
            steps {
                script {
                    echo '🔧 Setting up Python environment...'
                    
                    // Create virtual environment
                    sh """
                        python3 -m venv ${VENV}
                        . ${VENV}/bin/activate
                        pip install --upgrade pip
                        pip install -r requirements.txt
                    """
                    
                    // Install Chrome if not present
                    sh '''
                        if ! command -v google-chrome &> /dev/null; then
                            echo "Installing Chrome..."
                            wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
                            echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
                            apt-get update
                            apt-get install -y google-chrome-stable
                        fi
                        
                        google-chrome --version
                    '''
                }
            }
        }
        
        stage('Determine Sites to Test') {
            steps {
                script {
                    def sitesArg = ''
                    
                    switch(params.SITES_TO_TEST) {
                        case 'TOP_10':
                            sitesArg = '--sites "New York,Los Angeles,Chicago,Philadelphia,Dallas-Fort Worth,San Francisco Bay Area,Boston,Washington DC,Miami,San Diego"'
                            break
                        case 'CRITICAL':
                            sitesArg = '--sites "New York,Los Angeles,Chicago,Washington DC,Boston"'
                            break
                        case 'CUSTOM':
                            if (params.CUSTOM_SITES) {
                                sitesArg = "--sites \"${params.CUSTOM_SITES}\""
                            }
                            break
                        default:
                            sitesArg = ''  // Test all sites
                    }
                    
                    env.SITES_ARG = sitesArg
                    echo "Sites configuration: ${env.SITES_ARG ?: 'ALL SITES'}"
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    echo "🧪 Running NBC Multi-Site Tests..."
                    echo "Workers: ${params.PARALLEL_WORKERS}"
                    echo "Environment: ${params.TEST_ENVIRONMENT}"
                    
                    def testCommand = """
                        . ${VENV}/bin/activate
                        python nbc_multi_site_tester.py --workers ${params.PARALLEL_WORKERS} ${env.SITES_ARG}
                    """
                    
                    // Run tests and capture exit code
                    def testResult = sh(
                        script: testCommand,
                        returnStatus: true
                    )
                    
                    // Store result
                    env.TEST_RESULT = testResult == 0 ? 'SUCCESS' : 'FAILURE'
                    
                    // Don't fail the build yet, we want to send notifications
                    if (testResult != 0) {
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
        }
        
        stage('Archive Reports') {
            steps {
                script {
                    echo '📁 Archiving test reports...'
                    
                    // Archive artifacts
                    archiveArtifacts artifacts: 'multi_site_report.html, test_summary.json', 
                                     allowEmptyArchive: false,
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
                    
                    // Parse test summary for metrics
                    def summary = readJSON file: 'test_summary.json'
                    
                    // Add custom summary
                    def testSummary = """
                        <h3>NBC Multi-Site Test Summary</h3>
                        <ul>
                            <li>Total Sites: ${summary.total_sites}</li>
                            <li>Sites Passed: ${summary.sites_passed}</li>
                            <li>Sites Failed: ${summary.sites_failed}</li>
                            <li>Total Tests: ${summary.total_tests}</li>
                            <li>Tests Passed: ${summary.total_passed}</li>
                            <li>Tests Failed: ${summary.total_failed}</li>
                            <li>Duration: ${summary.duration_seconds}s</li>
                        </ul>
                    """
                    
                    currentBuild.description = testSummary
                }
            }
        }
        
        stage('Send Slack Notification') {
            steps {
                script {
                    echo "📨 Sending notification to ${params.SLACK_CHANNEL}..."
                    
                    // Use the Slack integration
                    sh """
                        . ${VENV}/bin/activate
                        export SLACK_WEBHOOK_URL=${SLACK_WEBHOOK}
                        python slack_reporter.py '${params.SLACK_CHANNEL}'
                    """
                    
                    // Alternative: Use Jenkins Slack plugin if configured
                    if (env.TEST_RESULT == 'SUCCESS') {
                        slackSend(
                            channel: params.SLACK_CHANNEL,
                            color: 'good',
                            message: "✅ NBC Multi-Site Tests PASSED - Build #${BUILD_NUMBER}\nView Report: ${HTML_REPORT_URL}"
                        )
                    } else {
                        slackSend(
                            channel: params.SLACK_CHANNEL,
                            color: 'danger',
                            message: "❌ NBC Multi-Site Tests FAILED - Build #${BUILD_NUMBER}\nView Report: ${HTML_REPORT_URL}"
                        )
                    }
                }
            }
        }
        
        stage('Performance Trends') {
            steps {
                script {
                    echo '📊 Recording performance metrics...'
                    
                    // Read and record metrics
                    def summary = readJSON file: 'test_summary.json'
                    
                    // Record for trending
                    def metricsFile = "${WORKSPACE}/metrics.properties"
                    writeFile file: metricsFile, text: """
                        SITES_TESTED=${summary.total_sites}
                        SITES_PASSED=${summary.sites_passed}
                        SITES_FAILED=${summary.sites_failed}
                        TOTAL_TESTS=${summary.total_tests}
                        TESTS_PASSED=${summary.total_passed}
                        TESTS_FAILED=${summary.total_failed}
                        DURATION=${summary.duration_seconds}
                    """
                }
            }
        }
    }
    
    post {
        always {
            script {
                echo "Build Status: ${currentBuild.result ?: 'SUCCESS'}"
                
                // Clean up workspace but keep reports
                sh '''
                    if [ -d "${VENV}" ]; then
                        rm -rf ${VENV}
                    fi
                '''
            }
        }
        
        success {
            echo '✅ All tests completed successfully!'
            
            // Update commit status if using GitHub/Bitbucket
            updateGitlabCommitStatus name: 'nbc-tests', state: 'success'
        }
        
        unstable {
            echo '⚠️ Some tests failed. Check the report for details.'
            
            // Update commit status
            updateGitlabCommitStatus name: 'nbc-tests', state: 'failed'
        }
        
        failure {
            echo '❌ Pipeline failed. Check logs for errors.'
            
            // Send emergency notification
            slackSend(
                channel: '#qa-alerts',
                color: 'danger',
                message: "🚨 NBC Test Pipeline FAILED - Build #${BUILD_NUMBER}\n${BUILD_URL}"
            )
        }
        
        cleanup {
            // Clean workspace after build
            deleteDir()
        }
    }
}
