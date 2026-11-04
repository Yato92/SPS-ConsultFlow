import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

const prototypeIndex: Plugin = {
  name: 'prototype-index',
  configureServer(server) {
    server.middlewares.use((req, _res, next) => {
      if (req.url === '/prototype' || req.url === '/prototype/') {
        req.url = '/prototype/index.html';
      }
      next();
    });
  },
  configurePreviewServer(server) {
    server.middlewares.use((req, _res, next) => {
      if (req.url === '/prototype' || req.url === '/prototype/') {
        req.url = '/prototype/index.html';
      }
      next();
    });
  },
};

export default defineConfig({
  plugins: [react(), prototypeIndex],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
