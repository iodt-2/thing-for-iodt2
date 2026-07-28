/**
 * Ontology Service
 *
 * Reads the published information model from the backend. The relationship
 * type vocabulary lives in the ontology, not in frontend constants — adding a
 * type there must be enough for it to appear in the UI.
 */

import axiosInstance from "./axios";

const handleError = (error) => {
  if (error.response) {
    throw new Error(
      error.response.data?.detail ||
        `Error ${error.response.status}: ${error.response.statusText}`
    );
  } else if (error.request) {
    throw new Error("Network error: unable to reach the ontology service");
  }
  throw new Error(error.message || "An unexpected error occurred");
};

const OntologyService = {
  /**
   * Relationship type vocabulary.
   * @param {boolean} includeDerived - include inverse types (isFedBy, ...)
   */
  getRelationshipTypes: async (includeDerived = true) => {
    try {
      const response = await axiosInstance.get("/v2/ontology/relationship-types", {
        params: { include_derived: includeDerived },
      });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  /** ts: classes with their external alignments. */
  getClasses: async () => {
    try {
      const response = await axiosInstance.get("/v2/ontology/classes");
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  /** ts: properties with their external alignments. */
  getProperties: async () => {
    try {
      const response = await axiosInstance.get("/v2/ontology/properties");
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  /**
   * The ontology itself as RDF.
   * @param {string} format - turtle | jsonld | xml | nt
   */
  getOntology: async (format = "turtle") => {
    try {
      const response = await axiosInstance.get("/v2/ontology", {
        params: { format },
        responseType: "text",
      });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },
};

export default OntologyService;
