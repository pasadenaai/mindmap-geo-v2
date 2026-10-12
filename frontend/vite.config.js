import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Content-Security-Policy is delivered as a <meta> tag in the production build, not as a header:
// API Gateway static header mappings cannot carry single quotes (a `\'` escape is emitted
// literally), and CSP needs 'self'. frame-ancestors is not honoured in <meta>; X-Frame-Options
// DENY (a header) covers framing. Google Fonts is the only third-party origin the app loads.
// TODO: self-host Inter and drop fonts.googleapis.com / fonts.gstatic.com.
const CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' data: https://fonts.gstatic.com",
  "img-src 'self' data: blob:",
  "connect-src 'self'",
  "worker-src 'self' blob:",
  "base-uri 'self'",
  "form-action 'self'",
].join('; ')

function cspMeta() {
  return {
    name: 'csp-meta',
    apply: 'build',   // never in `vite dev`: it would block HMR's inline preamble and websocket
    transformIndexHtml() {
      return [{
        tag: 'meta',
        attrs: { 'http-equiv': 'Content-Security-Policy', content: CSP },
        injectTo: 'head-prepend',
      }]
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:8004'

  return {
    plugins: [react(), cspMeta()],
    server: {
      port: 4203,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
