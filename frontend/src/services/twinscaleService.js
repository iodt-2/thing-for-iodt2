/**
 * TwinScale-Lite Service
 *
 * API service for TwinScale YAML creation, storage, and management.
 * Direct form-to-YAML-to-RDF workflow without WoT conversion.
 */

import axiosInstance from "./axios";

// Get tenant headers from localStorage
const getTenantHeaders = () => {
  try {
    const selectedTenant = localStorage.getItem("selectedTenant");
    if (selectedTenant) {
      return { "X-Tenant-ID": selectedTenant };
    }
  } catch (error) {
    console.error("Error getting tenant headers:", error);
  }
  return {};
};

// Error handler
const handleError = (error) => {
  if (error.response) {
    const errorMessage =
      error.response.data.detail ||
      error.response.data.message ||
      `Error ${error.response.status}: ${error.response.statusText}`;
    throw new Error(errorMessage);
  } else if (error.request) {
    throw new Error("Network error: Unable to connect to TwinScale service");
  } else {
    throw new Error(error.message || "An unexpected error occurred");
  }
};

/**
 * Create TwinScale Thing directly from form data
 * @param {Object} formData - Form data for the TwinScale Thing
 * @returns {Promise<Object>} Created thing response
 */
const createTwinScaleThing = async (formData) => {
  try {
    const response = await axiosInstance.post(
      "/v2/twinscale/create",
      formData,
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * List all TwinScale Interfaces
 * @param {string} nameFilter - Optional name filter
 * @param {number} limit - Maximum results
 * @returns {Promise<Object>} List of interfaces
 */
const listInterfaces = async (nameFilter = null, limit = 100) => {
  try {
    const params = { limit };
    if (nameFilter) params.name_filter = nameFilter;

    const response = await axiosInstance.get(
      "/v2/twinscale/rdf/interfaces",
      { params, headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * List all TwinScale Instances
 * @param {string} interfaceName - Optional interface filter
 * @param {number} limit - Maximum results
 * @returns {Promise<Object>} List of instances
 */
const listInstances = async (interfaceName = null, limit = 100) => {
  try {
    const params = { limit };
    if (interfaceName) params.interface_name = interfaceName;

    const response = await axiosInstance.get(
      "/v2/twinscale/rdf/instances",
      { params, headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Get TwinScale Interface details
 * @param {string} interfaceName - Interface name
 * @returns {Promise<Object>} Interface details
 */
const getInterfaceDetails = async (interfaceName) => {
  try {
    const response = await axiosInstance.get(
      `/v2/twinscale/rdf/interfaces/${interfaceName}`,
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Export TwinScale YAML as ZIP
 * @param {string} interfaceName - Interface name to export
 * @returns {Promise<Blob>} ZIP file blob
 */
const exportAsZip = async (interfaceName) => {
  try {
    const response = await axiosInstance.get(
      `/v2/twinscale/export/${interfaceName}`,
      {
        headers: getTenantHeaders(),
        responseType: "blob"
      }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Delete TwinScale Interface
 * @param {string} interfaceName - Interface name to delete
 * @returns {Promise<Object>} Delete response
 */
const deleteInterface = async (interfaceName) => {
  try {
    const response = await axiosInstance.delete(
      `/v2/twinscale/rdf/interfaces/${interfaceName}`,
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Execute custom SPARQL query
 * @param {string} query - SPARQL SELECT query
 * @param {number} limit - Maximum results
 * @returns {Promise<Object>} Query results
 */
const executeSparqlQuery = async (query, limit = 100) => {
  try {
    const response = await axiosInstance.post(
      "/v2/twinscale/rdf/query",
      { query, limit },
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Validate TwinScale YAML
 * @param {string} yamlContent - YAML content to validate
 * @param {string} kind - "TwinInterface" or "TwinInstance"
 * @returns {Promise<Object>} Validation result
 */
const validateYaml = async (yamlContent, kind) => {
  try {
    const response = await axiosInstance.post(
      "/v2/twinscale/validate",
      { yaml_content: yamlContent, kind },
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

const TwinScaleService = {
  // Creation
  createTwinScaleThing,

  // Listing
  listInterfaces,
  listInstances,

  // Details
  getInterfaceDetails,

  // Export
  exportAsZip,

  // Delete
  deleteInterface,

  // Query
  executeSparqlQuery,

  // Validation
  validateYaml,
};

export default TwinScaleService;
