/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  // Agrega aquí otros prefijos VITE_ que use el proyecto si es necesario
  readonly VITE_SOFTMOBILE_ENABLE_CATALOG_PRO?: string;
  readonly VITE_SOFTMOBILE_ENABLE_TRANSFERS?: string;
  readonly VITE_SOFTMOBILE_ENABLE_PURCHASES_SALES?: string;
  readonly VITE_SOFTMOBILE_ENABLE_ANALYTICS_ADV?: string;
  readonly VITE_SOFTMOBILE_ENABLE_2FA?: string;
  readonly VITE_SOFTMOBILE_ENABLE_HYBRID_PREP?: string;
  readonly VITE_SOFTMOBILE_ENABLE_PRICE_LISTS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
