/**
 * Simulation Service
 *
 * Client for the hazard simulation endpoints: a partner platform computes the
 * shaking, the platform works out what stops working because of it.
 */

import axiosInstance from "./axios";

const handleError = (error) => {
  if (error.response) {
    throw new Error(
      error.response.data?.detail ||
        `Error ${error.response.status}: ${error.response.statusText}`
    );
  } else if (error.request) {
    throw new Error("Network error: unable to reach the simulation service");
  }
  throw new Error(error.message || "An unexpected error occurred");
};

const SimulationService = {
  /** Partner platforms and what each of them can do. */
  listProviders: async () => {
    try {
      const response = await axiosInstance.get("/v2/integrations/providers");
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  /** Recent real earthquakes, so a scenario can start from one that happened. */
  listEvents: async (provider, { days = 7, minMagnitude = 4 } = {}) => {
    try {
      const response = await axiosInstance.get(
        `/v2/integrations/${provider}/events`,
        { params: { days, min_magnitude: minMagnitude } }
      );
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  /**
   * Run a scenario.
   *
   * A simulation calls out to the partner and then walks the graph, so it can
   * take a while — the default axios timeout is too short for it.
   */
  runEarthquake: async (provider, scenario) => {
    try {
      const response = await axiosInstance.post(
        `/v2/simulation/${provider}/earthquake`,
        scenario,
        { timeout: 120000 }
      );
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  listRuns: async (tenant) => {
    try {
      const response = await axiosInstance.get("/v2/simulation/runs", {
        params: { tenant },
      });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },

  getRun: async (runId, tenant) => {
    try {
      const response = await axiosInstance.get(`/v2/simulation/runs/${runId}`, {
        params: { tenant },
      });
      return response.data;
    } catch (error) {
      handleError(error);
    }
  },
};

export default SimulationService;
