# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test.spec.ts >> ezStay Dashboard Tests >> should display profile dropdown in header
- Location: tests\test.spec.ts:129:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('#profileDropdown')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('#profileDropdown')

```

# Page snapshot

```yaml
- generic [ref=e2]:
  - heading "Sign In" [level=3] [ref=e3]
  - generic [ref=e4]:
    - generic [ref=e5]:
      - generic [ref=e6]: Username or Email
      - textbox "Enter your username or email" [ref=e7]
    - generic [ref=e8]:
      - generic [ref=e9]: Password
      - textbox "Enter your password" [ref=e10]
      - generic [ref=e11]:
        - checkbox "Show Password" [ref=e12]
        - generic [ref=e13]: Show Password
    - button "Login" [ref=e14] [cursor=pointer]
    - generic [ref=e15]:
      - link "Forgot your password?" [ref=e16] [cursor=pointer]:
        - /url: /forgot_password
      - link "Create an account" [ref=e17] [cursor=pointer]:
        - /url: /signup
      - link "Back to Home" [ref=e18] [cursor=pointer]:
        - /url: /index
```

# Test source

```ts
  31  |     
  32  |     // Verify initial state is password
  33  |     await expect(passwordInput).toHaveAttribute('type', 'password');
  34  |     
  35  |     // Click show password checkbox
  36  |     await showPasswordCheckbox.click();
  37  |     
  38  |     // Verify password is now visible
  39  |     await expect(passwordInput).toHaveAttribute('type', 'text');
  40  |     
  41  |     // Click again to hide password
  42  |     await showPasswordCheckbox.click();
  43  |     
  44  |     // Verify password is hidden again
  45  |     await expect(passwordInput).toHaveAttribute('type', 'password');
  46  |   });
  47  | 
  48  |   test('should display signup and password recovery links', async ({ page }) => {
  49  |     await page.goto('/login');
  50  |     
  51  |     // Check for signup link
  52  |     const signupLink = page.locator('a:has-text("Create an account")');
  53  |     await expect(signupLink).toBeVisible();
  54  |     
  55  |     // Check for forgot password link
  56  |     const forgotLink = page.locator('a:has-text("Forgot your password")');
  57  |     await expect(forgotLink).toBeVisible();
  58  |     
  59  |     // Check for home link
  60  |     const homeLink = page.locator('a:has-text("Back to Home")');
  61  |     await expect(homeLink).toBeVisible();
  62  |   });
  63  | 
  64  |   test('should submit login form with credentials', async ({ page }) => {
  65  |     await page.goto('/login');
  66  |     
  67  |     // Fill in credentials
  68  |     await page.fill('input[name="username_or_email"]', 'testuser@example.com');
  69  |     await page.fill('input[name="password"]', 'testpassword123');
  70  |     
  71  |     // Note: Actual login will depend on valid credentials in your system
  72  |     // This test just verifies the form can be filled and submitted
  73  |     const loginButton = page.locator('button[type="submit"]');
  74  |     expect(await loginButton.isEnabled()).toBe(true);
  75  |   });
  76  | });
  77  | 
  78  | test.describe('ezStay Dashboard Tests', () => {
  79  |   test.beforeEach(async ({ page }) => {
  80  |     // Navigate to dashboard
  81  |     await page.goto('/dashboard').catch(() => {
  82  |       // If dashboard requires auth, navigate to login instead
  83  |       return page.goto('/login');
  84  |     });
  85  |   });
  86  | 
  87  |   test('should display dashboard header', async ({ page }) => {
  88  |     // Skip if not on dashboard (e.g., if redirected to login)
  89  |     if (!page.url().includes('/dashboard')) {
  90  |       test.skip();
  91  |     }
  92  |     
  93  |     const pageTitle = page.locator('.page-title');
  94  |     await expect(pageTitle).toBeVisible({ timeout: 5000 });
  95  |     const titleText = await pageTitle.textContent();
  96  |     expect(titleText?.toLowerCase()).toContain('dashboard');
  97  |   });
  98  | 
  99  |   test('should display sidebar with navigation menu', async ({ page }) => {
  100 |     // Skip if not on dashboard (e.g., if redirected to login due to auth)
  101 |     if (!page.url().includes('/dashboard')) {
  102 |       test.skip();
  103 |     }
  104 |     
  105 |     const sidebar = page.locator('#sidebar');
  106 |     await expect(sidebar).toBeVisible({ timeout: 5000 });
  107 |     
  108 |     // Check for menu items
  109 |     const menuItems = page.locator('.side-menu__item');
  110 |     const count = await menuItems.count();
  111 |     expect(count).toBeGreaterThan(0);
  112 |   });
  113 | 
  114 |   test('should display notification bell in header', async ({ page }) => {
  115 |     // Skip if not on dashboard
  116 |     if (!page.url().includes('/dashboard')) {
  117 |       test.skip();
  118 |     }
  119 |     
  120 |     // Skip if not on dashboard
  121 |     if (!page.url().includes('/dashboard')) {
  122 |       test.skip();
  123 |     }
  124 |     
  125 |     const profileDropdown = page.locator('#profileDropdown');
  126 |     await expect(profileDropdown).toBeVisible({ timeout: 5000 });
  127 |   });
  128 | 
  129 |   test('should display profile dropdown in header', async ({ page }) => {
  130 |     const profileDropdown = page.locator('#profileDropdown');
> 131 |     await expect(profileDropdown).toBeVisible();
      |                                   ^ Error: expect(locator).toBeVisible() failed
  132 |   });
  133 | 
  134 |   test('should open and close notification dropdown', async ({ page }) => {
  135 |     // Skip if not on dashboard
  136 |     if (!page.url().includes('/dashboard')) {
  137 |       test.skip();
  138 |     }
  139 |     
  140 |     // Click notification bell to open dropdown
  141 |     const notificationBell = page.locator('#notifDropdown');
  142 |     if (await notificationBell.count() > 0) {
  143 |       await notificationBell.click();
  144 |       
  145 |       const notificationDropdown = page.locator('#notif-dropdown');
  146 |       await expect(notificationDropdown).toBeVisible({ timeout: 5000 });
  147 |     }
  148 |   });
  149 | 
  150 |   test('should open profile dropdown menu', async ({ page }) => {
  151 |     // Skip if not on dashboard
  152 |     if (!page.url().includes('/dashboard')) {
  153 |       test.skip();
  154 |     }
  155 |     
  156 |     // Click profile dropdown to open menu
  157 |     const profileDropdown = page.locator('#profileDropdown');
  158 |     if (await profileDropdown.count() > 0) {
  159 |       await profileDropdown.click();
  160 |       
  161 |       const profileMenu = page.locator('[aria-labelledby="profileDropdown"]');
  162 |       await expect(profileMenu).toBeVisible({ timeout: 5000 });
  163 |     }
  164 |   });
  165 | 
  166 |   test('should navigate to different sections via sidebar', async ({ page }) => {
  167 |     // Test navigation to a common page like Rooms (if available for user role)
  168 |     const roomsLink = page.locator('a[href="/rooms"]');
  169 |     const roomsCount = await roomsLink.count();
  170 |     
  171 |     if (roomsCount > 0) {
  172 |       await roomsLink.first().click();
  173 |       // Wait for URL to change instead of navigation event
  174 |       await page.waitForURL('**/rooms', { timeout: 5000 }).catch(() => {});
  175 |       expect(page.url()).toContain('/rooms');
  176 |     }
  177 |   });
  178 | 
  179 |   test('should display alerts/flash messages if present', async ({ page }) => {
  180 |     // This test checks if alerts are properly displayed
  181 |     // Skip if not on dashboard
  182 |     if (!page.url().includes('/dashboard')) {
  183 |       test.skip();
  184 |     }
  185 |     
  186 |     const alerts = page.locator('.alert');
  187 |     const count = await alerts.count();
  188 |     
  189 |     // Alerts may or may not be present
  190 |     expect(count).toBeGreaterThanOrEqual(0);
  191 |   });
  192 | 
  193 |   test('should have responsive header with notification and profile areas', async ({ page }) => {
  194 |     // Skip if not on dashboard
  195 |     if (!page.url().includes('/dashboard')) {
  196 |       test.skip();
  197 |     }
  198 |     
  199 |     // Check header structure
  200 |     const header = page.locator('header.app-header');
  201 |     await expect(header).toBeVisible({ timeout: 5000 });
  202 |     
  203 |     // Check notification area
  204 |     const notificationArea = page.locator('.dropdown').first();
  205 |     await expect(notificationArea).toBeVisible();
  206 |     
  207 |     // Check profile area
  208 |     const profileArea = page.locator('.dropdown').nth(1);
  209 |     await expect(profileArea).toBeVisible();
  210 |   });
  211 | });
  212 | 
```