pipeline {
    agent any
    
    environment {
        // Your existing Slack Configuration
        SLACK_CHANNEL = '#ops-realtime-monitoring'
        SLACK_WEBHOOK_CREDENTIALS = 'Jenkins-Slack-Integration'
        
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
            description: 'Test NBC New York only or all 52 sites'
        )
        choice(
            name: 'PARALLEL_WORKERS',
            choices: ['5', '3', '10'],
            description: 'Number of parallel workers'
        )
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo "Starting NBC Testing Pipeline"
                checkout scm
            }
        }
        
        stage('Setup Environment') {
            steps {
                script {
                    echo "Setting up Python environment..."
                    
                    sh '''
                        # Create virtual environment
                        python3 -m venv ${VENV}
                        
                        # Install packages
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
                    
                    def sitesParam = ""
                    if (params.SITES_TO_TEST == 'NBC_NEW_YORK_ONLY') {
                        sitesParam = '--sites "New York"'
                    }
                    
                    // Run the tests
                    def exitCode = sh(
                        script: """
                            . ${VENV}/bin/activate
                            python nbc_multi_site_tester.py --workers ${params.PARALLEL_WORKERS} ${sitesParam}
                        """,
                        returnStatus: true
                    )
                    
                    // Set build result based on tests
                    if (exitCode != 0) {
                        currentBuild.result = 'UNSTABLE'
                    }
                }
            }
        }
        
        stage('Archive Reports') {
            steps {
                script {
                    // Archive artifacts
                    archiveArtifacts artifacts: 'multi_site_report.html, test_summary.json', 
                                     allowEmptyArchive: false
                    
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
                    
                    // Read test results
                    def summaryFile = readFile('test_summary.json')
                    def summary = readJSON text: summaryFile
                    
                    // Determine status
                    def testStatus = summary.sites_failed == 0 ? 'PASSED' : 'FAILED'
                    def color = summary.sites_failed == 0 ? 'good' : 'danger'
                    def emoji = summary.sites_failed == 0 ? '✅' : '❌'
                    
                    // Create message
                    def slackMessage = """${emoji} *NBC Test Results* - Build #${BUILD_NUMBER}
*Status:* ${testStatus}
*Sites Tested:* ${summary.total_sites}
*Sites Passed:* ${summary.sites_passed}/${summary.total_sites}
*Tests Run:* ${summary.total_tests}
*Success Rate:* ${Math.round(summary.total_passed * 100.0 / summary.total_tests)}%
*Duration:* ${summary.duration_seconds}s

View Full Report: ${HTML_REPORT_URL}"""

                    // Send to Slack using your credentials
                    slackSend(
                        channel: env.SLACK_CHANNEL,
                        color: color,
                        message: slackMessage,
                        tokenCredentialId: env.SLACK_WEBHOOK_CREDENTIALS,
                        teamDomain: 'your-team',  // Replace with your Slack team domain
                        botUser: true
                    )
                }
            }
        }
    }
    
    post {
        always {
            script {
                // Clean up
                sh '''
                    if [ -d "${VENV}" ]; then
                        rm -rf ${VENV}
                    fi
                '''
                
                echo "Pipeline completed with status: ${currentBuild.result ?: 'SUCCESS'}"
            }
        }
        
        success {
            echo '✅ All tests completed successfully!'
        }
        
        unstable {
            echo '⚠️ Some tests failed. Check the report for details.'
            
            // Send alert for failures
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'warning',
                message: "⚠️ NBC Tests have failures - Build #${BUILD_NUMBER}\nCheck report: ${HTML_REPORT_URL}",
                tokenCredentialId: env.SLACK_WEBHOOK_CREDENTIALS,
                teamDomain: 'your-team',
                botUser: true
            )
        }
        
        failure {
            echo '❌ Pipeline failed!'
            
            // Send critical alert
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'danger',
                message: "🚨 NBC Test Pipeline FAILED - Build #${BUILD_NUMBER}\nCheck logs: ${BUILD_URL}console",
                tokenCredentialId: env.SLACK_WEBHOOK_CREDENTIALS,
                teamDomain: 'your-team',
                botUser: true
            )
        }
    }
}
