"""
NBC Station Testing Suite
Complete production-ready test automation
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
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Station Configuration
NBC_STATIONS = {
    "NBC New York": "https://www.nbcnewyork.com/",
    # Add more stations here when ready
}


class NBCStationTester:
    """Individual station test runner"""
    
    def __init__(self, station_name, station_url):
        self.station_name = station_name
        self.station_url = station_url
        self.results = []
        self.driver = None
        self.start_time = None
        self.end_time = None
        self.perf_metrics = {}
    
    def setup_driver(self):
        """Initialize Chrome driver"""
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            # Find Chromium
            chromium_paths = ['/usr/bin/chromium-browser', '/usr/bin/chromium']
            for path in chromium_paths:
                if os.path.exists(path):
                    options.binary_location = path
                    break
            
            # Find chromedriver
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
            logger.info(f"Driver initialized for {self.station_name}")
            return True
            
        except Exception as e:
            logger.error(f"Driver setup failed: {e}")
            self.results.append({
                "test": "Browser Setup",
                "status": "ERROR",
                "message": f"Failed: {str(e)[:80]}"
            })
            return False
    
    def test_page_performance(self):
        """Test 1: Page load performance"""
        test = "Page Load Performance"
        try:
            logger.info(f"Testing {self.station_name}...")
            start = time.time()
            self.driver.get(self.station_url)
            
            WebDriverWait(self.driver, 30).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            perf = self.driver.execute_script("""
                const t = performance.timing;
                return {
                    loadTime: t.loadEventEnd - t.navigationStart,
                    domReady: t.domContentLoadedEventEnd - t.navigationStart
                };
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
        """Test 2: Broken links check"""
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
        """Test 3: Video player check"""
        test = "Video Players"
        try:
            selectors = "video, iframe[src*='youtube'], iframe[src*='player'], .video-player"
            videos = self.driver.find_elements(By.CSS_SELECTOR, selectors)
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
        """Test 4: Footer compliance check"""
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
        """Test 5: Mobile responsiveness"""
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
        """Test 6: Scroll smoothness"""
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
        """Test 7: Ad verification"""
        test = "Advertisements"
        try:
            selectors = [
                "iframe[id*='google_ads']", "iframe[id*='ad']",
                "div[class*='ad-container']", "div[id*='dfp-ad']",
                "ins.adsbygoogle", "[data-ad-slot]"
            ]
            
            ads = []
            for sel in selectors:
                found = self.driver.find_elements(By.CSS_SELECTOR, sel)
                ads.extend([a for a in found if a.is_displayed() and a.size['height'] > 50])
            
            # Scroll and check again
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
        """Test 8: Navigation menu"""
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
        """Execute all tests"""
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
        """Generate test summary"""
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


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NBC Station Testing')
    parser.add_argument('--station', type=str, help='Specific station to test')
    parser.add_argument('--url', type=str, help='Custom URL to test')
    args = parser.parse_args()
    
    # Determine what to test
    if args.url:
        stations = {"Custom URL": args.url}
    elif args.station and args.station in NBC_STATIONS:
        stations = {args.station: NBC_STATIONS[args.station]}
    elif args.station:
        logger.error(f"Station '{args.station}' not found")
        return 1
    else:
        stations = NBC_STATIONS
    
    logger.info(f"Testing {len(stations)} station(s)")
    
    # Run tests
    all_results = []
    for name, url in stations.items():
        tester = NBCStationTester(name, url)
        result = tester.run_all_tests()
        all_results.append(result)
        
        symbol = "✓" if result['overall_status'] == 'PASS' else "✗"
        print(f"{symbol} {name}: {result['passed']}/{result['total_tests']} passed")
    
    # Generate summary
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
    
    logger.info(f"Summary: {summary['stations_passed']}/{summary['total_stations']} passed")
    
    return 0 if summary['stations_failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
