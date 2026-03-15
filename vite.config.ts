import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import basicSsl from '@vitejs/plugin-basic-ssl';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    const useHttps = env.VITE_DEV_HTTPS === 'true';
    const apiProxyTarget = env.VITE_DEV_API_PROXY_TARGET;

    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
        strictPort: true,
        cors: true,
        allowedHosts: true,
        proxy: apiProxyTarget
          ? {
              '/api': {
                target: apiProxyTarget,
                changeOrigin: true,
                secure: false,
              },
            }
          : undefined,
      },
      plugins: [
        react(),
        useHttps ? basicSsl() : null,
      ].filter(Boolean),
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});
