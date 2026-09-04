# Cross-browser compatibility evidence

- Run date: 2026-08-30
- Frontend: Vite production build served by `npm run preview`
- Test runner: `@playwright/test` 1.62.1
- Firefox: Playwright build 1538
- WebKit: Playwright build 2336
- Result: 8/8 tests passed in 2.2 minutes

## Projects

- Firefox desktop: 1440 x 900
- Firefox mobile: 390 x 844
- WebKit desktop: 1440 x 900
- WebKit mobile: iPhone 13 profile

## Coverage

The route smoke test covers `/`, `/category`, `/tu-van`, `/login`,
`/register`, `/cart`, and `/contact`. Each route must return a successful
document response, mount React content, produce no page or console errors, and
avoid horizontal document overflow. A separate interaction test verifies that
the login password visibility control changes the input type.

Backend responses are deterministically mocked because this suite isolates
frontend engine and viewport compatibility. WebKit is the automated proxy for
Safari's rendering engine; this run is not a physical Apple-device test.

## Regression fixed

The first run detected that the mobile navigation list was open by default and
intercepted pointer input over the login form. The header now exposes a closed
mobile menu with an accessible toggle and closes it after route navigation.

## Reproduction

```text
npm run build
npm run lint
npm run test:browser
```
