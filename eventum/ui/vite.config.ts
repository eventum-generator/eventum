import react from '@vitejs/plugin-react';
import path from 'node:path';
import { defineConfig } from 'vite';
import svgr from 'vite-plugin-svgr';

export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: ['babel-plugin-react-compiler'],
      },
    }),
    svgr(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:9474',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, '../www'),
    emptyOutDir: true,
  },
});
