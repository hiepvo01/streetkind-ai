"""
Responsive layout tests across desktop, tablet, and mobile viewports.
"""

import pytest
from playwright.sync_api import Page, expect
from .conftest import do_login, BASE_URL

VIEWPORTS = [
    {"name": "desktop_1920", "width": 1920, "height": 1080},
    {"name": "ipad_768", "width": 768, "height": 1024},
    {"name": "mobile_375", "width": 375, "height": 812},
]


class TestResponsive:
    @pytest.mark.parametrize("vp", VIEWPORTS, ids=[v["name"] for v in VIEWPORTS])
    def test_login_page_no_overflow(self, page: Page, vp):
        """The login page should not overflow horizontally at any viewport."""
        page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
        page.goto(BASE_URL)
        page.wait_for_selector('text=Login', timeout=10000)
        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        assert scroll_w <= vp["width"] + 5, (
            f"Horizontal overflow at {vp['name']}: scrollWidth={scroll_w}, viewport={vp['width']}"
        )

    @pytest.mark.parametrize("vp", VIEWPORTS, ids=[v["name"] for v in VIEWPORTS])
    def test_app_no_overflow(self, page: Page, vp):
        """The main app should not overflow horizontally at any viewport."""
        page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
        do_login(page)
        scroll_w = page.evaluate("document.documentElement.scrollWidth")
        assert scroll_w <= vp["width"] + 5, (
            f"Horizontal overflow at {vp['name']}: scrollWidth={scroll_w}, viewport={vp['width']}"
        )

    @pytest.mark.parametrize("vp", VIEWPORTS, ids=[v["name"] for v in VIEWPORTS])
    def test_sidebar_works(self, page: Page, vp):
        """The sidebar should open and show Dashboard at any viewport."""
        page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
        do_login(page)
        page.locator('i.sidebar.icon').first.click()
        expect(page.locator('text=Dashboard')).to_be_visible(timeout=3000)
