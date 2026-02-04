import axiosInstance from "./axios";

// Tenant header'ını almak için utility fonksiyon
const getTenantHeaders = () => {
  try {
    const currentTenantStr = localStorage.getItem("currentTenant");
    if (currentTenantStr) {
      const currentTenant = JSON.parse(currentTenantStr);
      if (currentTenant?.tenant_id) {
        return {
          'X-Tenant-ID': currentTenant.tenant_id
        };
      }
    }
  } catch (error) {
    console.error('Error getting tenant headers:', error);
  }
  return {};
};

const handleError = (error) => {
  if (error.response) {
    const errorMessage =
      error.response.data.message ||
      error.response.data.description ||
      `Error ${error.response.status}: ${error.response.statusText}`;
    throw new Error(errorMessage);
  } else if (error.request) {
    throw new Error("Network error: Unable to connect to Fuseki service");
  } else {
    throw new Error(`Request failed: ${error.message}`);
  }
};

const createDittoCompatibleId = (wotId) => {
  if (!wotId) {
    //console.error("WoT ID is missing");
    return null;
  }
  
  try {
    // Get current tenant from localStorage
    const currentTenantStr = localStorage.getItem("currentTenant");
    let tenantId = null;
    
    if (currentTenantStr) {
      try {
        const currentTenant = JSON.parse(currentTenantStr);
        if (currentTenant?.tenant_id) {
          tenantId = currentTenant.tenant_id;
        }
      } catch (error) {
        console.warn("Failed to parse current tenant for Ditto ID creation:", error);
      }
    }
    
    // Tenant seçimi yapılmamışsa hata ver
    if (!tenantId) {
      console.error("No tenant selected. Cannot create Ditto compatible ID without tenant context.");
      return null;
    }
    
    // ID'yi : karakterine göre parçala
    const parts = wotId.split(':');
    
    // Entity kısmını al (son parça)
    const entity = parts[parts.length - 1];
    
    // Tenant-aware domain ve entity'yi birleştir
    return `${tenantId}:${entity}`;
  } catch {
    //console.error("Error converting WoT ID to Ditto format:", error);
    return null;
  }
};

const fusekiService = {
  things: {
    // Tüm thing'leri getir
    getAll: async (options = {}) => {
      try {
        const { page = 1, pageSize = 10 } = options;
        const response = await axiosInstance.get('/v2/fuseki/', {
          params: {
            page,
            pageSize
          },
          headers: getTenantHeaders()
        });
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },

    // ID'ye göre thing getir
    getById: async (thingId) => {
      try {
        const response = await axiosInstance.get(
          `/v2/fuseki/${encodeURIComponent(thingId)}`,
          {
            headers: getTenantHeaders()
          }
        );
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },

    // Thing oluştur
    create: async (thingData) => {
      try {
        if (!thingData?.["@id"]) {
          throw new Error("Thing ID (@id) is required");
        }

        const response = await axiosInstance.post('/v2/fuseki/', thingData, {
          headers: getTenantHeaders()
        });
        return response.data;
      } catch (error) {
        console.error("Error in create thing:", error);
        throw handleError(error);
      }
    },

    // Thing güncelle
    update: async (thingId, thingData) => {
      try {
        const response = await axiosInstance.put(
          `/v2/fuseki/${encodeURIComponent(thingId)}`, 
          thingData,
          {
            headers: getTenantHeaders()
          }
        );
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },

    // Thing sil
    delete: async (thingId) => {
      try {
        // Önce WoT thing'i Fuseki'den sil
        await axiosInstance.delete(`/v2/fuseki/${encodeURIComponent(thingId)}`, {
          headers: getTenantHeaders()
        });
        
        // Sonra Ditto senkronizasyonu yap
        try {
          // Ditto ID'sini WoT ID'sinden elde et
          const dittoId = createDittoCompatibleId(thingId);
          if (dittoId) {
            await axiosInstance.delete(`/v2/things/${dittoId}`);
          }
        } catch (dittoError) {
          console.warn(`Warning: Error syncing delete to Ditto: ${dittoError.message}`);
          // Ditto hatası olsa bile işlemi başarılı say
        }
        
        return true;
      } catch (error) {
        throw handleError(error);
      }
    },

    // Thing ara (metin arama)
    search: async (searchQuery) => {
      try {
        console.log('Searching things with query:', searchQuery);
        const headers = getTenantHeaders();
        console.log('Using tenant headers:', headers);

        const response = await axiosInstance.get(`/v2/fuseki/search/`, {
          params: { q: searchQuery },
          headers
        });

        console.log('Search response:', response.data);
        return response.data;
      } catch (error) {
        console.error('Search error:', error);
        throw new Error(`Error searching things: ${error.response?.data?.detail || error.message}`);
      }
    },

    executeSparqlQuery : async (sparqlQuery) => {
      try {
        const response = await axiosInstance.post(`/v2/fuseki/sparql`, {
          query: sparqlQuery
        });
        return response.data;
      } catch (error) {
        throw new Error(`Error executing SPARQL query: ${error.response?.data?.detail || error.message}`);
      }
    },

    saveSearch : async (name, query, isSparql) => {
      try {
        const response = await axiosInstance.post(`/v2/fuseki/saved-searches`, {
          name,
          query,
          isSparql
        });
        return response.data;
      } catch (error) {
        throw new Error(`Error saving search: ${error.response?.data?.detail || error.message}`);
      }
    },

    // Özelliğe göre thing'leri getir
    getByProperty: async (propertyName) => {
      try {
        const response = await axiosInstance.get('/v2/fuseki/', {
          params: { property_name: propertyName }
        });
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    },

    // Belirli bir şeyin belirli bir özelliğini getir
    getProperty: async (thingId, propertyName) => {
      try {
        const response = await axiosInstance.get(
          `/v2/fuseki/${encodeURIComponent(thingId)}/properties/${propertyName}`
        );
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    }
  },
  
  // SPARQL sorgu yönetimi
  sparql: {
    // SPARQL sorgusu çalıştır
    execute : async (sparqlQuery) => {
      try {
        console.log('Executing SPARQL query:', sparqlQuery);
        const headers = getTenantHeaders();
        console.log('Using tenant headers:', headers);

        const response = await axiosInstance.post(`/v2/fuseki/sparql/search`, {
          query: sparqlQuery
        }, {
          headers
        });

        console.log('SPARQL response:', response.data);
        return response.data;
      } catch (error) {
        console.error('SPARQL execution error:', error);
        throw handleError(error);
      }
    },

    // Kullanılabilir SPARQL öneklerini getir
    getPrefixes: async () => {
      try {
        const response = await axiosInstance.get('/v2/fuseki/sparql/prefixes');
        return response.data;
      } catch (error) {
        throw handleError(error);
      }
    }
  },

  // Sistem sağlık kontrolü
  system: {
    checkHealth: async () => {
      try {
        const response = await axiosInstance.get('/v2/fuseki/health');
        return response.data;
      } catch (error) {
        return {
          status: "unhealthy",
          error: error.message,
          detail: "Failed to connect to Fuseki service"
        };
      }
    }
  },


};

export default fusekiService;