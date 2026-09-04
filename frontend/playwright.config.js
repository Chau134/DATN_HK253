import { defineConfig, devices } from '@playwright/test';

const desktopViewport = { width: 1440, height: 900 };
const mobileViewport = { width: 390, height: 844 };
const isCI = Boolean(globalThis.process?.env?.CI);

export default defineConfig({
    testDir: './tests',
    timeout: 120_000,
    outputDir: './test-results',
    fullyParallel: false,
    forbidOnly: isCI,
    retries: isCI ? 2 : 0,
    workers: 1,
    reporter: [
        ['list'],
        ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ],
    use: {
        baseURL: 'http://127.0.0.1:4173',
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
    },
    projects: [
        {
            name: 'firefox-desktop',
            use: { ...devices['Desktop Firefox'], viewport: desktopViewport },
        },
        {
            name: 'firefox-mobile',
            use: {
                browserName: 'firefox',
                viewport: mobileViewport,
                deviceScaleFactor: 1,
                hasTouch: true,
            },
        },
        {
            name: 'webkit-desktop',
            use: { ...devices['Desktop Safari'], viewport: desktopViewport },
        },
        {
            name: 'webkit-mobile',
            use: { ...devices['iPhone 13'] },
        },
    ],
    webServer: {
        command: 'npm run preview -- --host 127.0.0.1 --port 4173',
        url: 'http://127.0.0.1:4173',
        reuseExistingServer: !isCI,
        timeout: 120_000,
    },
});
