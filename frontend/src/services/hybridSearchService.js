/**
 * Hybrid Search Service
 * Combines SPARQL (schema) + Ditto (values) searches
 */

import axiosInstance from "./axios";

/**
 * Search things by property value using hybrid search (SPARQL + Ditto)
 * @param {string} property - Property name (e.g., 'temperature')
 * @param {string} operator - Comparison operator ('gt', 'lt', 'eq', 'gte', 'lte', 'ne')
 * @param {number} value - Threshold value
 * @param {string} tenantId - Optional tenant ID filter
 * @returns {Promise<Object>} - Search results with metadata
 */
export async function searchByPropertyValue(property, operator, value, tenantId = null) {
  try {
    // Call backend hybrid search endpoint
    const params = new URLSearchParams({
      property,
      operator,
      value: value.toString(),
    });
    
    if (tenantId) {
      params.append('tenant_id', tenantId);
    }

    const response = await axiosInstance.get(`/v2/search/hybrid?${params.toString()}`);
    
    // Log search results
    console.log(`🔍 Hybrid search completed in ${response.data.query_time_ms}ms`);
    console.log(`📊 Schema matches: ${response.data.schema_matches}, Value matches: ${response.data.value_matches}`);
    console.log(`✅ Final results: ${response.data.count}`);
    
    if (response.data.count > 0) {
      console.log(`📋 Things found:`, response.data.results.map(t => t.thingId).join(', '));
    }
    
    return response.data;

  } catch (error) {
    console.error("Hybrid search error:", error);
    throw error;
  }
}

/**
 * Search things with multiple conditions
 * @param {Object} filters - Filter object
 * @returns {Promise<Array>}
 */
export async function advancedSearch(filters) {
  const { property, operator, value, domain, type } = filters;
  
  // Build SPARQL query with additional filters
  let whereClause = `
    ?thing a wot:Thing .
    ?thing wot:hasPropertyAffordance ?prop .
    ?prop wot:name "${property}" .
  `;
  
  if (domain) {
    whereClause += `
    ?thing a ${domain}:${type} .
    `;
  }
  
  const sparqlQuery = `
    PREFIX wot: <https://www.w3.org/2019/wot/td#>
    PREFIX eq: <https://earthquake.innova.com.tr/ont#>
    PREFIX mfg: <https://manufacturing.innova.com.tr/ont#>
    PREFIX bldg: <https://smartbuilding.innova.com.tr/ont#>
    
    SELECT ?thing ?title
    WHERE {
      GRAPH ?g {
        ${whereClause}
        OPTIONAL { ?thing wot:title ?title }
      }
    }
  `;
  
  const response = await axiosInstance.post("/fuseki/query", {
    query: sparqlQuery,
  });
  
  return response.data.results || [];
}

export default {
  searchByPropertyValue,
  advancedSearch,
};
