#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NBC Station Testing Suite - 13 Tests
- 10 Homepage / Compliance checks
- 3 Functional workflow checks (Weather page, Ad iframe, Video player)
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --------------------------
# Logging
# --------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("nbc_station_tester")

# --------------------------
# Defaults
# --------------------------
DEFAULT_STATIONS = {
    "NBC New York": "https://www.nbcnewyork.com/",
}

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def screenshot(driver, outdir: str, name: str):
    try:
        ensure_dir(outdir)
        driver.save_screenshot(os.path.join(outdir, f"{name}.png"))
    except Exception:
        pass

def build_driver(headless: bool) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

    service = None
    for p in ["/usr/bin/chromedriver", "/usr/local/bin/chromedriver"]:
        if os.path.exists(p):
            service = Service(p)
            break
    if not service:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())

    drv = webdriver.Chrome(service=service, options=options)
    drv.set_page_load_timeout(30)
    return drv

def wait_dom_complete(driver, timeout=30):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

def get_nav_perf(driver) -> Dict:
    js = """
    const nav = performance.getEntriesByType('navigation')[0];
    if (!nav) return {};
    return {
        loadTime: nav.loadEventEnd - nav.startTime,
        domContentLoaded: nav.domContentLoadedEventEnd - nav.startTime
    };
    """
    try:
        return driver.execute_script(js) or {}
    except Exception:
        return {}


class NBCStationTester:
    def __init__(self, station_name: str, station_url: str, outdir: str, screenshots: bool, headless: bool):
        self.station_name = station_name
        self.station_url = station_url
        self.outdir = outdir
        self.screenshots = screenshots
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.results: List[Dict] = []
        self.perf_metrics: Dict = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def add_result(self, test: str, status: str, message: str):
        self.results.append({"test": test, "status": status, "message": message})

    def setup(self) -> bool:
        try:
            self.driver = build_driver(self.headless)
            return True
        except Exception as e:
            self.add_result("Browser Setup", "ERROR", f"{e}")
            return False

    def teardown(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

    # --------------------
    # Core Tests (10)
    # --------------------
    def test_page_performance(self):  # 1
        name = "Page Load Performance"
        try:
            self.driver.get(self.station_url)
            wait_dom_complete(self.driver, 30)
            perf = get_nav_perf(self.driver)
            self.perf_metrics = perf
            load_s = (perf.get("loadTime", 0) or 0) / 1000.0
            if load_s < 5:
                status, msg = "PASS", f"Fast: {load_s:.2f}s"
            elif load_s < 10:
                status, msg = "WARNING", f"Slow: {load_s:.2f}s"
            else:
                status, msg = "FAIL", f"Very slow: {load_s:.2f}s"
            self.add_result(name, status, msg)
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_page_size(self):  # 2
        name = "Page Size Check"
        try:
            html = self.driver.page_source or ""
            size_mb = len(html.encode("utf-8")) / (1024 * 1024)
            if size_mb < 2:
                status, msg = "PASS", f"Good size: {size_mb:.2f}MB"
            elif size_mb < 5:
                status, msg = "WARNING", f"Large: {size_mb:.2f}MB"
            else:
                status, msg = "FAIL", f"Too large: {size_mb:.2f}MB"
            self.add_result(name, status, msg)
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_javascript_errors(self):  # 3
        name = "JavaScript Errors"
        try:
            logs = self.driver.get_log("browser")
            errors = [l for l in logs if l.get("level") in ("SEVERE", "ERROR")]
            if not errors:
                status, msg = "PASS", "No JS errors"
            elif len(errors) <= 2:
                status, msg = "WARNING", f"{len(errors)} JS error(s)"
            else:
                status, msg = "FAIL", f"{len(errors)} JS error(s)"
            self.add_result(name, status, msg)
        except Exception:
            self.add_result(name, "WARNING", "Browser logs unavailable")

    def test_image_loading(self):  # 4
        name = "Image Loading"
        try:
            images = self.driver.find_elements(By.TAG_NAME, "img")[:20]
            broken = 0
            for img in images:
                ok = self.driver.execute_script(
                    "return arguments[0].complete && arguments[0].naturalWidth>0;", img
                )
                if not ok:
                    broken += 1
            if broken == 0:
                status, msg = "PASS", f"All {len(images)} images load"
            elif broken <= 2:
                status, msg = "WARNING", f"{broken} broken image(s)"
            else:
                status, msg = "FAIL", f"{broken} broken images"
            self.add_result(name, status, msg)
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_video_presence(self):  # 5
        name = "Video Players (Presence)"
        try:
            videos = self.driver.find_elements(By.CSS_SELECTOR, "video, iframe[src*='player']")
            if any(v.is_displayed() for v in videos):
                self.add_result(name, "PASS", f"{len(videos)} video(s) detected")
            else:
                self.add_result(name, "WARNING", "No visible videos found")
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_weather_widget(self):  # 6
        name = "Weather Widget"
        try:
            selectors = [".weather", "#weather", "[class*='weather']"]
            found = any(self.driver.find_elements(By.CSS_SELECTOR, s) for s in selectors)
            if found:
                self.add_result(name, "PASS", "Weather widget found")
            else:
                self.add_result(name, "FAIL", "Weather widget not found")
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_mobile_responsive(self):  # 7
        name = "Mobile Responsive"
        try:
            vp = self.driver.execute_script(
                "let m=document.querySelector('meta[name=viewport]');return m?m.content:null;"
            )
            if vp and "width=device-width" in vp:
                self.add_result(name, "PASS", "Viewport meta ok")
            else:
                self.add_result(name, "FAIL", "No proper viewport meta")
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_ads_presence(self):  # 8
        name = "Advertisements (Presence)"
        try:
            ads = self.driver.find_elements(By.CSS_SELECTOR, "iframe[id*='ad'], div[class*='ad']")
            visible = [a for a in ads if a.is_displayed()]
            if len(visible) >= 2:
                self.add_result(name, "PASS", f"{len(visible)} ads visible")
            elif len(visible) == 1:
                self.add_result(name, "WARNING", "Only 1 ad visible")
            else:
                self.add_result(name, "FAIL", "No ads detected")
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_navigation_menu(self):  # 9
        name = "Navigation Menu"
        try:
            links = self.driver.find_elements(By.CSS_SELECTOR, "nav a, header a")
            visible = [l for l in links if l.is_displayed()]
            if len(visible) >= 5:
                self.add_result(name, "PASS", f"{len(visible)} nav links visible")
            else:
                self.add_result(name, "FAIL", f"Only {len(visible)} nav links")
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_footer_compliance(self):  # 10
        name = "Footer Compliance"
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            footer = self.driver.find_element(By.CSS_SELECTOR, "footer")
            text = footer.text.lower()
            required = ["privacy", "terms", "copyright", "©"]
            found = [r for r in required if r in text]
            if len(found) >= 3:
                self.add_result(name, "PASS", "Footer compliance ok")
            elif len(found) == 2:
                self.add_result(name, "WARNING", "Some footer items missing")
            else:
                self.add_result(name, "FAIL", "Footer compliance missing")
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    # --------------------
    # Functional Workflows (3)
    # --------------------
    def test_weather_page_navigation(self):  # 11
        name = "Weather Page Navigation"
        try:
            self.driver.get(self.station_url)
            wait_dom_complete(self.driver, 30)
            weather_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/weather/'][data-lid='Weather']"))
            )
            weather_link.click()
            forecast = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.weather-page__section--forecast-block"))
            )
            visible = self.driver.execute_script("return arguments[0].offsetHeight>0 && arguments[0].offsetWidth>0;", forecast)
            if visible:
                self.add_result(name, "PASS", "Weather page loaded")
            else:
                self.add_result(name, "FAIL", "Forecast block not visible")
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_ad_iframe_validation(self):  # 12
        name = "Ad Iframe Validation"
        try:
            iframe_container = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[id^='google_ads_iframe_'][id$='__container__']"))
            )
            iframe = iframe_container.find_element(By.TAG_NAME, "iframe")
            ad_loaded = self.driver.execute_script("""
                let frame = arguments[0];
                try {
                    let doc = frame.contentDocument || frame.contentWindow.document;
                    return doc && doc.readyState==='complete' && doc.body.innerHTML.trim().length>0;
                } catch(e) { return false; }
            """, iframe)
            if ad_loaded:
                self.add_result(name, "PASS", "Ad iframe content loaded")
            else:
                self.add_result(name, "FAIL", "Ad iframe empty/not loaded")
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    def test_video_functional(self):  # 13
        name = "Video Player Functional Test"
        try:
            video = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "video.jw-video"))
            )
            initial = float(self.driver.execute_script("return arguments[0].currentTime;", video))
            time.sleep(2)
            later = float(self.driver.execute_script("return arguments[0].currentTime;", video))
            if later > initial:
                self.add_result(name, "PASS", f"Video played {initial}->{later}")
            else:
                self.add_result(name, "FAIL", "Video did not play")
        except Exception as e:
            self.add_result(name, "FAIL", f"{e}")

    # --------------------
    def run_all(self) -> Dict:
        self.start_time = datetime.now()
        if not self.setup():
            self.end_time = datetime.now()
            return self.summary()
        try:
            # 10 homepage checks
            self.test_page_performance()
            self.test_page_size()
            self.test_javascript_errors()
            self.test_image_loading()
            self.test_video_presence()
            self.test_weather_widget()
            self.test_mobile_responsive()
            self.test_ads_presence()
            self.test_navigation_menu()
            self.test_footer_compliance()

            # 3 functional workflows
            self.test_weather_page_navigation()
            self.test_ad_iframe_validation()
            self.test_video_functional()

        finally:
            if self.screenshots:
                screenshot(self.driver, self.outdir, "final_page")
            self.teardown()
            self.end_time = datetime.now()
        return self.summary()

    def summary(self) -> Dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        warnings = sum(1 for r in self.results if r["status"] == "WARNING")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else 0
        overall = "PASS" if failed == 0 and errors == 0 else "FAIL"
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
            "overall_status": overall,
            "test_results": self.results,
            "performance": self.perf_metrics,
        }


def generate_html_report(summary: Dict, outfile="index.html"):
    passed = summary["stations_passed"]
    failed = summary["stations_failed"]
    overall_status = "PASSED" if failed == 0 else "FAILED"
    overall_color = "#28a745" if failed == 0 else "#dc3545"
    html = f"<html><body><h1 style='color:{overall_color}'>NBC Station Test Report: {overall_status}</h1>"
    for station in summary["stations"]:
        html += f"<h2>{station['station_name']} ({station['overall_status']})</h2>"
        html += "<table border=1><tr><th>Test</th><th>Status</th><th>Message</th></tr>"
        for t in station["test_results"]:
            html += f"<tr><td>{t['test']}</td><td>{t['status']}</td><td>{t['message']}</td></tr>"
        html += "</table><br/>"
    html += "</body></html>"
    with open(outfile, "w") as f:
        f.write(html)
    logger.info(f"HTML report saved to {outfile}")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--station", type=str)
    p.add_argument("--url", type=str)
    p.add_argument("--screenshots", action="store_true")
    p.add_argument("--outdir", type=str, default="artifacts")
    p.add_argument("--no-headless", action="store_true")
    return p.parse_args()

def resolve_stations(args):
    if args.url:
        return {"Custom URL": args.url}
    if args.station:
        if args.station in DEFAULT_STATIONS:
            return {args.station: DEFAULT_STATIONS[args.station]}
        logger.error(f"Unknown station {args.station}")
        sys.exit(2)
    return DEFAULT_STATIONS

def main() -> int:
    args = parse_args()
    ensure_dir(args.outdir)
    stations = resolve_stations(args)
    all_results = []
    for name, url in stations.items():
        tester = NBCStationTester(name, url, args.outdir, args.screenshots, not args.no_headless)
        res = tester.run_all()
        all_results.append(res)
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_stations": len(all_results),
        "stations_passed": sum(1 for r in all_results if r["overall_status"] == "PASS"),
        "stations_failed": sum(1 for r in all_results if r["overall_status"] == "FAIL"),
        "total_tests": sum(r["total_tests"] for r in all_results),
        "total_passed": sum(r["passed"] for r in all_results),
        "total_failed": sum(r["failed"] for r in all_results),
        "stations": all_results,
    }
    with open(os.path.join(args.outdir, "test_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    generate_html_report(summary, outfile=os.path.join(args.outdir, "index.html"))
    return 0 if summary["stations_failed"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
