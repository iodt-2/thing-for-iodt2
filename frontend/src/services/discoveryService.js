/**
 * Discovery Service
 *
 * Client for the W3C WoT Discovery style endpoints: geographic proximity,
 * capability search, and the saved query catalog.
 */

import axiosInstance from "./axios";

const handleError = (error) => {
  if (error.response) {
    throw new Error(
      error.response.data?.detail ||
        `Error ${error.response.status}: ${error.response.statusText}`
    );
  } else if (error.request) {
    throw new Error("Network error: unable to reach the discovery service");
  }
  throw new Error(error.message || "An unexpected error occurred");
};

/**
 * Flatten a Thing Description for the results list.
 *
 * The list renders whatever keys it finds as chips, so empty values are
 * dropped and properties are summarised into one readable string rather than
 * left as objects that would print as truncated JSON.
 */
export const thingDescriptionToResult = (td) => {
  const properties = Object.entries(td.properties || {})
    .map(([name, prop]) => (prop.unit ? `${name} (${prop.unit})` : name))
    .join(", ");

  const coordinates =
    td["geo:lat"] != null && td["geo:long"] != null
      ? `${td["geo:lat"]}, ${td["geo:long"]}`
      : null;

  const result = {
    id: td.id,
    name: td.title,
    description: td.description,
    type: "TwinInterface",
    thingType: td["ts:thingType"],
    address: td["ts:address"],
    coordinates,
    distanceKm: td["ts:distanceKm"] != null ? `${td["ts:distanceKm"]} km` : null,
    properties: properties || null,
  };

  return Object.fromEntries(
    Object.entries(result).filter(([, value]) => value != null && value !== "")
  );
};

const DiscoveryService = {
  /** Twins within radius_km of a point, nearest first. */
  findNearby: async ({ lat, lon, radiusKm = 1, limit = 20 }) => {
    try {
      const response = await axiosInstance.get("/v2/discovery/nearby", {
        params: { lat, lon, radius_km: radiusKm, limit },
      });
      return response.data.map(thingDescriptionToResult);
    } catch (error) {
      handleError(error);
    }
  },

  /** Twins matching capability criteria; criteria combine with AND. */
  findByCapability: async ({ property, unit, thingType, dtdl, limit = 20 }) => {
    try {
      const response = await axiosInstance.get("/v2/discovery/by-capability", {
        params: {
          property: property || undefined,
          unit: unit || undefined,
          thing_type: thingType || undefined,
          dtdl: dtdl || undefined,
          limit,
        },
      });
      return response.data.map(thingDescriptionToResult);
    } catch (error) {
      handleError(error);
    }
  },

  /** Inventory of properties, units and twin types actually present. */
  getCapabilities: async () => {
    try {
      const response = await axiosInstance.get("/v2/discovery/capabilities");
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  /** Saved SPARQL searches from the backend catalog. */
  getSavedQueries: async (category) => {
    try {
      const response = await axiosInstance.get("/v2/discovery/queries", {
        params: category && category !== "all" ? { category } : undefined,
      });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  /** Run a query through the read-only discovery endpoint. */
  runSparql: async ({ query, saved }) => {
    try {
      const response = await axiosInstance.get("/v2/discovery/sparql", {
        params: saved ? { saved } : { q: query },
      });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },
};

export default DiscoveryService;
