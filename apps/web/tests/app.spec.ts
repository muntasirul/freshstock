import { expect, test } from "@playwright/test";

test("dashboard loads overview", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /clearer view/i })).toBeVisible();
  await expect(page.getByText("Products tracked")).toBeVisible();
});
