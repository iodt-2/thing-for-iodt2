/**
 * Twin-Lite Axios Configuration
 *
 * Simplified HTTP client without authentication.
 */

import axios from "axios";

// Base URL configuration
const baseURL = import.meta.env.DEV
  ? "/api"
  : (import.meta.env.VITE_API_URL || "/api");

const axiosInstance = axios.create({
  baseURL: baseURL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 10000,
});

// Request interceptor
axiosInstance.interceptors.request.use(
  (config) => {
    // Tenant header injection — reads from 'currentTenant' (JSON object set by useTenantStore)
    try {
      const tenantData = localStorage.getItem("currentTenant");
      if (tenantData) {
        const tenant = JSON.parse(tenantData);
        if (tenant?.tenant_id) {
          config.headers["X-Tenant-ID"] = tenant.tenant_id;
        }
      }
    } catch {
      // ignore parse errors
    }

    return config;
  },
  (error) => {
    console.error("Request Error:", error);
    return Promise.reject(error);
  }
);

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("Response Error:", error.config?.url, error.response?.status);
    return Promise.reject(error);
  }
);

export default axiosInstance;
