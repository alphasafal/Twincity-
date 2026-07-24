import { expect, test } from '@playwright/test';

/**
 * Critical web flows for TwinPilot demo.
 * Requires API at NEXT_PUBLIC_API_URL (default http://localhost:8000).
 */
test.describe('TwinPilot critical flows', () => {
  test('login and view dashboard', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /TwinPilot/i })).toBeVisible();
    await expect(page.getByText(/Autonomous optimization you can verify/i)).toBeVisible();

    await page.getByLabel(/email/i).fill('manager@twinpilot.demo');
    await page.getByLabel(/password/i).fill('TwinPilot-Manager-Demo!');
    await page.getByRole('button', { name: /log in|sign in|login/i }).click();

    await expect(page).toHaveURL(/dashboard/, { timeout: 20_000 });
    await expect(page.getByText(/AUTONOMOUS|GUARDED|ADVISORY|FALLBACK|MANUAL/i).first()).toBeVisible({
      timeout: 20_000,
    });
  });
});
