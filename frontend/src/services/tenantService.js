// services/tenantService.js
import axiosInstance from "./axios";

const tenantService = {
  // Error handling utility
  handleError(error) {
    console.error("Tenant Service Error:", error);
    
    if (error.response) {
      // Server error with response
      const message = error.response.data?.detail || 
                     error.response.data?.message || 
                     `Server Error: ${error.response.status}`;
      throw new Error(message);
    } else if (error.request) {
      // Network error
      throw new Error("Network error - please check your connection");
    } else {
      // Other error
      throw new Error(error.message || "An unexpected error occurred");
    }
  },

  // Get all tenants user has access to
  async getAllTenants(activeOnly = false) {
    try {
      const response = await axiosInstance.get("/v2/tenants/", {
        params: { active_only: activeOnly }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Get all tenants without authentication (public endpoint)
  async getPublicTenants(activeOnly = true) {
    try {
      const response = await axiosInstance.get("/v2/tenants/", {
        params: { active_only: activeOnly },
        // Don't add auth header for this request
        headers: {
          'X-Skip-Auth': 'true'
        }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Get specific tenant by ID
  async getTenant(tenantId) {
    try {
      const response = await axiosInstance.get(`/v2/tenants/${tenantId}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Create new tenant
  async createTenant(tenantData) {
    try {
      const response = await axiosInstance.post("/v2/tenants/", tenantData);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Update existing tenant
  async updateTenant(tenantId, tenantData) {
    try {
      const response = await axiosInstance.put(`/v2/tenants/${tenantId}`, tenantData);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Delete tenant
  async deleteTenant(tenantId, hardDelete = true) {
    try {
      const response = await axiosInstance.delete(`/v2/tenants/${tenantId}`, {
        params: { hard_delete: hardDelete }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Deactivate tenant (soft delete)
  async deactivateTenant(tenantId) {
    try {
      const response = await axiosInstance.delete(`/v2/tenants/${tenantId}`, {
        params: { hard_delete: false }
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Get tenant statistics
  async getTenantStats(tenantId) {
    try {
      const response = await axiosInstance.get(`/v2/tenants/${tenantId}/stats`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Get tenant limits/validation
  async getTenantLimits(tenantId) {
    try {
      const response = await axiosInstance.get(`/v2/tenants/${tenantId}/limits`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Get user's tenants (for current user)
  async getUserTenants() {
    try {
      const response = await axiosInstance.get("/v2/tenants/user/me/tenants/");
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Assign user to tenant
  async assignUserToTenant(tenantId, userId, role = 'member') {
    try {
      const response = await axiosInstance.post(`/v2/tenants/${tenantId}/users`, {
        user_id: userId,
        role: role
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Remove user from tenant
  async removeUserFromTenant(tenantId, userId) {
    try {
      const response = await axiosInstance.delete(`/v2/tenants/${tenantId}/users/${userId}`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Update user role in tenant
  async updateUserRole(tenantId, userId, role) {
    try {
      const response = await axiosInstance.put(`/v2/tenants/${tenantId}/users/${userId}/role`, {
        role: role
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Get tenant users
  async getTenantUsers(tenantId) {
    try {
      const response = await axiosInstance.get(`/v2/tenants/${tenantId}/users`);
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  // Validate tenant name availability
  async validateTenantId(tenantId) {
    try {
      const response = await axiosInstance.get(`/v2/tenants/validate/${tenantId}`);
      // Backend now always returns 200 OK with availability status
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }
};

export default tenantService; 