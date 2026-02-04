import { create } from "zustand";
import tenantService from "../services/tenantService";

// LocalStorage keys
const CURRENT_TENANT_KEY = "currentTenant";

const useTenantStore = create((set, get) => ({
  // State
  currentTenant: JSON.parse(localStorage.getItem(CURRENT_TENANT_KEY)) || null,
  availableTenants: [],
  isLoading: false,
  error: null,

  // Actions
  fetchTenants: async (activeOnly = true, usePublicEndpoint = false) => {
    try {
      set({ isLoading: true, error: null });

      // Check if user is authenticated
      const hasToken = !!localStorage.getItem("access_token");

      // Use public endpoint if explicitly requested or if user is not authenticated
      const tenants = (usePublicEndpoint || !hasToken)
        ? await tenantService.getPublicTenants(activeOnly)
        : await tenantService.getAllTenants(activeOnly);

      set({
        availableTenants: tenants,
        isLoading: false
      });

      // If no current tenant selected and tenants available, set first as default
      const currentTenant = get().currentTenant;
      if (!currentTenant && tenants.length > 0) {
        const defaultTenant = tenants.find(t => t.tenant_id === "default") || tenants[0];
        get().switchTenant(defaultTenant.tenant_id);
      }

      return tenants;
    } catch (error) {
      console.error("Error fetching tenants:", error);
      set({
        error: error.message,
        isLoading: false
      });
      throw error;
    }
  },

  switchTenant: async (tenantId) => {
    try {
      set({ isLoading: true, error: null });
      
      const tenants = get().availableTenants;
      const tenant = tenants.find(t => t.tenant_id === tenantId);
      
      if (!tenant) {
        throw new Error(`Tenant with ID ${tenantId} not found`);
      }

      // Update store state
      set({ 
        currentTenant: tenant, 
        isLoading: false 
      });
      
      // Persist to localStorage
      localStorage.setItem(CURRENT_TENANT_KEY, JSON.stringify(tenant));
      
      return tenant;
    } catch (error) {
      console.error("Error switching tenant:", error);
      set({ 
        error: error.message, 
        isLoading: false 
      });
      throw error;
    }
  },

  createTenant: async (tenantData) => {
    try {
      set({ isLoading: true, error: null });
      const newTenant = await tenantService.createTenant(tenantData);
      
      // Add to available tenants
      const currentTenants = get().availableTenants;
      set({ 
        availableTenants: [...currentTenants, newTenant],
        isLoading: false 
      });
      
      return newTenant;
    } catch (error) {
      console.error("Error creating tenant:", error);
      set({ 
        error: error.message, 
        isLoading: false 
      });
      throw error;
    }
  },

  updateTenant: async (tenantId, tenantData) => {
    try {
      set({ isLoading: true, error: null });
      const updatedTenant = await tenantService.updateTenant(tenantId, tenantData);
      
      // Update in available tenants
      const tenants = get().availableTenants;
      const updatedTenants = tenants.map(t => 
        t.tenant_id === updatedTenant.tenant_id ? updatedTenant : t
      );
      
      // Update current tenant if it's the one being updated
      const currentTenant = get().currentTenant;
      const newCurrentTenant = currentTenant?.tenant_id === updatedTenant.tenant_id 
        ? updatedTenant 
        : currentTenant;
      
      set({ 
        availableTenants: updatedTenants,
        currentTenant: newCurrentTenant,
        isLoading: false 
      });
      
      // Update localStorage if current tenant was updated
      if (newCurrentTenant !== currentTenant) {
        localStorage.setItem(CURRENT_TENANT_KEY, JSON.stringify(newCurrentTenant));
      }
      
      return updatedTenant;
    } catch (error) {
      console.error("Error updating tenant:", error);
      set({ 
        error: error.message, 
        isLoading: false 
      });
      throw error;
    }
  },

  deleteTenant: async (tenantId, hardDelete = true) => {
    try {
      set({ isLoading: true, error: null });
      await tenantService.deleteTenant(tenantId, hardDelete);
      
      // Handle different delete types
      if (hardDelete) {
        // Hard delete: Remove from available tenants immediately
        const tenants = get().availableTenants;
        const updatedTenants = tenants.filter(t => t.tenant_id !== tenantId);
        
        // If deleted tenant was current, clear current tenant
        const currentTenant = get().currentTenant;
        let newCurrentTenant = currentTenant;
        
        if (currentTenant?.tenant_id === tenantId) {
          newCurrentTenant = null;
          localStorage.removeItem(CURRENT_TENANT_KEY);
        }
        
        set({ 
          availableTenants: updatedTenants,
          currentTenant: newCurrentTenant,
          isLoading: false 
        });
      } else {
        // Soft delete (deactivate): Update the tenant status locally
        const tenants = get().availableTenants;
        const updatedTenants = tenants.map(t => 
          t.tenant_id === tenantId 
            ? { ...t, is_active: false }
            : t
        );
        
        set({ 
          availableTenants: updatedTenants,
          isLoading: false 
        });
      }
      
      return true;
    } catch (error) {
      console.error("Error deleting tenant:", error);
      set({ 
        error: error.message, 
        isLoading: false 
      });
      throw error;
    }
  },

  // YENİ: Tenant ID formatters - Eclipse Ditto compliant format
  formatThingId: (deviceId) => {
    const { currentTenant } = get();
    if (!currentTenant || currentTenant.tenant_id === 'default') {
      return deviceId;
    }
    
    // Remove existing namespace if any
    if (deviceId && deviceId.includes(':')) {
      deviceId = deviceId.split(':', 1)[1];
    }
    
    // Eclipse Ditto compliant format: {tenant}:{device-name}
    return `${currentTenant.tenant_id}:${deviceId}`;
  },
  
  parseThingId: (thingId) => {
    const { currentTenant } = get();
    if (!currentTenant || !thingId || !thingId.includes(':')) {
      return thingId;
    }
    
    // Extract device part from {tenant}:device format
    const parts = thingId.split(':');
    if (parts.length > 1) {
      const namespace = parts[0];
      // Validate namespace matches current tenant
      if (namespace === currentTenant.tenant_id) {
        return parts.slice(1).join(':');
      }
    }
    return thingId; // Return original if format doesn't match
  },
  
  formatPolicyId: (policyName) => {
    const { currentTenant } = get();
    if (!currentTenant || currentTenant.tenant_id === 'default') {
      return policyName;
    }
    
    // Remove existing namespace if any
    if (policyName && policyName.includes(':')) {
      policyName = policyName.split(':', 1)[1];
    }
    
    // Eclipse Ditto compliant format: {tenant}:{policy-name}
    return `${currentTenant.tenant_id}:${policyName}`;
  },

  // Utility actions
  clearError: () => set({ error: null }),
  
  clearCurrentTenant: () => {
    set({ currentTenant: null });
    localStorage.removeItem(CURRENT_TENANT_KEY);
  },

  // Initialize store - load from localStorage and fetch tenants
  initialize: async () => {
    try {
      // Load from localStorage first
      const savedTenant = localStorage.getItem(CURRENT_TENANT_KEY);
      if (savedTenant) {
        const tenant = JSON.parse(savedTenant);
        set({ currentTenant: tenant });
      }
      
      // Then fetch latest tenants from API
      await get().fetchTenants();
    } catch (error) {
      console.error("Error initializing tenant store:", error);
      // Don't throw error on initialization failure
    }
  }
}));

export default useTenantStore; 