import { expect, test } from '@playwright/test';

const publicRoutes = [
    '/',
    '/category',
    '/tu-van',
    '/login',
    '/register',
    '/cart',
    '/contact',
];

function mockApiResponse(url) {
    if (url.pathname.endsWith('/api/products')) {
        return {
            items: [],
            total_pages: 0,
            total_elements: 0,
            first: true,
            last: true,
        };
    }

    if (
        url.pathname.endsWith('/api/categories') ||
        url.pathname.endsWith('/api/brands') ||
        url.pathname.endsWith('/api/promotions') ||
        url.pathname.endsWith('/api/reviews/recent')
    ) {
        return [];
    }

    return {};
}

test.beforeEach(async ({ page }) => {
    await page.route('**/spring-api/**', async (route) => {
        const url = new URL(route.request().url());
        await route.fulfill({
            status: 200,
            contentType: 'application/json; charset=utf-8',
            body: JSON.stringify(mockApiResponse(url)),
        });
    });
});

test('public routes render without browser errors or horizontal overflow', async ({ page }) => {
    const browserErrors = [];
    page.on('pageerror', (error) => browserErrors.push(error.message));
    page.on('console', (message) => {
        if (message.type() === 'error') browserErrors.push(message.text());
    });

    for (const route of publicRoutes) {
        await test.step(route, async () => {
            browserErrors.length = 0;
            const response = await page.goto(route, { waitUntil: 'domcontentloaded' });

            expect(response?.ok()).toBeTruthy();
            await expect(page.locator('#root')).not.toBeEmpty({ timeout: 15_000 });

            const overflow = await page.evaluate(() => ({
                viewportWidth: document.documentElement.clientWidth,
                contentWidth: document.documentElement.scrollWidth,
            }));
            expect(overflow.contentWidth).toBeLessThanOrEqual(overflow.viewportWidth + 1);
            expect(browserErrors).toEqual([]);
        });
    }
});

test('password visibility control works consistently', async ({ page }) => {
    await page.goto('/login');

    const password = page.locator('input[type="password"]').first();
    const passwordField = password.locator('xpath=..');
    const passwordHandle = await password.elementHandle();
    expect(passwordHandle).not.toBeNull();
    await expect(password).toBeVisible();
    await passwordField.getByRole('button').click();
    await expect.poll(() => passwordHandle.getAttribute('type')).toBe('text');
});

test('AI consulting results remain available after viewing a product and going back', async ({ page }) => {
    await page.route('**/spring-api/api/search/ai/text', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json; charset=utf-8',
            body: JSON.stringify({
                products: [
                    {
                        product_id: 42,
                        title: 'Sản phẩm tư vấn',
                        price: 250000,
                        currency: 'VND',
                        available: true,
                    },
                ],
                warnings: [],
            }),
        });
    });

    await page.goto('/tu-van');
    const keywordInput = page.locator('form').filter({ hasText: 'Tìm theo từ khóa' }).getByRole('textbox');
    await keywordInput.fill('áo hoodie đen');
    await keywordInput.press('Enter');

    await expect(page.getByText('Sản phẩm tư vấn')).toBeVisible();
    await page.getByRole('link', { name: 'Xem', exact: true }).click();
    await expect(page).toHaveURL(/\/prodetail\/42$/);

    await page.goBack();
    await expect(page).toHaveURL(/\/tu-van$/);
    await expect(keywordInput).toHaveValue('áo hoodie đen');
    await expect(page.getByText('Sản phẩm tư vấn')).toBeVisible();
});
