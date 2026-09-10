/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly NODE_API_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare const __APP_VERSION__: string
