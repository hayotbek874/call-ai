/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GEMINI_API_KEY?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_DEV_HTTPS?: string;
  readonly VITE_DEV_API_PROXY_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
