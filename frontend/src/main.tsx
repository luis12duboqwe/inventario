import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./app/App";
import "./styles.css";
// [PACK26-AUTHZ-BOOT-START]
import { AuthzProvider } from "./auth/useAuthz";
// [PACK26-AUTHZ-BOOT-END]

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      {/* [PACK26-AUTHZ-BOOT-START] */}
      <AuthzProvider user={{ id: "1", name: "Demo", role: "GERENTE" }}>
        <App />
      </AuthzProvider>
      {/* [PACK26-AUTHZ-BOOT-END] */}
    </QueryClientProvider>
  </React.StrictMode>
);
