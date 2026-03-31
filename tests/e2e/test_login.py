"""
E2E tests for the login flow.
"""

from playwright.sync_api import Page, expect
from .conftest import do_login, BASE_URL, DEMO_VOLUNTEER, DEMO_ADMIN


class TestLogin:
    def test_shows_login_when_unauthenticated(self, page: Page):
        """Unauthenticated visitors should see the login form."""
        page.goto(BASE_URL)
        expect(page.locator('text=Safe Base & Incident Report Login')).to_be_visible(timeout=10000)

    def test_login_with_valid_credentials(self, page: Page):
        """Logging in with a valid demo account reaches the main app."""
        do_login(page)
        expect(page.locator('text=Tap to start speaking')).to_be_visible()

    def test_login_with_invalid_credentials(self, page: Page):
        """Bad credentials should show an error message."""
        page.goto(BASE_URL)
        page.wait_for_selector('input[placeholder="Email Address"]', timeout=10000)
        page.fill('input[placeholder="Email Address"]', "bad@email.com")
        page.fill('input[placeholder="Password"]', "wrongpass")
        page.click('button:has-text("Login")')
        # Semantic UI renders errors with .error.message or .negative.message
        expect(page.locator('.error.message, .negative.message')).to_be_visible(timeout=8000)

    def test_logout(self, page: Page):
        """After logging in the user can log out via the sidebar."""
        do_login(page)
        # Open the sidebar (hamburger icon in the MenuBar)
        page.locator('i.sidebar.icon').first.click()
        page.wait_for_timeout(500)
        page.click('text=Log out')
        expect(page.locator('text=Safe Base & Incident Report Login')).to_be_visible(timeout=10000)

    def test_admin_login(self, page: Page):
        """Admin user can also log in successfully."""
        do_login(page, email=DEMO_ADMIN["email"], password=DEMO_ADMIN["password"])
        expect(page.locator('text=Tap to start speaking')).to_be_visible()
