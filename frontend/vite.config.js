import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const springProxy = {
  target: 'http://localhost:8080',
  changeOrigin: true,
  headers: {
    Origin: 'http://localhost:5173',
  },
  configure: (proxy) => {
    proxy.on('proxyReq', (proxyReq) => {
      proxyReq.setHeader('Origin', 'http://localhost:5173')
      proxyReq.setHeader('origin', 'http://localhost:5173')
    })
  },
}

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/catalog-api': {
        ...springProxy,
        rewrite: (path) => path.replace(/^\/catalog-api/, ''),
      },
      '/ai-api': {
        ...springProxy,
        rewrite: (path) => path.replace(/^\/ai-api/, ''),
      },
      '/spring-api': {
        ...springProxy,
        rewrite: (path) => path.replace(/^\/spring-api/, ''),
      },
    },
  },
})
