pipeline {
    agent { label 'QA-Agent' }
    
    environment {
        SLACK_CHANNEL = '#automation_test_results'
        VENV = "${WORKSPACE}/venv"
        HTML_REPORT_URL = "${BUILD_URL}artifact/index.html"
    }
    
    options {
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '30'))
    }
    
    parameters {
        choice(
            name: 'STATION',
            choices: ['NBC New York', 'ALL_STATIONS'],
            description: 'Which station to test'
        )
        string(
            name: 'CUSTOM_URL',
            defaultValue: '',
            description: 'Optional: Custom URL to test'
        )
    }
    
    triggers {
        cron('H 2 * * *')
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Setup Python') {
            steps {
                sh '''
                    python3 -m venv ${VENV}
                    . ${VENV}/bin/activate
                    pip install --quiet --upgrade pip
                    pip install --quiet selenium==4.16.0 webdriver-manager==4.0.1 requests
                '''
            }
        }
        
        stage('Install Chrome') {
            steps {
                sh '''
                    if ! command -v chromium-browser &> /dev/null; then
                        sudo apt-get update -qq
                        sudo apt-get install -y -qq chromium-browser chromium-chromedriver
                    fi
                '''
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    def testCmd = ". ${VENV}/bin/activate && python nbc_test.py"
                    
                    if (params.CUSTOM_URL) {
                        testCmd += " --url '${params.CUSTOM_URL}'"
                    } else if (params.STATION != 'ALL_STATIONS') {
                        testCmd += " --station '${params.STATION}'"
                    }
                    
                    // Run the test script, allow non-zero exit without failing Jenkins job
                    sh testCmd + " || true"
                }
            }
        }
        
        stage('Archive Reports') {
            steps {
                archiveArtifacts artifacts: 'index.html, test_summary.json', allowEmptyArchive: false
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: '.',
                    reportFiles: 'index.html',
                    reportName: 'Test Report',
                    reportTitles: 'NBC Test Report'
                ])
            }
        }
        
        stage('Send Slack Report') {
            steps {
                script {
                    def summary = readJSON file: 'test_summary.json'
                    
                    def overallStatus = summary.stations_failed == 0 ? 'PASSED' : 'FAILED'
                    def statusIcon = summary.stations_failed == 0 ? ':white_check_mark:' : ':x:'
                    def slackColor = summary.stations_failed == 0 ? 'good' : 'danger'
                    
                    def successRate = 0
                    if (summary.total_tests > 0) {
                        successRate = ((summary.total_passed / summary.total_tests) * 100).toInteger()
                    }
                    
                    def details = ""
                    summary.stations.each { station ->
                        def icon = station.overall_status == 'PASS' ? ':white_check_mark:' : ':x:'
                        details += "${icon} *${station.station_name}*: ${station.passed}/${station.total_tests} passed\n"
                    }
                    
                    slackSend(
                        channel: env.SLACK_CHANNEL,
                        color: slackColor,
                        message: """${statusIcon} *NBC Test #${BUILD_NUMBER}: ${overallStatus}*

*Results:*
- Stations: ${summary.stations_passed}/${summary.total_stations} passed
- Tests: ${summary.total_passed}/${summary.total_tests} passed
- Success Rate: ${successRate}%

${details}

:page_facing_up: *View Full Report:* ${HTML_REPORT_URL}"""
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
