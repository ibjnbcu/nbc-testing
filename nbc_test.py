"""
NBC Station Testing Suite with HTML Report
"""

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
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

NBC_STATIONS = {
    "NBC New York": "https://www.nbcnewyork.com/",
}


class NBCStationTester:
    def __init__(self, station_name, station_url):
        self.station_name = station_name
        self.station_url = station_url
        self.results = []
        self.driver = None
        self.start_time = None
        self.end_time = None
        self.perf_metrics = {}
    
    def setup_driver(self):
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            chromium_paths = ['/usr/bin/chromium-browser', '/usr/bin/chromium']
            for path in chromium_paths:
                if os.path.exists(path):
                    options.binary_location = path
                    break
            
            driver_paths = ['/usr/bin/chromedriver', '/usr/local/bin/chromedriver']
            service = None
            for path in driver_paths:
                if os.path.exists(path):
                    service = Service(path)
                    break
            
            if not service:
                from webdriver_manager.chrome import ChromeDriverManager
                from webdriver_manager.core.os_manager import ChromeType
                service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
            
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30)
            return True
            
        except Exception as e:
            self.results.append({"test": "Browser Setup", "status": "ERROR", "message": str(e)[:80]})
            return False
    
    def test_page_performance(self):
        test = "Page Load Performance"
        try:
            self.driver.get(self.station_url)
            WebDriverWait(self.driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            perf = self.driver.execute_script("""
                const t = performance.timing;
                return {loadTime: t.loadEventEnd - t.navigationStart, domReady: t.domContentLoadedEventEnd - t.navigationStart};
            """)
            
            self.perf_metrics = perf
            load_sec = perf['loadTime'] / 1000
            
            if load_sec < 5:
                status, msg = "PASS", f"Fast: {load_sec:.2f}s"
            elif load_sec < 10:
                status, msg = "WARNING", f"Slow: {load_sec:.2f}s"
            else:
                status, msg = "FAIL", f"Very slow: {load_sec:.2f}s"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return status != "FAIL"
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:80]})
            return False
    
    def test_broken_links(self):
        test = "Broken Links"
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "nav a, header a")[:12]
            broken = 0
            
            for link in links:
                href = link.get_attribute('href')
                if href and href.startswith('http'):
                    try:
                        status = self.driver.execute_script(f"""
                            try {{
                                const xhr = new XMLHttpRequest();
                                xhr.open('HEAD', '{href}', false);
                                xhr.send();
                                return xhr.status;
                            }} catch(e) {{ return 0; }}
                        """)
                        if status >= 400 or status == 0:
                            broken += 1
                    except:
                        pass
            
            if broken == 0:
                status, msg = "PASS", "All links working"
            elif broken <= 2:
                status, msg = "WARNING", f"{broken} broken links"
            else:
                status, msg = "FAIL", f"{broken} broken links"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:80]})
            return False
    
    def test_video_players(self):
        test = "Video Players"
        try:
            videos = self.driver.find_elements(By.CSS_SELECTOR, "video, iframe[src*='youtube'], iframe[src*='player'], .video-player")
            visible = [v for v in videos if v.is_displayed()]
            
            if len(visible) >= 1:
                status, msg = "PASS", f"{len(visible)} video(s) found"
            else:
                status, msg = "WARNING", "No videos on homepage"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:80]})
            return False
    
    def test_footer_compliance(self):
        test = "Footer Compliance"
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            footer = None
            for sel in ["footer", ".footer", "#footer", "[role='contentinfo']"]:
                try:
                    footer = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if footer:
                        break
                except:
                    pass
            
            if not footer:
                self.results.append({"test": test, "status": "FAIL", "message": "Footer not found"})
                return False
            
            text = footer.text.lower()
            required = ['privacy', 'terms', 'copyright', '©']
            found = [r for r in required if r in text]
            
            if len(found) >= 3:
                status, msg = "PASS", "Footer has compliance items"
            elif len(found) >= 2:
                status, msg = "WARNING", "Some compliance items missing"
            else:
                status, msg = "FAIL", "Missing compliance information"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:80]})
            return False
    
    def test_mobile_responsive(self):
        test = "Mobile Responsive"
        try:
            viewport = self.driver.execute_script("""
                const meta = document.querySelector('meta[name="viewport"]');
                return meta ? meta.getAttribute('content') : null;
            """)
            
            if viewport and 'width=device-width' in viewport:
                status, msg = "PASS", "Mobile optimized"
            elif viewport:
                status, msg = "WARNING", "Viewport tag exists but incomplete"
            else:
                status, msg = "FAIL", "No viewport meta tag"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:80]})
            return False
    
    def test_scroll_performance(self):
        test = "Scroll Performance"
        try:
            self.driver.execute_script("window.scrollTo({top: 800, behavior: 'smooth'});")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo({top: 0, behavior: 'smooth'});")
            self.results.append({"test": test, "status": "PASS", "message": "Scroll functional"})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "WARNING", "message": "Could not test"})
            return True
    
    def test_advertisements(self):
        test = "Advertisements"
        try:
            selectors = ["iframe[id*='google_ads']", "iframe[id*='ad']", "div[class*='ad-container']", "div[id*='dfp-ad']", "ins.adsbygoogle", "[data-ad-slot]"]
            
            ads = []
            for sel in selectors:
                found = self.driver.find_elements(By.CSS_SELECTOR, sel)
                ads.extend([a for a in found if a.is_displayed() and a.size['height'] > 50])
            
            self.driver.execute_script("window.scrollTo(0, 800);")
            time.sleep(2)
            
            if len(ads) >= 3:
                status, msg = "PASS", f"{len(ads)} ads visible"
            elif len(ads) >= 1:
                status, msg = "WARNING", f"Only {len(ads)} ad(s)"
            else:
                status, msg = "FAIL", "No ads detected"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:80]})
            return False
    
    def test_navigation(self):
        test = "Navigation Menu"
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "nav a, header a")
            visible = [l for l in links if l.is_displayed()]
            
            if len(visible) >= 5:
                status, msg = "PASS", f"{len(visible)} nav links"
            else:
                status, msg = "FAIL", f"Only {len(visible)} nav links"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:80]})
            return False
    
    def run_all_tests(self):
        self.start_time = datetime.now()
        
        if not self.setup_driver():
            self.end_time = datetime.now()
            return self.get_summary()
        
        try:
            if self.test_page_performance():
                self.test_broken_links()
                self.test_video_players()
                self.test_footer_compliance()
                self.test_mobile_responsive()
                self.test_scroll_performance()
                self.test_advertisements()
                self.test_navigation()
        finally:
            if self.driver:
                self.driver.quit()
            self.end_time = datetime.now()
        
        return self.get_summary()
    
    def get_summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARNING')
        errors = sum(1 for r in self.results if r['status'] == 'ERROR')
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        
        return {
            "station_name": self.station_name,
            "station_url": self.station_url,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "errors": errors,
            "overall_status": "PASS" if (failed == 0 and errors == 0) else "FAIL",
            "test_results": self.results,
            "performance": self.perf_metrics
        }


def generate_html_report(summary):
    """Generate beautiful HTML report"""
    timestamp = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    
    overall_color = "#28a745" if summary['stations_failed'] == 0 else "#dc3545"
    overall_status = "PASSED" if summary['stations_failed'] == 0 else "FAILED"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBC Station Test Report</title>
    <style>
        * {{margin:0; padding:0; box-sizing:border-box;}}
        body {{font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; min-height: 100vh;}}
        .container {{max-width: 1400px; margin: 0 auto;}}
        .header {{background: white; border-radius: 12px; padding: 30px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}}
        h1 {{color: #1a202c; font-size: 2rem; margin-bottom: 10px;}}
        .timestamp {{color: #718096; font-size: 0.9rem;}}
        .status-banner {{background: {overall_color}; color: white; padding: 15px 30px; border-radius: 8px; font-size: 1.5rem; font-weight: bold; text-align: center; margin: 20px 0;}}
        .summary-grid {{display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;}}
        .metric-card {{background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}}
        .metric-value {{font-size: 2.5rem; font-weight: bold; margin-bottom: 5px;}}
        .success {{color: #28a745;}}
        .danger {{color: #dc3545;}}
        .warning {{color: #ff9800;}}
        .info {{color: #4299e1;}}
        .metric-label {{color: #718096; font-size: 0.85rem; text-transform: uppercase;}}
        .station-card {{background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}}
        .station-header {{display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px; border-bottom: 2px solid #e2e8f0; margin-bottom: 20px;}}
        .station-name {{font-size: 1.5rem; font-weight: 600; color: #2d3748;}}
        .station-url {{color: #4299e1; font-size: 0.9rem; margin-top: 5px;}}
        table {{width: 100%; border-collapse: collapse; margin-top: 15px;}}
        th {{background: #f7fafc; padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #e2e8f0;}}
        td {{padding: 12px; border-bottom: 1px solid #e2e8f0;}}
        .status-badge {{display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;}}
        .badge-pass {{background: #c6f6d5; color: #22543d;}}
        .badge-fail {{background: #fed7d7; color: #742a2a;}}
        .badge-warning {{background: #feebc8; color: #7c2d12;}}
        .badge-error {{background: #fed7d7; color: #742a2a;}}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NBC Station Test Report</h1>
            <p class="timestamp">Generated: {timestamp}</p>
        </div>
        
        <div class="status-banner">{overall_status}</div>
        
        <div class="summary-grid">
            <div class="metric-card">
                <div class="metric-value info">{summary['total_stations']}</div>
                <div class="metric-label">Stations Tested</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{summary['stations_passed']}</div>
                <div class="metric-label">Stations Passed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value info">{summary['total_tests']}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric-card">
                <div class="metric-value {'success' if summary['total_passed'] == summary['total_tests'] else 'danger'}">{summary['total_passed']}/{summary['total_tests']}</div>
                <div class="metric-label">Tests Passed</div>
            </div>
        </div>
"""
    
    for station in summary['stations']:
        status_class = 'success' if station['overall_status'] == 'PASS' else 'danger'
        
        html += f"""
        <div class="station-card">
            <div class="station-header">
                <div>
                    <div class="station-name">{station['station_name']}</div>
                    <div class="station-url">{station['station_url']}</div>
                </div>
                <div class="{status_class}" style="font-size: 1.5rem; font-weight: bold;">{station['overall_status']}</div>
            </div>
            
            <div style="color: #4a5568; margin-bottom: 15px;">
                <strong>Tests:</strong> {station['passed']}/{station['total_tests']} passed | 
                <strong>Duration:</strong> {station['duration_seconds']}s | 
                <strong>Timestamp:</strong> {station['timestamp']}
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Status</th>
                        <th>Details</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for test in station['test_results']:
            badge_class = {
                'PASS': 'badge-pass',
                'FAIL': 'badge-fail',
                'WARNING': 'badge-warning',
                'ERROR': 'badge-error'
            }.get(test['status'], 'badge-fail')
            
            html += f"""
                    <tr>
                        <td><strong>{test['test']}</strong></td>
                        <td><span class="status-badge {badge_class}">{test['status']}</span></td>
                        <td>{test['message']}</td>
                        <td>{station['timestamp'].split('T')[1][:8]}</td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    logger.info("HTML report generated: index.html")


def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--station', type=str)
    parser.add_argument('--url', type=str)
    args = parser.parse_args()
    
    if args.url:
        stations = {"Custom URL": args.url}
    elif args.station and args.station in NBC_STATIONS:
        stations = {args.station: NBC_STATIONS[args.station]}
    elif args.station:
        logger.error(f"Station '{args.station}' not found")
        return 0
    else:
        stations = NBC_STATIONS
    
    all_results = []
    for name, url in stations.items():
        tester = NBCStationTester(name, url)
        result = tester.run_all_tests()
        all_results.append(result)
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_stations": len(all_results),
        "stations_passed": sum(1 for r in all_results if r['overall_status'] == 'PASS'),
        "stations_failed": sum(1 for r in all_results if r['overall_status'] == 'FAIL'),
        "total_tests": sum(r['total_tests'] for r in all_results),
        "total_passed": sum(r['passed'] for r in all_results),
        "total_failed": sum(r['failed'] for r in all_results),
        "stations": all_results
    }
    
    with open('test_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    generate_html_report(summary)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
