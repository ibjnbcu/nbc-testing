import json
import requests
import sys
import os
from datetime import datetime


class SlackReporter:
    def __init__(self):
        self.webhook_url = None
        self.channel = None
        self.build_info = {
            'number': os.environ.get('BUILD_NUMBER', 'LOCAL'),
            'url': os.environ.get('BUILD_URL', '#'),
            'job_name': os.environ.get('JOB_NAME', 'NBC-Testing'),
            'node': os.environ.get('NODE_NAME', 'local'),
            'branch': os.environ.get('GIT_BRANCH', 'main')
        }
    
    def send_to_slack(self, channel):
        """Send test results to specified Slack channel"""
        
        # Jenkins will provide the webhook URL for the channel
        # The webhook is configured in Jenkins credentials
        
        try:
            # Read test summary
            with open('test_summary.json', 'r') as f:
                summary = json.load(f)
            
            # Determine overall status
            total_sites = summary['total_sites']
            sites_failed = summary['sites_failed']
            sites_passed = summary['sites_passed']
            
            if sites_failed == 0:
                status_emoji = "🟢"
                status_text = "ALL SITES PASSING"
                color = "good"
            elif sites_failed <= 5:
                status_emoji = "🟡"
                status_text = f"{sites_failed} SITES WITH ISSUES"
                color = "warning"
            else:
                status_emoji = "🔴"
                status_text = f"{sites_failed} SITES FAILING"
                color = "danger"
            
            # Get top failing sites
            failing_sites = []
            for site in summary['sites']:
                if site.get('failed', 0) > 0:
                    failing_sites.append({
                        'name': site['site_name'],
                        'failed': site['failed'],
                        'total': site['total_tests']
                    })
            
            # Sort by number of failures
            failing_sites.sort(key=lambda x: x['failed'], reverse=True)
            
            # Build Slack message
            message = {
                "channel": channel,
                "username": "NBC Test Bot",
                "icon_emoji": ":robot_face:",
                "text": f"{status_emoji} NBC Multi-Site Test Results - Build #{self.build_info['number']}",
                "attachments": [
                    {
                        "color": color,
                        "title": f"Test Summary - {total_sites} Sites Tested",
                        "title_link": f"{self.build_info['url']}NBC_20Multi-Site_20Report/",
                        "fields": [
                            {
                                "title": "Overall Status",
                                "value": status_text,
                                "short": True
                            },
                            {
                                "title": "Build",
                                "value": f"#{self.build_info['number']}",
                                "short": True
                            },
                            {
                                "title": "Sites Passed",
                                "value": f"{sites_passed}/{total_sites}",
                                "short": True
                            },
                            {
                                "title": "Sites Failed",
                                "value": f"{sites_failed}/{total_sites}",
                                "short": True
                            },
                            {
                                "title": "Total Tests Run",
                                "value": str(summary['total_tests']),
                                "short": True
                            },
                            {
                                "title": "Success Rate",
                                "value": f"{(summary['total_passed']/summary['total_tests']*100):.1f}%",
                                "short": True
                            }
                        ],
                        "footer": f"Branch: {self.build_info['branch']} | Node: {self.build_info['node']}",
                        "footer_icon": "https://www.jenkins.io/images/logos/jenkins/jenkins.png",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # Add failing sites if any
            if failing_sites:
                sites_text = "\n".join([
                    f"• *{site['name']}*: {site['failed']}/{site['total']} tests failed"
                    for site in failing_sites[:5]
                ])
                
                message["attachments"].append({
                    "color": "danger",
                    "title": "⚠️ Sites Requiring Attention",
                    "text": sites_text,
                    "mrkdwn_in": ["text"]
                })
            
            # Add action buttons
            message["attachments"].append({
                "fallback": "View reports",
                "color": "#439FE0",
                "actions": [
                    {
                        "type": "button",
                        "text": "📊 View Full Report",
                        "url": f"{self.build_info['url']}NBC_20Multi-Site_20Report/"
                    },
                    {
                        "type": "button",
                        "text": "📁 View Build",
                        "url": self.build_info['url']
                    },
                    {
                        "type": "button",
                        "text": "📈 View Trends",
                        "url": f"{self.build_info['url'].rsplit('/', 2)[0]}/trend"
                    }
                ]
            })
            
            # Add execution details
            message["attachments"].append({
                "color": "#e2e8f0",
                "fields": [
                    {
                        "title": "Execution Time",
                        "value": f"{summary['duration_seconds']:.1f} seconds",
                        "short": True
                    },
                    {
                        "title": "Timestamp",
                        "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z'),
                        "short": True
                    }
                ]
            })
            
            return message
            
        except Exception as e:
            print(f"Error preparing Slack message: {e}")
            return None
    
    def send_via_webhook(self, webhook_url, message):
        """Send message via webhook URL"""
        try:
            response = requests.post(webhook_url, json=message)
            if response.status_code == 200:
                print(f"✅ Slack notification sent to {message['channel']}")
                return True
            else:
                print(f"❌ Failed to send Slack notification: {response.status_code}")
                print(response.text)
                return False
        except Exception as e:
            print(f"❌ Error sending to Slack: {e}")
            return False


if __name__ == "__main__":
    # Get channel from command line argument
    channel = sys.argv[1] if len(sys.argv) > 1 else "#qa-automation"
    
    # Create reporter and send
    reporter = SlackReporter()
    message = reporter.send_to_slack(channel)
    
    if message:
        # In Jenkins, the webhook URL will be provided as environment variable
        webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        if webhook_url:
            reporter.send_via_webhook(webhook_url, message)
        else:
            # Just output the message for debugging
            print(json.dumps(message, indent=2))
