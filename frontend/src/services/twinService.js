/**
 * Twin-Lite Service
 *
 * API service for Twin YAML creation, storage, and management.
 * Direct form-to-YAML-to-RDF workflow without WoT conversion.
 */

import axiosInstance from "./axios";

// Get tenant headers from localStorage — reads 'currentTenant' (JSON) set by useTenantStore
const getTenantHeaders = () => {
  try {
    const tenantData = localStorage.getItem("currentTenant");
    if (tenantData) {
      const tenant = JSON.parse(tenantData);
      if (tenant?.tenant_id) {
        return { "X-Tenant-ID": tenant.tenant_id };
      }
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
    throw new Error("Network error: Unable to connect to Twin service");
  } else {
    throw new Error(error.message || "An unexpected error occurred");
  }
};

/**
 * Create Twin Thing directly from form data
 * @param {Object} formData - Form data for the Twin Thing
 * @returns {Promise<Object>} Created thing response
 */
const createTwinThing = async (formData) => {
  try {
    const response = await axiosInstance.post(
      "/v2/twin/create",
      formData,
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * List all Twin Interfaces
 * @param {string} nameFilter - Optional name filter
 * @param {number} limit - Maximum results
 * @returns {Promise<Object>} List of interfaces
 */
const listInterfaces = async (nameFilter = null, limit = 100) => {
  try {
    const params = { limit };
    if (nameFilter) params.name_filter = nameFilter;

    const response = await axiosInstance.get(
      "/v2/twin/rdf/interfaces",
      { params, headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * List all Twin Instances
 * @param {string} interfaceName - Optional interface filter
 * @param {number} limit - Maximum results
 * @returns {Promise<Object>} List of instances
 */
const listInstances = async (interfaceName = null, limit = 100) => {
  try {
    const params = { limit };
    if (interfaceName) params.interface_name = interfaceName;

    const response = await axiosInstance.get(
      "/v2/twin/rdf/instances",
      { params, headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Get Twin Interface details
 * @param {string} interfaceName - Interface name
 * @returns {Promise<Object>} Interface details
 */
const getInterfaceDetails = async (interfaceName) => {
  try {
    const response = await axiosInstance.get(
      `/v2/twin/rdf/interfaces/${interfaceName}`,
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Export Twin YAML as ZIP
 * @param {string} interfaceName - Interface name to export
 * @returns {Promise<Blob>} ZIP file blob
 */
const exportAsZip = async (interfaceName) => {
  try {
    const response = await axiosInstance.get(
      `/v2/twin/export/${interfaceName}`,
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
 * Delete Twin Interface
 * @param {string} interfaceName - Interface name to delete
 * @returns {Promise<Object>} Delete response
 */
const deleteInterface = async (interfaceName) => {
  try {
    const response = await axiosInstance.delete(
      `/v2/twin/rdf/interfaces/${interfaceName}`,
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Get relationship dependencies for a TwinInterface (before deletion)
 * @param {string} interfaceName
 * @returns {Promise<Object>} { forward_count, inverse_count, forward_targets, inverse_sources }
 */
const getDependencies = async (interfaceName) => {
  try {
    const response = await axiosInstance.get(
      `/v2/twin/rdf/interfaces/${interfaceName}/dependencies`,
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Reactivate an Inactive relationship
 * @param {string} interfaceName - Source interface name
 * @param {string} relName - Relationship name
 * @returns {Promise<Object>} Reactivation result
 */
const reactivateRelationship = async (interfaceName, relName) => {
  try {
    const response = await axiosInstance.put(
      `/v2/twin/rdf/interfaces/${interfaceName}/relationships/${relName}/reactivate`,
      {},
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
      "/v2/twin/rdf/query",
      { query, limit },
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Validate Twin YAML
 * @param {string} yamlContent - YAML content to validate
 * @param {string} kind - "TwinInterface" or "TwinInstance"
 * @returns {Promise<Object>} Validation result
 */
const validateYaml = async (yamlContent, kind) => {
  try {
    const response = await axiosInstance.post(
      "/v2/twin/validate",
      { yaml_content: yamlContent, kind },
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Get tenant graph data (nodes + edges) for visualization
 * @returns {Promise<Object>} { nodes, edges, node_count, edge_count }
 */
const getTenantGraph = async () => {
  try {
    const response = await axiosInstance.get(
      "/v2/twin/rdf/graph",
      { headers: getTenantHeaders() }
    );
    return response.data;
  } catch (error) {
    handleError(error);
  }
};

/**
 * Get location information (address + altitude) from coordinates
 * @param {number} latitude - Latitude coordinate
 * @param {number} longitude - Longitude coordinate
 * @returns {Promise<Object>} Location info with address and altitude
 */
const getLocationInfo = async (latitude, longitude) => {
  try {
    const response = await axiosInstance.get("/v2/twin/location", {
      params: { lat: latitude, lon: longitude },
      headers: getTenantHeaders(),
    });
    return response.data;
  } catch (error) {
    console.error("Error fetching location info:", error);
    // Don't throw, just return null so the app continues working
    return null;
  }
};

const TwinService = {
  // Creation
  createTwinThing,

  // Listing
  listInterfaces,
  listInstances,

  // Details
  getInterfaceDetails,

  // Export
  exportAsZip,

  // Delete
  deleteInterface,

  // Dependencies & Reactivation
  getDependencies,
  reactivateRelationship,

  // Query
  executeSparqlQuery,

  // Validation
  validateYaml,

  // Graph
  getTenantGraph,

  // Location
  getLocationInfo,
};

export default TwinService;
