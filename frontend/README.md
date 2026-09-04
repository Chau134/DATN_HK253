# Client

React frontend da duoc nang cap sang Vite + React.

## Stack

- React 19
- Vite
- React Router
- Redux Toolkit
- Axios
- Bootstrap / React Bootstrap
- Sass

## Run Local

```bash
npm install --legacy-peer-deps
npm run dev
```

Mac dinh Vite chay tai:

```text
http://localhost:5173
```

Neu port 5173 dang ban, Vite se tu chuyen sang port khac.

## Scripts

```bash
npm run dev
npm run build
npm run preview
npm run lint
npm run test:browser
```

## Cross-browser smoke tests

Playwright smoke tests cover the public customer flows with deterministic API
responses on Firefox and WebKit at desktop and mobile viewports. WebKit is used
as the automated compatibility proxy for Safari; final device acceptance should
still be checked on Safari when Apple hardware is available.

Install the managed browser binaries once, then run the suite:

```bash
npx playwright install firefox webkit
npm run build
npm run test:browser
```

## Migration Notes

- Da bo `react-scripts` va cac script `NODE_OPTIONS=--openssl-legacy-provider`.
- Entry HTML cua Vite nam tai `index.html`.
- Source React dung JSX da duoc doi tu `.js` sang `.jsx` de Vite 8 build on dinh.
- `public/index.html` la template CRA cu va khong con duoc Vite su dung.
