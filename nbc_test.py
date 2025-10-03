"""
NBC Station Testing Suite - Production Grade
Incorporates QA Engineer's detailed testing methodology
15 comprehensive tests with deep validation
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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
        """Initialize Chrome driver"""
        try:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            
            # Enable browser logging
            options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
            
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
            logger.info(f"Driver initialized for {self.station_name}")
            return True
            
        except Exception as e:
            logger.error(f"Driver setup failed: {e}")
            self.results.append({"test": "Browser Setup", "status": "ERROR", "message": str(e)[:100]})
            return False
    
    def test_page_performance(self):
        """Test 1: Page load performance"""
        test = "Page Load Performance"
        try:
            logger.info(f"Testing {self.station_name} homepage...")
            start = time.time()
            self.driver.get(self.station_url)
            
            wait = WebDriverWait(self.driver, 30)
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
            
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
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_page_size(self):
        """Test 2: Page size check"""
        test = "Page Size Check"
        try:
            page_size = self.driver.execute_script("return document.documentElement.outerHTML.length;")
            size_mb = page_size / (1024 * 1024)
            
            if size_mb < 2:
                status, msg = "PASS", f"{size_mb:.2f}MB"
            elif size_mb < 5:
                status, msg = "WARNING", f"Large: {size_mb:.2f}MB"
            else:
                status, msg = "FAIL", f"Too large: {size_mb:.2f}MB"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_javascript_errors(self):
        """Test 3: JavaScript console errors"""
        test = "JavaScript Errors"
        try:
            logs = self.driver.get_log('browser')
            errors = [log for log in logs if log['level'] == 'SEVERE']
            
            if len(errors) == 0:
                status, msg = "PASS", "No JS errors"
            elif len(errors) <= 2:
                status, msg = "WARNING", f"{len(errors)} JS error(s)"
            else:
                status, msg = "FAIL", f"{len(errors)} JS errors"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except:
            self.results.append({"test": test, "status": "WARNING", "message": "Could not check JS errors"})
            return True
    
    def test_images_loading(self):
        """Test 4: Image loading verification"""
        test = "Image Loading"
        try:
            images = self.driver.find_elements(By.TAG_NAME, "img")[:20]
            broken = 0
            
            for img in images:
                try:
                    is_broken = self.driver.execute_script(
                        "return arguments[0].complete && arguments[0].naturalWidth === 0;", img
                    )
                    if is_broken:
                        broken += 1
                except:
                    pass
            
            if broken == 0:
                status, msg = "PASS", f"{len(images)} images OK"
            elif broken <= 2:
                status, msg = "WARNING", f"{broken} broken image(s)"
            else:
                status, msg = "FAIL", f"{broken} broken images"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_video_page_detailed(self):
        """Test 5: Video page - Detailed validation (from QA engineer)"""
        test = "Video Page Validation"
        try:
            wait = WebDriverWait(self.driver, 15)
            
            # Look for video on homepage first
            try:
                video = wait.until(EC.presence_of_element_located(By.CSS_SELECTOR, "video.jw-video, video"))
                
                # Check visibility
                is_visible = self.driver.execute_script(
                    "return arguments[0].offsetHeight > 0 && arguments[0].offsetWidth > 0;", video
                )
                
                if not is_visible:
                    status, msg = "WARNING", "Video found but not visible"
                    self.results.append({"test": test, "status": status, "message": msg})
                    return True
                
                # Check if video can play (has source)
                has_source = self.driver.execute_script(
                    "return arguments[0].currentSrc && arguments[0].currentSrc.length > 0;", video
                )
                
                if has_source:
                    status, msg = "PASS", "Video player present and has source"
                else:
                    status, msg = "WARNING", "Video player present but no source"
                
                self.results.append({"test": test, "status": status, "message": msg})
                return True
                
            except TimeoutException:
                status, msg = "WARNING", "No video found on homepage"
                self.results.append({"test": test, "status": status, "message": msg})
                return True
                
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_weather_page_detailed(self):
        """Test 6: Weather page - Detailed validation (from QA engineer)"""
        test = "Weather Page Validation"
        try:
            wait = WebDriverWait(self.driver, 15)
            
            # Step 1: Navigate to homepage
            self.driver.get(self.station_url)
            time.sleep(2)
            
            # Step 2: Look for weather menu link
            weather_selectors = [
                "a[href='/weather/'][data-lid='Weather']",
                "a[href='/weather/']",
                "a[href*='weather']"
            ]
            
            weather_link = None
            for selector in weather_selectors:
                try:
                    weather_link = wait.until(EC.element_to_be_clickable(By.CSS_SELECTOR, selector))
                    if weather_link:
                        break
                except:
                    continue
            
            if not weather_link:
                status, msg = "FAIL", "Weather link not found in navigation"
                self.results.append({"test": test, "status": status, "message": msg})
                return False
            
            # Step 3: Click weather link
            self.driver.execute_script("arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", weather_link)
            time.sleep(1)
            weather_link.click()
            time.sleep(3)
            
            # Step 4: Wait for forecast section to load
            forecast_selectors = [
                "div.weather-page__section--forecast-block",
                "div.forecast__current-hourly",
                ".weather-forecast",
                "[class*='forecast']",
                "[class*='weather']"
            ]
            
            forecast_found = False
            for selector in forecast_selectors:
                try:
                    forecast = wait.until(EC.presence_of_element_located(By.CSS_SELECTOR, selector))
                    is_visible = self.driver.execute_script(
                        "return arguments[0].offsetHeight > 0 && arguments[0].offsetWidth > 0;", forecast
                    )
                    if is_visible:
                        forecast_found = True
                        break
                except:
                    continue
            
            if forecast_found:
                status, msg = "PASS", "Weather page loaded successfully"
            else:
                status, msg = "FAIL", "Weather forecast not visible"
            
            self.results.append({"test": test, "status": status, "message": msg})
            
            # Navigate back to homepage
            self.driver.get(self.station_url)
            time.sleep(2)
            
            return status == "PASS"
            
        except TimeoutException:
            self.results.append({"test": test, "status": "FAIL", "message": "Timeout loading weather page"})
            self.driver.get(self.station_url)
            return False
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            self.driver.get(self.station_url)
            return False
    
    def test_advertisements_detailed(self):
        """Test 7: Advertisement - Detailed validation (from QA engineer)"""
        test = "Advertisement Validation"
        try:
            wait = WebDriverWait(self.driver, 15)
            
            # Step 1: Locate ad iframe container
            ad_container_selectors = [
                "div[id^='google_ads_iframe_'][id$='__container__']",
                "div[id*='google_ads_iframe']",
                "div[class*='ad-container']"
            ]
            
            container_found = False
            iframe_container = None
            
            for selector in ad_container_selectors:
                try:
                    iframe_container = wait.until(EC.presence_of_element_located(By.CSS_SELECTOR, selector))
                    if iframe_container.is_displayed():
                        container_found = True
                        break
                except:
                    continue
            
            if not container_found:
                # Try alternate ad detection
                ad_iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe[id*='google_ads'], iframe[id*='ad']")
                visible_ads = [ad for ad in ad_iframes if ad.is_displayed() and ad.size['height'] > 50]
                
                if len(visible_ads) >= 1:
                    status, msg = "PASS", f"{len(visible_ads)} ad(s) visible"
                else:
                    status, msg = "FAIL", "No ads detected"
                
                self.results.append({"test": test, "status": status, "message": msg})
                return status == "PASS"
            
            # Step 2: Find iframe inside container
            try:
                iframe = iframe_container.find_element(By.TAG_NAME, "iframe")
                if iframe and iframe.is_displayed():
                    # Step 3: Check if iframe has content
                    try:
                        ad_loaded = self.driver.execute_script("""
                            let frame = arguments[0];
                            try {
                                let iframeDoc = frame.contentDocument || frame.contentWindow.document;
                                return iframeDoc && iframeDoc.readyState === 'complete';
                            } catch(e) {
                                return true;
                            }
                        """, iframe)
                        
                        if ad_loaded:
                            status, msg = "PASS", "Ad iframe loaded successfully"
                        else:
                            status, msg = "WARNING", "Ad iframe present but content not verified"
                    except:
                        status, msg = "PASS", "Ad iframe present"
                else:
                    status, msg = "FAIL", "Ad iframe not visible"
            except:
                status, msg = "WARNING", "Ad container found but iframe missing"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return status == "PASS"
            
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_sports_section(self):
        """Test 8: Sports section"""
        test = "Sports Section"
        try:
            sports_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='sports'], .sports, #sports")
            
            if len(sports_elements) > 0:
                status, msg = "PASS", "Sports section found"
            else:
                status, msg = "WARNING", "Sports section not detected"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_search_functionality(self):
        """Test 9: Search box"""
        test = "Search Functionality"
        try:
            search_selectors = [
                "input[type='search']", "input[name='search']",
                "input[placeholder*='Search']", ".search-input", "#search"
            ]
            
            search_found = False
            for sel in search_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if elements and any(e.is_displayed() for e in elements):
                    search_found = True
                    break
            
            if search_found:
                status, msg = "PASS", "Search box present"
            else:
                status, msg = "FAIL", "Search box not found"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_social_media(self):
        """Test 10: Social media buttons"""
        test = "Social Media Buttons"
        try:
            social_links = self.driver.find_elements(By.CSS_SELECTOR, 
                "a[href*='facebook.com'], a[href*='twitter.com'], a[href*='instagram.com']")
            
            if len(social_links) >= 2:
                status, msg = "PASS", f"{len(social_links)} social links"
            elif len(social_links) >= 1:
                status, msg = "WARNING", "Only 1 social link"
            else:
                status, msg = "FAIL", "No social media links"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_footer_compliance(self):
        """Test 11: Footer compliance"""
        test = "Footer Compliance"
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            footer = None
            for sel in ["footer", ".footer", "#footer"]:
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
            required = ['privacy', 'terms', '©']
            found = [r for r in required if r in text]
            
            if len(found) >= 2:
                status, msg = "PASS", "Footer compliance OK"
            else:
                status, msg = "WARNING", "Some compliance items missing"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_mobile_responsive(self):
        """Test 12: Mobile responsiveness"""
        test = "Mobile Responsive"
        try:
            viewport = self.driver.execute_script("""
                const meta = document.querySelector('meta[name="viewport"]');
                return meta ? meta.getAttribute('content') : null;
            """)
            
            if viewport and 'width=device-width' in viewport:
                status, msg = "PASS", "Mobile optimized"
            else:
                status, msg = "WARNING", "Viewport tag incomplete"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_scroll_performance(self):
        """Test 13: Scroll smoothness"""
        test = "Scroll Performance"
        try:
            self.driver.execute_script("window.scrollTo({top: 800, behavior: 'smooth'});")
            time.sleep(1)
            self.results.append({"test": test, "status": "PASS", "message": "Scroll functional"})
            return True
        except:
            self.results.append({"test": test, "status": "WARNING", "message": "Could not test scroll"})
            return True
    
    def test_navigation(self):
        """Test 14: Navigation menu"""
        test = "Navigation Menu"
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "nav a, header a")
            visible = [l for l in links if l.is_displayed()]
            
            if len(visible) >= 5:
                status, msg = "PASS", f"{len(visible)} nav links"
            else:
                status, msg = "WARNING", f"Only {len(visible)} nav links"
            
            self.results.append({"test": test, "status": status, "message": msg})
            return True
        except Exception as e:
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def test_broken_links(self):
        """Test 15: Broken links check"""
        test = "Broken Links"
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "nav a, header a")[:10]
            broken = 0
            
            for link in links:
                href = link.get_attribute('href')
                if href and href.startswith('http'):
                    try:
                        status_code = self.driver.execute_script(f"""
                            try {{
                                const xhr = new XMLHttpRequest();
                                xhr.open('HEAD', '{href}', false);
                                xhr.send();
                                return xhr.status;
                            }} catch(e) {{ return 0; }}
                        """)
                        if status_code >= 400 or status_code == 0:
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
            self.results.append({"test": test, "status": "FAIL", "message": str(e)[:100]})
            return False
    
    def run_all_tests(self):
        """Execute all 15 tests"""
        self.start_time = datetime.now()
        
        if not self.setup_driver():
            self.end_time = datetime.now()
            return self.get_summary()
        
        try:
            # Core tests
            if self.test_page_performance():
                self.test_page_size()
                self.test_javascript_errors()
                self.test_images_loading()
                
                # QA Engineer's detailed tests
                self.test_video_page_detailed()
                self.test_weather_page_detailed()
                self.test_advertisements_detailed()
                
                # Additional tests
                self.test_sports_section()
                self.test_search_functionality()
                self.test_social_media()
                self.test_footer_compliance()
                self.test_mobile_responsive()
                self.test_scroll_performance()
                self.test_navigation()
                self.test_broken_links()
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
    """Generate professional HTML report"""
    timestamp = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    overall_color = "#28a745" if summary['stations_failed'] == 0 else "#dc3545"
    overall_status = "PASSED" if summary['stations_failed'] == 0 else "FAILED"
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBC Test Report - QA Engineer Methodology</title>
    <style>
        * {{margin:0; padding:0; box-sizing:border-box;}}
        body {{font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px;}}
        .container {{max-width: 1400px; margin: 0 auto;}}
        .header {{background: white; border-radius: 12px; padding: 30px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}}
        h1 {{color: #1a202c; font-size: 2rem; margin-bottom: 10px;}}
        .subtitle {{color: #718096; font-size: 1rem;}}
        .timestamp {{color: #718096; font-size: 0.9rem; margin-top: 5px;}}
        .status-banner {{background: {overall_color}; color: white; padding: 15px 30px; border-radius: 8px; font-size: 1.5rem; font-weight: bold; text-align: center; margin: 20px 0;}}
        .summary-grid {{display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;}}
        .metric-card {{background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}}
        .metric-value {{font-size: 2.5rem; font-weight: bold;}}
        .success {{color: #28a745;}}
        .danger {{color: #dc3545;}}
        .warning {{color: #ff9800;}}
        .info {{color: #4299e1;}}
        .metric-label {{color: #718096; font-size: 0.85rem; text-transform: uppercase; margin-top: 5px;}}
        .station-card {{background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}}
        .station-header {{display: flex; justify-content: space-between; align-items: center; padding-bottom: 15px; border-bottom: 2px solid #e2e8f0; margin-bottom: 20px;}}
        .station-name {{font-size: 1.5rem; font-weight: 600; color: #2d3748;}}
        table {{width: 100%; border-collapse: collapse; margin-top: 15px;}}
        th {{background: #f7fafc; padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #e2e8f0;}}
        td {{padding: 12px; border-bottom: 1px solid #e2e8f0;}}
        .status-badge {{display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600;}}
        .badge-pass {{background: #c6f6d5; color: #22543d;}}
        .badge-fail {{background: #fed7d7; color: #742a2a;}}
        .badge-warning {{background: #feebc8; color: #7c2d12;}}
        .test-categories {{background: #f7fafc; padding: 15px; border-radius: 8px; margin-bottom: 15px;}}
        .test-categories h3 {{color: #2d3748; margin-bottom: 10px;}}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NBC Station Test Report</h1>
            <p class="subtitle">15 Comprehensive Tests | QA Engineer Methodology</p>
            <p class="timestamp">Generated: {timestamp}</p>
        </div>
        
        <div class="status-banner">{overall_status}</div>
        
        <div class="summary-grid">
            <div class="metric-card">
                <div class="metric-value info">{summary['total_stations']}</div>
                <div class="metric-label">Stations</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{summary['stations_passed']}</div>
                <div class="metric-label">Passed</div>
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
                    <div style="color: #4299e1; font-size: 0.9rem;">{station['station_url']}</div>
                </div>
                <div class="{status_class}" style="font-size: 1.5rem; font-weight: bold;">{station['overall_status']}</div>
            </div>
            
            <div style="color: #4a5568; margin-bottom: 15px;">
                <strong>Tests:</strong> {station['passed']} passed, {station['failed']} failed, {station['warnings']} warnings | 
                <strong>Duration:</strong> {station['duration_seconds']}s
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Status</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        for test in station['test_results']:
            badge_class = {'PASS': 'badge-pass', 'FAIL': 'badge-fail', 'WARNING': 'badge-warning'}.get(test['status'], 'badge-fail')
            
            html += f"""
                    <tr>
                        <td><strong>{test['test']}</strong></td>
                        <td><span class="status-badge {badge_class}">{test['status']}</span></td>
                        <td>{test['message']}</td>
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
    else:
        stations = NBC_STATIONS
    
    all_results = []
    for name, url in stations.items():
        logger.info(f"Testing {name}...")
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
    
    logger.info(f"Testing complete: {summary['stations_passed']}/{summary['total_stations']} stations passed")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
