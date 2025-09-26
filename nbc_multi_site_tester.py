"""
NBC Multi-Site Testing Suite 
"""

import os
import time
import json
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging with thread safety
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
print_lock = threading.Lock()

def safe_print(message):
    """Thread-safe printing"""
    with print_lock:
        print(message)

# NBC SITES CONFIGURATION
NBC_SITES = {
    # NBC Owned & Operated Stations
    "New York": "https://www.nbcnewyork.com/",
       
}


class NBCSiteTester:
    """Test suite for individual NBC site"""
    
    def __init__(self, site_name, site_url, timeout=20):
        self.site_name = site_name
        self.site_url = site_url
        self.timeout = timeout
        self.results = []
        self.start_time = None
        self.end_time = None
        self.driver = None
        self.wait = None
        self.performance_data = {}
        
    def create_driver(self):
        """Create Chrome driver with production-ready settings"""
        try:
            # Chrome options optimized for CI/CD
            options = Options()
            options.add_argument("--headless=new")  # New headless mode
            options.add_argument("--no-sandbox")  # Required for Docker/CI
            options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-gpu")  # Applicable to Windows, harmless on Linux
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            
            # Performance improvements
            prefs = {
                "profile.default_content_setting_values": {
                    "images": 2,  # Block images for faster loading
                    "plugins": 2,  # Block plugins
                    "popups": 2,  # Block popups
                    "geolocation": 2,  # Block location
                    "notifications": 2,  # Block notifications
                    "media_stream": 2,  # Block media stream
                }
            }
            options.add_experimental_option("prefs", prefs)
            
            # Auto-install ChromeDriver
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(self.timeout)
            self.wait = WebDriverWait(self.driver, self.timeout)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create driver for {self.site_name}: {str(e)}")
            self.results.append({
                "test": "Driver Setup",
                "status": "ERROR",
                "details": f"Failed to initialize Chrome driver: {str(e)[:100]}"
            })
            return False
    
    def test_homepage_loads(self):
        """Test if homepage loads successfully with performance metrics"""
        test_name = "Homepage Load"
        try:
            # Navigate and measure performance
            self.driver.get(self.site_url)
            
            # Wait for page to be interactive
            self.wait.until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Get performance metrics using Navigation Timing API
            performance_metrics = self.driver.execute_script("""
                const timing = window.performance.timing;
                return {
                    loadTime: timing.loadEventEnd - timing.navigationStart,
                    domContentLoaded: timing.domContentLoadedEventEnd - timing.navigationStart,
                    responseTime: timing.responseEnd - timing.requestStart,
                    renderTime: timing.domComplete - timing.domLoading
                };
            """)
            
            # Store performance data for later use
            self.performance_data = performance_metrics
            load_time_seconds = performance_metrics['loadTime'] / 1000
            
            # Check title
            page_title = self.driver.title
            if not page_title:
                raise Exception("No page title found")
            
            # Determine status based on load time
            if load_time_seconds < 5:
                status = "PASS"
                perf_note = "Fast"
            elif load_time_seconds < 10:
                status = "WARNING"
                perf_note = "Slow"
            else:
                status = "WARNING"
                perf_note = "Very Slow"
            
            self.results.append({
                "test": test_name,
                "status": status,
                "details": f"Loaded in {load_time_seconds:.2f}s ({perf_note}). Title: {page_title[:50]}"
            })
            return True
            
        except TimeoutException:
            self.results.append({
                "test": test_name,
                "status": "FAIL",
                "details": f"Page load timeout after {self.timeout}s"
            })
            return False
        except Exception as e:
            self.results.append({
                "test": test_name,
                "status": "FAIL",
                "details": f"Failed to load: {str(e)[:100]}"
            })
            return False
    
    def test_navigation_menu(self):
        """Test navigation menu with proper waits"""
        test_name = "Navigation Menu"
        try:
            # Wait for navigation elements to be present
            nav_elements = self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "nav a, .navigation a, .menu a, header a, [role='navigation'] a")
                )
            )
            
            # Filter visible elements
            visible_nav = [elem for elem in nav_elements if elem.is_displayed()]
            
            if len(visible_nav) >= 3:
                self.results.append({
                    "test": test_name,
                    "status": "PASS",
                    "details": f"Found {len(visible_nav)} navigation links"
                })
            elif len(visible_nav) > 0:
                self.results.append({
                    "test": test_name,
                    "status": "WARNING",
                    "details": f"Only {len(visible_nav)} navigation links found"
                })
            else:
                self.results.append({
                    "test": test_name,
                    "status": "FAIL",
                    "details": "No navigation links found"
                })
            return True
            
        except TimeoutException:
            self.results.append({
                "test": test_name,
                "status": "FAIL",
                "details": "Navigation menu not found within timeout"
            })
            return False
        except Exception as e:
            self.results.append({
                "test": test_name,
                "status": "FAIL",
                "details": str(e)[:100]
            })
            return False
    
    def test_search_functionality(self):
        """Test search feature with improved selectors"""
        test_name = "Search Feature"
        try:
            # Multiple search selectors for different implementations
            search_selectors = [
                "input[type='search']",
                "input[aria-label*='earch' i]",
                "input[placeholder*='earch' i]",
                "button[aria-label*='earch' i]",
                ".search-button",
                ".search-icon",
                "#search"
            ]
            
            search_element = None
            for selector in search_selectors:
                try:
                    search_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if search_element.is_displayed():
                        break
                except:
                    continue
            
            if search_element:
                self.results.append({
                    "test": test_name,
                    "status": "PASS",
                    "details": "Search functionality found"
                })
            else:
                self.results.append({
                    "test": test_name,
                    "status": "WARNING",
                    "details": "No search element detected"
                })
            return True
            
        except Exception as e:
            self.results.append({
                "test": test_name,
                "status": "FAIL",
                "details": str(e)[:100]
            })
            return False
    
    def test_content_presence(self):
        """Test for news content with wait conditions"""
        test_name = "Content Articles"
        try:
            # Wait for content to load
            content_loaded = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "article, .article, .story, h1, h2, .headline, [role='article']")
                )
            )
            
            # Count various content elements
            articles = self.driver.find_elements(By.CSS_SELECTOR, 
                "article, .article, .story, [role='article']")
            headlines = self.driver.find_elements(By.CSS_SELECTOR, 
                "h1, h2, h3, .headline, .title")
            
            total_content = len(articles) + len(headlines)
            
            if total_content >= 10:
                self.results.append({
                    "test": test_name,
                    "status": "PASS",
                    "details": f"Found {len(articles)} articles, {len(headlines)} headlines"
                })
            elif total_content >= 5:
                self.results.append({
                    "test": test_name,
                    "status": "WARNING",
                    "details": f"Limited content: {len(articles)} articles, {len(headlines)} headlines"
                })
            else:
                self.results.append({
                    "test": test_name,
                    "status": "FAIL",
                    "details": f"Insufficient content: only {total_content} items found"
                })
            return True
            
        except TimeoutException:
            self.results.append({
                "test": test_name,
                "status": "FAIL",
                "details": "No content found within timeout"
            })
            return False
        except Exception as e:
            self.results.append({
                "test": test_name,
                "status": "FAIL",
                "details": str(e)[:100]
            })
            return False
    
    def test_footer(self):
        """Test footer with scroll and wait"""
        test_name = "Footer Section"
        try:
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait a moment for lazy-loaded content
            time.sleep(1)
            
            # Look for footer
            footer_selectors = ["footer", ".footer", "#footer", "[role='contentinfo']"]
            footer_found = False
            footer_links = []
            
            for selector in footer_selectors:
                try:
                    footer = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if footer.is_displayed():
                        footer_found = True
                        footer_links = footer.find_elements(By.TAG_NAME, "a")
                        break
                except:
                    continue
            
            if footer_found and len(footer_links) >= 3:
                self.results.append({
                    "test": test_name,
                    "status": "PASS",
                    "details": f"Footer found with {len(footer_links)} links"
                })
            elif footer_found:
                self.results.append({
                    "test": test_name,
                    "status": "WARNING",
                    "details": f"Footer found but only {len(footer_links)} links"
                })
            else:
                self.results.append({
                    "test": test_name,
                    "status": "WARNING",
                    "details": "Footer not detected"
                })
            return True
            
        except Exception as e:
            self.results.append({
                "test": test_name,
                "status": "FAIL",
                "details": str(e)[:100]
            })
            return False
    
    def test_responsive_elements(self):
        """Test key responsive elements"""
        test_name = "Responsive Elements"
        try:
            # Check for mobile menu button (hamburger)
            mobile_menu_selectors = [
                ".mobile-menu", ".hamburger", ".menu-toggle", 
                "[aria-label*='menu' i]", ".nav-toggle"
            ]
            
            mobile_menu_found = False
            for selector in mobile_menu_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if element:
                        mobile_menu_found = True
                        break
                except:
                    continue
            
            # Check viewport meta tag
            viewport = self.driver.find_elements(By.CSS_SELECTOR, "meta[name='viewport']")
            
            if viewport:
                self.results.append({
                    "test": test_name,
                    "status": "PASS",
                    "details": "Responsive viewport meta tag found"
                })
            else:
                self.results.append({
                    "test": test_name,
                    "status": "WARNING",
                    "details": "No viewport meta tag detected"
                })
            return True
            
        except Exception as e:
            self.results.append({
                "test": test_name,
                "status": "FAIL",
                "details": str(e)[:100]
            })
            return False
    
    def run_tests(self):
        """Run all tests for this site with proper error handling"""
        self.start_time = datetime.now()
        
        # Initialize driver
        if not self.create_driver():
            # Driver creation failed, return error summary
            self.end_time = datetime.now()
            return {
                "site_name": self.site_name,
                "site_url": self.site_url,
                "total_tests": 1,
                "passed": 0,
                "failed": 1,
                "warnings": 0,
                "success_rate": 0,
                "test_results": self.results,
                "duration": (self.end_time - self.start_time).total_seconds(),
                "error": "Chrome driver initialization failed"
            }
        
        try:
            # Run test suite
            self.test_homepage_loads()
            
            # Only run other tests if homepage loaded
            if self.results and self.results[0]["status"] != "FAIL":
                self.test_navigation_menu()
                self.test_search_functionality()
                self.test_content_presence()
                self.test_footer()
                self.test_responsive_elements()
            else:
                # Homepage failed, skip other tests
                for test in ["Navigation Menu", "Search Feature", "Content Articles", 
                           "Footer Section", "Responsive Elements"]:
                    self.results.append({
                        "test": test,
                        "status": "SKIP",
                        "details": "Skipped due to homepage load failure"
                    })
            
        except Exception as e:
            logger.error(f"Unexpected error testing {self.site_name}: {str(e)}")
            self.results.append({
                "test": "Test Execution",
                "status": "ERROR",
                "details": f"Unexpected error: {str(e)[:100]}"
            })
            
        finally:
            # Clean up
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
            self.end_time = datetime.now()
            
        return self.get_summary()
    
    def get_summary(self):
        """Generate test summary with performance data"""
        total = len(self.results)
        passed = len([r for r in self.results if r["status"] == "PASS"])
        failed = len([r for r in self.results if r["status"] in ["FAIL", "ERROR"]])
        warnings = len([r for r in self.results if r["status"] == "WARNING"])
        skipped = len([r for r in self.results if r["status"] == "SKIP"])
        
        summary = {
            "site_name": self.site_name,
            "site_url": self.site_url,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "skipped": skipped,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "test_results": self.results,
            "duration": (self.end_time - self.start_time).total_seconds() if self.end_time else 0,
            "performance": self.performance_data
        }
        
        return summary


class NBCMultiSiteTester:
    """Main orchestrator for testing all NBC sites"""
    
    def __init__(self, max_workers=5, sites_to_test=None):
        """
        Initialize multi-site tester
        max_workers: number of parallel threads (recommend 5 for CI/CD)
        sites_to_test: list of site names or None for all sites
        """
        self.max_workers = min(max_workers, 10)  # Cap at 10 for stability
        self.sites_to_test = sites_to_test or NBC_SITES
        self.all_results = []
        self.start_time = datetime.now()
        
    def test_single_site(self, site_name, site_url):
        """Test a single site with error handling"""
        safe_print(f"🔍 Testing {site_name}...")
        try:
            tester = NBCSiteTester(site_name, site_url)
            return tester.run_tests()
        except Exception as e:
            logger.error(f"Fatal error testing {site_name}: {str(e)}")
            return {
                "site_name": site_name,
                "site_url": site_url,
                "total_tests": 1,
                "passed": 0,
                "failed": 1,
                "warnings": 0,
                "success_rate": 0,
                "test_results": [{
                    "test": "Site Test",
                    "status": "ERROR",
                    "details": f"Fatal error: {str(e)[:100]}"
                }],
                "duration": 0,
                "error": str(e)
            }
    
    def run_all_tests(self):
        """Run tests on all NBC sites with improved parallel execution"""
        safe_print(f"\n🚀 Starting tests for {len(self.sites_to_test)} NBC websites...")
        safe_print(f"📊 Using {self.max_workers} parallel workers\n")
        safe_print("="*60)
        
        # Run tests in parallel with thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.test_single_site, name, url): name 
                for name, url in self.sites_to_test.items()
            }
            
            completed = 0
            total = len(futures)
            
            # Process completed futures
            for future in as_completed(futures):
                completed += 1
                site_name = futures[future]
                
                try:
                    result = future.result(timeout=60)  # 60 second timeout per site
                    self.all_results.append(result)
                    
                    # Determine status icon
                    if result['failed'] > 0 or result.get('error'):
                        status = "❌"
                    elif result['warnings'] > 0:
                        status = "⚠️"
                    else:
                        status = "✅"
                    
                    # Print progress
                    safe_print(
                        f"[{completed}/{total}] {status} {site_name} - "
                        f"Passed: {result['passed']}/{result['total_tests']} "
                        f"({result['duration']:.1f}s)"
                    )
                    
                except Exception as e:
                    safe_print(f"[{completed}/{total}] ❌ {site_name} - Error: {str(e)[:50]}")
                    # Add error result
                    self.all_results.append({
                        "site_name": site_name,
                        "site_url": self.sites_to_test.get(site_name, ""),
                        "total_tests": 1,
                        "passed": 0,
                        "failed": 1,
                        "warnings": 0,
                        "success_rate": 0,
                        "test_results": [{
                            "test": "Execution",
                            "status": "ERROR",
                            "details": str(e)[:100]
                        }],
                        "duration": 0
                    })
        
        safe_print("="*60)
        safe_print("✅ All tests completed!\n")
        
        # Generate reports
        self.generate_html_report()
        self.generate_json_summary()
        
        return self.all_results
    
    def generate_html_report(self):
        """Generate comprehensive HTML report"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        # Calculate statistics
        total_sites = len(self.all_results)
        sites_passed = len([s for s in self.all_results if s['failed'] == 0 and not s.get('error')])
        sites_with_issues = total_sites - sites_passed
        
        total_tests = sum(s['total_tests'] for s in self.all_results)
        total_passed = sum(s['passed'] for s in self.all_results)
        total_failed = sum(s['failed'] for s in self.all_results)
        total_warnings = sum(s['warnings'] for s in self.all_results)
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBC Multi-Site Test Report - {total_sites} Websites</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        .header {{
            background: white;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        h1 {{
            color: #1a202c;
            font-size: 2rem;
            margin-bottom: 8px;
            font-weight: 700;
        }}
        
        .subtitle {{
            color: #718096;
            font-size: 1rem;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }}
        
        .metric-card:hover {{ transform: translateY(-2px); }}
        
        .metric-value {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 4px;
        }}
        
        .metric-label {{
            color: #718096;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .success {{ color: #48bb78; }}
        .warning {{ color: #ed8936; }}
        .danger {{ color: #f56565; }}
        .info {{ color: #4299e1; }}
        
        .results-table {{
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        thead th {{
            background: #f7fafc;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #4a5568;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        tbody td {{
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        tbody tr:hover {{ background: #f7fafc; }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        
        .badge-success {{ background: #c6f6d5; color: #22543d; }}
        .badge-warning {{ background: #feebc8; color: #7c2d12; }}
        .badge-danger {{ background: #fed7d7; color: #742a2a; }}
        
        .progress-bar {{
            width: 100px;
            height: 8px;
            background: #e2e8f0;
            border-radius: 9999px;
            overflow: hidden;
            display: inline-block;
            vertical-align: middle;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #48bb78, #38a169);
            transition: width 0.3s ease;
        }}
        
        .details {{
            margin-top: 8px;
            padding: 8px;
            background: #f7fafc;
            border-radius: 8px;
            font-size: 0.875rem;
            display: none;
        }}
        
        .details.show {{ display: block; }}
        
        .test-badge {{
            display: inline-block;
            margin: 2px;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.75rem;
        }}
        
        .test-pass {{ background: #c6f6d5; color: #22543d; }}
        .test-fail {{ background: #fed7d7; color: #742a2a; }}
        .test-warning {{ background: #feebc8; color: #7c2d12; }}
        .test-skip {{ background: #e2e8f0; color: #4a5568; }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 32px;
            padding: 16px;
        }}
        
        .clickable {{ cursor: pointer; user-select: none; }}
    </style>
    <script>
        function toggleDetails(id) {{
            const element = document.getElementById('details-' + id);
            element.classList.toggle('show');
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 NBC Multi-Site Test Report</h1>
            <p class="subtitle">
                Tested {total_sites} NBC affiliate websites | 
                {end_time.strftime('%B %d, %Y at %I:%M %p')} | 
                Duration: {total_duration:.1f}s
            </p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value info">{total_sites}</div>
                <div class="metric-label">Sites Tested</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{sites_passed}</div>
                <div class="metric-label">Fully Passing</div>
            </div>
            <div class="metric-card">
                <div class="metric-value danger">{sites_with_issues}</div>
                <div class="metric-label">With Issues</div>
            </div>
            <div class="metric-card">
                <div class="metric-value info">{total_tests}</div>
                <div class="metric-label">Total Tests</div>
            </div>
            <div class="metric-card">
                <div class="metric-value success">{overall_success_rate:.1f}%</div>
                <div class="metric-label">Success Rate</div>
            </div>
        </div>
        
        <div class="results-table">
            <h2 style="margin-bottom: 16px; color: #2d3748;">Site-by-Site Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Site Location</th>
                        <th>Status</th>
                        <th>Tests Passed</th>
                        <th>Success Rate</th>
                        <th>Load Time</th>
                        <th>Issues</th>
                    </tr>
                </thead>
                <tbody>
"""
        
        # Sort sites by success rate
        sorted_sites = sorted(self.all_results, key=lambda x: (-x['success_rate'], x['site_name']))
        
        for idx, site in enumerate(sorted_sites):
            # Determine status
            if site.get('error') or site['failed'] > 0:
                status_badge = '<span class="status-badge badge-danger">Failed</span>'
            elif site['warnings'] > 0:
                status_badge = '<span class="status-badge badge-warning">Warning</span>'
            else:
                status_badge = '<span class="status-badge badge-success">Passed</span>'
            
            # Get load time from performance data
            load_time = "N/A"
            if site.get('performance') and site['performance'].get('loadTime'):
                load_time = f"{site['performance']['loadTime']/1000:.2f}s"
            
            html += f"""
                <tr class="clickable" onclick="toggleDetails({idx})">
                    <td><strong>{site['site_name']}</strong></td>
                    <td>{status_badge}</td>
                    <td>{site['passed']}/{site['total_tests']}</td>
                    <td>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {site['success_rate']:.0f}%"></div>
                        </div>
                        {site['success_rate']:.0f}%
                    </td>
                    <td>{load_time}</td>
                    <td>
                        ✓ {site['passed']} | 
                        ✗ {site['failed']} | 
                        ⚠ {site['warnings']}
                    </td>
                </tr>
                <tr>
                    <td colspan="6" style="padding: 0;">
                        <div id="details-{idx}" class="details">
                            <strong>URL:</strong> {site['site_url']}<br>
                            <strong>Test Results:</strong><br>
"""
            
            # Add test details
            for test in site['test_results']:
                badge_map = {
                    'PASS': 'test-pass',
                    'FAIL': 'test-fail',
                    'ERROR': 'test-fail',
                    'WARNING': 'test-warning',
                    'SKIP': 'test-skip'
                }
                badge_class = badge_map.get(test['status'], 'test-skip')
                html += f'<span class="test-badge {badge_class}">{test["test"]}: {test["status"]}</span>'
            
            html += """
                        </div>
                    </td>
                </tr>
"""
        
        html += f"""
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>NBC Multi-Site Testing Suite v2.0 | Generated in {total_duration:.1f} seconds</p>
            <p>Report any issues to the QA team</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Save report
        with open('multi_site_report.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        safe_print("📄 HTML report generated: multi_site_report.html")
    
    def generate_json_summary(self):
        """Generate JSON summary for integrations"""
        end_time = datetime.now()
        
        summary = {
            "timestamp": end_time.isoformat(),
            "duration_seconds": (end_time - self.start_time).total_seconds(),
            "total_sites": len(self.all_results),
            "sites_passed": len([s for s in self.all_results if s['failed'] == 0 and not s.get('error')]),
            "sites_failed": len([s for s in self.all_results if s['failed'] > 0 or s.get('error')]),
            "sites_with_warnings": len([s for s in self.all_results if s['warnings'] > 0]),
            "total_tests": sum(s['total_tests'] for s in self.all_results),
            "total_passed": sum(s['passed'] for s in self.all_results),
            "total_failed": sum(s['failed'] for s in self.all_results),
            "total_warnings": sum(s['warnings'] for s in self.all_results),
            "sites": self.all_results
        }
        
        with open('test_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        safe_print("📄 JSON summary generated: test_summary.json")
        
        return summary


def main():
    """Main entry point with CLI arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description='NBC Multi-Site Testing Suite')
    parser.add_argument('--workers', type=int, default=5,
                      help='Number of parallel workers (default: 5, max: 10)')
    parser.add_argument('--sites', type=str, default=None,
                      help='Comma-separated list of site names to test (default: all)')
    parser.add_argument('--timeout', type=int, default=20,
                      help='Page load timeout in seconds (default: 20)')
    
    args = parser.parse_args()
    
    # Parse sites if specified
    sites_to_test = NBC_SITES
    if args.sites:
        site_names = [s.strip() for s in args.sites.split(',')]
        sites_to_test = {name: url for name, url in NBC_SITES.items() if name in site_names}
        if not sites_to_test:
            print(f"❌ No matching sites found for: {args.sites}")
            return 1
    
    # Run tests
    tester = NBCMultiSiteTester(max_workers=args.workers, sites_to_test=sites_to_test)
    results = tester.run_all_tests()
    
    # Print summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    
    sites_passed = len([s for s in results if s['failed'] == 0 and not s.get('error')])
    total_sites = len(results)
    
    print(f"Total Sites Tested: {total_sites}")
    print(f"Sites Fully Passed: {sites_passed}")
    print(f"Sites with Issues: {total_sites - sites_passed}")
    
    # Show top issues
    problem_sites = [s for s in results if s['failed'] > 0 or s.get('error')]
    if problem_sites:
        print("\n⚠️ Sites requiring attention:")
        for site in problem_sites[:5]:
            print(f"  - {site['site_name']}: {site['failed']} tests failed")
    
    print(f"\n📊 Reports generated:")
    print(f"  - HTML: multi_site_report.html")
    print(f"  - JSON: test_summary.json")
    print("="*60)
    
    # Exit code: 0 if all passed, 1 if any issues
    return 0 if sites_passed == total_sites else 1


if __name__ == "__main__":
    exit(main())
