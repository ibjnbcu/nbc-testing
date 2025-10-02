pipeline {
    agent { label 'QA-Agent' }
    
    environment {
        SLACK_CHANNEL = '#automation_test_results'
        VENV = "${WORKSPACE}/venv"
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
            description: 'Which station(s) to test'
        )
        string(
            name: 'CUSTOM_URL',
            defaultValue: '',
            description: 'Optional: Enter custom URL to test'
        )
    }
    
    triggers {
        cron('H 2 * * *')
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo "Code checked out"
            }
        }
        
        stage('Setup Python') {
            steps {
                sh '''
                    python3 -m venv ${VENV}
                    . ${VENV}/bin/activate
                    pip install --quiet --upgrade pip
                    pip install --quiet selenium==4.16.0 webdriver-manager==4.0.1
                    echo "Python environment ready"
                '''
            }
        }
        
        stage('Install Chrome') {
            steps {
                sh '''
                    if ! command -v chromium-browser &> /dev/null; then
                        echo "Installing Chromium..."
                        sudo apt-get update -qq
                        sudo apt-get install -y -qq chromium-browser chromium-chromedriver
                    else
                        echo "Chromium already installed"
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
                    
                    sh testCmd
                }
            }
        }
        
        stage('Archive Results') {
            steps {
                archiveArtifacts artifacts: 'test_summary.json',
                                allowEmptyArchive: false
                echo "Results archived"
            }
        }
        
        stage('Send Slack Report') {
            steps {
                script {
                    def summary = readJSON file: 'test_summary.json'
                    
                    def overallStatus = summary.stations_failed == 0 ? 'PASSED' : 'FAILED'
                    def statusIcon = summary.stations_failed == 0 ? ':white_check_mark:' : ':x:'
                    def slackColor = summary.stations_failed == 0 ? 'good' : 'danger'
                    
                    // Build station details
                    def details = ""
                    summary.stations.each { station ->
                        def icon = station.overall_status == 'PASS' ? ':white_check_mark:' : ':x:'
                        details += "${icon} *${station.station_name}*\n"
                        details += "   Tests: ${station.passed}/${station.total_tests} passed"
                        
                        if (station.warnings > 0) {
                            details += " (:warning: ${station.warnings} warnings)"
                        }
                        
                        details += "\n"
                        
                        // Show failures
                        if (station.failed > 0 || station.errors > 0) {
                            def failures = station.test_results.findAll { 
                                it.status == 'FAIL' || it.status == 'ERROR' 
                            }
                            failures.each { test ->
                                details += "      :x: ${test.test}: ${test.message}\n"
                            }
                        }
                        
                        // Show performance
                        if (station.performance?.loadTime) {
                            def loadSec = (station.performance.loadTime / 1000).round(2)
                            details += "   Load time: ${loadSec}s\n"
                        }
                        
                        details += "   Duration: ${station.duration_seconds}s\n\n"
                    }
                    
                    // Send to Slack
                    slackSend(
                        channel: env.SLACK_CHANNEL,
                        color: slackColor,
                        message: """
${statusIcon} *NBC Station Test #${BUILD_NUMBER}: ${overallStatus}*

*Overall Results:*
- Stations: ${summary.stations_passed}/${summary.total_stations} passed
- Tests: ${summary.total_passed}/${summary.total_tests} passed
- Success Rate: ${((summary.total_passed / summary.total_tests) * 100).round(1)}%

*Station Details:*
${details}

:link: Console: ${BUILD_URL}console
:page_facing_up: Report: ${BUILD_URL}artifact/test_summary.json
"""
                    )
                }
            }
        }
    }
    
    post {
        always {
            sh "rm -rf ${VENV}"
        }
        
        failure {
            slackSend(
                channel: env.SLACK_CHANNEL,
                color: 'danger',
                message: """
:warning: *NBC Test #${BUILD_NUMBER}: PIPELINE FAILURE*

The pipeline encountered an error and could not complete.

Check console: ${BUILD_URL}console
"""
            )
        }
    }
}
