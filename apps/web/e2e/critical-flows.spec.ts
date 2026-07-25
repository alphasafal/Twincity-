import { expect, test } from '@playwright/test';

/**
 * Critical web flows for TwinPilot demo.
 * Requires API at NEXT_PUBLIC_API_URL (default http://localhost:8000).
 *
 * Run:
 *   make demo   # in one terminal
 *   pnpm --filter @twinpilot/web test:e2e:install
 *   pnpm --filter @twinpilot/web test:e2e
 */
test.describe('TwinPilot critical flows', () => {
  test('login and view dashboard', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: /TwinPilot/i })).toBeVisible();
    await expect(page.getByText(/Autonomous optimization you can verify/i)).toBeVisible();

    await page.getByLabel(/email/i).fill('manager@twinpilot.demo');
    await page.getByLabel(/password/i).fill('TwinPilot-Manager-Demo!');
    await page.getByRole('button', { name: /enter control room/i }).click();

    await expect(page).toHaveURL(/dashboard/, { timeout: 20_000 });
    await expect(
      page.getByText(/AUTONOMOUS|GUARDED|ADVISORY|FALLBACK|MANUAL/i).first(),
    ).toBeVisible({ timeout: 20_000 });
  });

  test('start demo scenario from simulator page', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('manager@twinpilot.demo');
    await page.getByLabel(/password/i).fill('TwinPilot-Manager-Demo!');
    await page.getByRole('button', { name: /enter control room/i }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 20_000 });

    await page.goto('/simulator');
    await expect(page.getByText(/scenario|what-if|simulator/i).first()).toBeVisible({
      timeout: 15_000,
    });
    const scenario = page.getByRole('button', { name: /faulty temperature sensor|faulty sensor/i });
    if (await scenario.count()) {
      await scenario.first().click();
      await expect(page.getByText(/GUARDED|FALLBACK|started|sensor/i).first()).toBeVisible({
        timeout: 15_000,
      });
    }
  });

  test('open decisions and alerts', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('manager@twinpilot.demo');
    await page.getByLabel(/password/i).fill('TwinPilot-Manager-Demo!');
    await page.getByRole('button', { name: /enter control room/i }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 20_000 });

    await page.goto('/decisions');
    await expect(page.getByText(/decision|timeline|validation/i).first()).toBeVisible({
      timeout: 15_000,
    });

    await page.goto('/alerts');
    await expect(page.getByText(/alert|severity|acknowledge/i).first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test('digital twin page renders zones', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('manager@twinpilot.demo');
    await page.getByLabel(/password/i).fill('TwinPilot-Manager-Demo!');
    await page.getByRole('button', { name: /enter control room/i }).click();
    await expect(page).toHaveURL(/dashboard/, { timeout: 20_000 });

    await page.goto('/digital-twin');
    await expect(page.getByText(/Core Office|North Office|digital twin/i).first()).toBeVisible({
      timeout: 15_000,
    });
  });
});
