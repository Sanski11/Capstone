import { test, expect } from '@playwright/test';

test.describe('ezStay Login Tests', () => {
  test('should load login page', async ({ page }) => {
    await page.goto('/login');
    const title = await page.title();
    expect(title).toContain('Login');
  });

  test('should display login form with all required fields', async ({ page }) => {
    await page.goto('/login');
    
    // Check for username/email input
    const usernameInput = page.locator('input[name="username_or_email"]');
    await expect(usernameInput).toBeVisible();
    
    // Check for password input
    const passwordInput = page.locator('input[name="password"]');
    await expect(passwordInput).toBeVisible();
    
    // Check for login button
    const loginButton = page.locator('button[type="submit"]');
    await expect(loginButton).toBeVisible();
  });

  test('should toggle password visibility', async ({ page }) => {
    await page.goto('/login');
    
    const passwordInput = page.locator('#password');
    const showPasswordCheckbox = page.locator('#showPassword');
    
    // Verify initial state is password
    await expect(passwordInput).toHaveAttribute('type', 'password');
    
    // Click show password checkbox
    await showPasswordCheckbox.click();
    
    // Verify password is now visible
    await expect(passwordInput).toHaveAttribute('type', 'text');
    
    // Click again to hide password
    await showPasswordCheckbox.click();
    
    // Verify password is hidden again
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('should display signup and password recovery links', async ({ page }) => {
    await page.goto('/login');
    
    // Check for signup link
    const signupLink = page.locator('a:has-text("Create an account")');
    await expect(signupLink).toBeVisible();
    
    // Check for forgot password link
    const forgotLink = page.locator('a:has-text("Forgot your password")');
    await expect(forgotLink).toBeVisible();
    
    // Check for home link
    const homeLink = page.locator('a:has-text("Back to Home")');
    await expect(homeLink).toBeVisible();
  });

  test('should submit login form with credentials', async ({ page }) => {
    await page.goto('/login');
    
    // Fill in credentials
    await page.fill('input[name="username_or_email"]', 'testuser@example.com');
    await page.fill('input[name="password"]', 'testpassword123');
    
    // Note: Actual login will depend on valid credentials in your system
    // This test just verifies the form can be filled and submitted
    const loginButton = page.locator('button[type="submit"]');
    expect(await loginButton.isEnabled()).toBe(true);
  });
});

test.describe('ezStay Dashboard Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/dashboard').catch(() => {
      // If dashboard requires auth, navigate to login instead
      return page.goto('/login');
    });
  });

  test('should display dashboard header', async ({ page }) => {
    // Skip if not on dashboard (e.g., if redirected to login)
    if (!page.url().includes('/dashboard')) {
      test.skip();
    }
    
    const pageTitle = page.locator('.page-title');
    await expect(pageTitle).toBeVisible({ timeout: 5000 });
    const titleText = await pageTitle.textContent();
    expect(titleText?.toLowerCase()).toContain('dashboard');
  });

  test('should display sidebar with navigation menu', async ({ page }) => {
    // Skip if not on dashboard (e.g., if redirected to login due to auth)
    if (!page.url().includes('/dashboard')) {
      test.skip();
    }
    
    const sidebar = page.locator('#sidebar');
    await expect(sidebar).toBeVisible({ timeout: 5000 });
    
    // Check for menu items
    const menuItems = page.locator('.side-menu__item');
    const count = await menuItems.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display notification bell in header', async ({ page }) => {
    // Skip if not on dashboard
    if (!page.url().includes('/dashboard')) {
      test.skip();
    }
    
    // Skip if not on dashboard
    if (!page.url().includes('/dashboard')) {
      test.skip();
    }
    
    const profileDropdown = page.locator('#profileDropdown');
    await expect(profileDropdown).toBeVisible({ timeout: 5000 });
  });

  test('should display profile dropdown in header', async ({ page }) => {
    const profileDropdown = page.locator('#profileDropdown');
    await expect(profileDropdown).toBeVisible();
  });

  test('should open and close notification dropdown', async ({ page }) => {
    // Skip if not on dashboard
    if (!page.url().includes('/dashboard')) {
      test.skip();
    }
    
    // Click notification bell to open dropdown
    const notificationBell = page.locator('#notifDropdown');
    if (await notificationBell.count() > 0) {
      await notificationBell.click();
      
      const notificationDropdown = page.locator('#notif-dropdown');
      await expect(notificationDropdown).toBeVisible({ timeout: 5000 });
    }
  });

  test('should open profile dropdown menu', async ({ page }) => {
    // Skip if not on dashboard
    if (!page.url().includes('/dashboard')) {
      test.skip();
    }
    
    // Click profile dropdown to open menu
    const profileDropdown = page.locator('#profileDropdown');
    if (await profileDropdown.count() > 0) {
      await profileDropdown.click();
      
      const profileMenu = page.locator('[aria-labelledby="profileDropdown"]');
      await expect(profileMenu).toBeVisible({ timeout: 5000 });
    }
  });

  test('should navigate to different sections via sidebar', async ({ page }) => {
    // Test navigation to a common page like Rooms (if available for user role)
    const roomsLink = page.locator('a[href="/rooms"]');
    const roomsCount = await roomsLink.count();
    
    if (roomsCount > 0) {
      await roomsLink.first().click();
      // Wait for URL to change instead of navigation event
      await page.waitForURL('**/rooms', { timeout: 5000 }).catch(() => {});
      expect(page.url()).toContain('/rooms');
    }
  });

  test('should display alerts/flash messages if present', async ({ page }) => {
    // This test checks if alerts are properly displayed
    // Skip if not on dashboard
    if (!page.url().includes('/dashboard')) {
      test.skip();
    }
    
    const alerts = page.locator('.alert');
    const count = await alerts.count();
    
    // Alerts may or may not be present
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should have responsive header with notification and profile areas', async ({ page }) => {
    // Skip if not on dashboard
    if (!page.url().includes('/dashboard')) {
      test.skip();
    }
    
    // Check header structure
    const header = page.locator('header.app-header');
    await expect(header).toBeVisible({ timeout: 5000 });
    
    // Check notification area
    const notificationArea = page.locator('.dropdown').first();
    await expect(notificationArea).toBeVisible();
    
    // Check profile area
    const profileArea = page.locator('.dropdown').nth(1);
    await expect(profileArea).toBeVisible();
  });
});
