import { create } from "zustand";
import fusekiService from "../services/fusekiService";
import dittoService from "../services/dittoService";

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
    const result = `${tenantId}:${entity}`;

    return result;
  } catch (error) {
    console.error("Error converting WoT ID to Ditto format:", error);
    return null;
  }
};

const useFusekiStore = create((set, get) => ({
  things: [],
  isLoading: false,
  error: null,
  searchResults: [],
  searchHistory: [],
  currentTenant: null,

  // CRUD Operasyonları
  fetchThings: async (options = {}) => {
    try {
      set({ isLoading: true, error: null });
      
      // İstek atmadan önce bir timeout başlat - ağ hatalarında sonsuza kadar beklememek için
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error("Request timeout")), 15000)
      );
      
      // Sayfalama parametrelerini options'tan al
      const { page = 1, pageSize = 10 } = options;
      
      // Yarış durumu oluştur - hangisi önce tamamlanırsa o sonuç alınır
      const response = await Promise.race([
        fusekiService.things.getAll({ page, pageSize }),
        timeoutPromise
      ]);
      
      // API response'unu işle
      const thingsData = Array.isArray(response)
        ? response
        : response?.items || [];
      
      // Pagination bilgilerini de sakla (gerekirse)
      const pagination = !Array.isArray(response) && response?.pagination
        ? response.pagination
        : null;
      
      set({ 
        things: thingsData, 
        isLoading: false,
        pagination // Pagination bilgilerini store'a ekledik
      });
      
      return thingsData;
    } catch (error) {
      console.error("Error fetching things:", error);
      
      // Hata durumunda boş bir liste ile devam et
      set({ 
        things: [], // Boş liste ayarla
        isLoading: false,
        error: `Failed to load things: ${error.message}`
      });
      
      // Silme işleminden sonra sunucu hatası olursa otomatik olarak yeniden deneme ekleyin
      if (error?.response?.status === 500) {
        setTimeout(() => {
          get().fetchThings(options).catch(e => console.error("Retry also failed:", e));
        }, 2000); // 2 saniye sonra tekrar dene
      }
      
      return []; // Hata durumunda boş dizi döndür
    }
  },

  createThing: async (thingData) => {
    try {
      set({ isLoading: true, error: null });
      const response = await fusekiService.things.create(thingData);
      await get().fetchThings();
      return response;
    } catch (error) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },

  updateThing: async (thingId, thingData) => {
    try {
      set({ isLoading: true, error: null });
      const response = await fusekiService.things.update(thingId, thingData);
      await get().fetchThings();
      return response;
    } catch (error) {
      set({ error: error.message, isLoading: false });
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  deleteThing: async (thingId) => {
    try {
      set({ isLoading: true, error: null });
      await fusekiService.things.delete(thingId);
      
      // Silme işleminin tamamlanması için kısa bir bekleme süresi
      await new Promise(resolve => setTimeout(resolve, 500));
      
      await get().fetchThings();
    } catch (error) {
      set({ error: error.message, isLoading: false });
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },

  // Yeni metot: WoT Thing'i oluştur ve Ditto'ya da kaydet
  createWoTThingWithDitto: async (thingData) => {
    try {
      set({ isLoading: true, error: null });
    
      // WoT ID kontrolü
      const wotId = thingData["@id"];
      if (!wotId) {
        throw new Error("Thing ID (@id) is required");
      }
      
      // Ditto uyumlu ID oluştur
      const dittoId = createDittoCompatibleId(wotId);
      if (!dittoId) {
        throw new Error("Failed to create Ditto compatible ID");
      }
      
      // Adım 1: WoT Thing oluştur
      const wotResponse = await fusekiService.things.create(thingData);
      
       // Subscribed topic bilgisini al
      const subscribedTopic = wotResponse.subscribed_topic;

      // Adım 2: Ditto Thing oluştur
      try {
        // MQTT topic bilgisini query parametresi olarak gönder
        await dittoService.wot.createFromWoT(dittoId, thingData, subscribedTopic);

      } catch (dittoError) {
        console.error("Ditto creation failed:", dittoError);
        
        // Ditto başarısız olduğu için WoT'u sil (rollback)
        try {
          await fusekiService.things.delete(wotId);
        } catch (rollbackError) {
          // Rollback 404 hatası normal olabilir (WoT thing henüz oluşturulmamışsa)
          if (rollbackError.response?.status === 404) {
            console.warn("WoT rollback: Thing not found (404) - this is expected if WoT creation also failed");
          } else {
            console.error("WoT rollback failed:", rollbackError);
            // 404 dışındaki hatalar için warning ver ama throw etme
            console.warn(
              `WoT Thing created but Ditto mapping failed AND rollback failed. 
              Systems may be out of sync: ${dittoError.message}. Rollback error: ${rollbackError.message}`
            );
          }
        }
        
        // Ditto hatasını yukarı fırlat
        throw new Error(`Ditto mapping failed: ${dittoError.message}`);
      }
    
      // Başarılı ise, things listesini yenile
      await get().fetchThings();
      return wotResponse;
    } catch (error) {
      set({ error: error.message, isLoading: false });
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },
  
  
  // WoT Thing'i güncelle ve Ditto'yu da güncelle
  updateWoTThingWithDitto: async (thingId, thingData) => {
    try {
      set({ isLoading: true, error: null });

      // WoT Thing'i güncelle
      const wotResponse = await fusekiService.things.update(thingId, thingData);

      // Ditto Thing'i güncelle
      try {
        await dittoService.wot.createFromWoT(thingId, thingData);
      } catch {
        //console.error("Failed to update Ditto thing:", dittoError);
      }

      // Thing listesini güncelle
      await get().fetchThings();

      return wotResponse;
    } catch (error) {
      set({ error: error.message, isLoading: false });
      throw error;
    } finally {
      set({ isLoading: false });
    }
  },
  // Search Methods
  searchThings: async (searchQuery) => {
    try {
      set({ isLoading: true, error: null });
      
      // Call the backend search endpoint with the query string
      const results = await fusekiService.things.search(searchQuery); 
      
      // Add the search to history
      const newSearch = {
        id: Date.now(),
        query: searchQuery,
        timestamp: new Date().toLocaleString(),
        count: results.length
      };
      
      set(state => ({ 
        searchResults: results, 
        searchHistory: [newSearch, ...state.searchHistory].slice(0, 20), // Keep only last 20 searches
        isLoading: false 
      }));
      
      return results;
    } catch (error) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },
  
  // Execute custom SPARQL query
  executeSparqlQuery: async (sparqlQuery) => {
    try {
      set({ isLoading: true, error: null });
      
      // Call the backend endpoint that executes SPARQL queries
      const results = await fusekiService.sparql.execute(sparqlQuery);
      
      // Add the SPARQL query to history
      const newSearch = {
        id: Date.now(),
        query: sparqlQuery,
        timestamp: new Date().toLocaleString(),
        type: 'sparql'
      };
      
      set(state => ({ 
        searchResults: results, 
        searchHistory: [newSearch, ...state.searchHistory].slice(0, 20),
        isLoading: false 
      }));
      
      return results;
    } catch (error) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },
  
  // Save a search query
  saveSearch: async (name, query, isSparql = false) => {
    try {
      // Here you could also save this to a backend endpoint if needed
      // For now, we'll just keep it in the store
      const savedSearch = {
        id: Date.now(),
        name,
        query,
        type: isSparql ? 'sparql' : 'simple',
        timestamp: new Date().toLocaleString()
      };
      
      set(state => ({ 
        savedSearches: [...(state.savedSearches || []), savedSearch] 
      }));
      
      return savedSearch;
    } catch (error) {
      set({ error: error.message });
      throw error;
    }
  },
  
  // Clear search history
  clearSearchHistory: () => {
    set({ searchHistory: [] });
  },
  
  // Clear search results
  clearSearchResults: () => {
    set({ searchResults: [] });
  },

  // Tenant management
  setCurrentTenant: (tenant) => {
    set({ currentTenant: tenant });
    // Tenant değiştiğinde things'i yenile
    if (tenant) {
      get().fetchThings().catch(console.error);
    } else {
      set({ things: [] }); // Tenant yoksa things'i temizle
    }
  },

  loadTenantFromStorage: () => {
    try {
      const tenantData = localStorage.getItem('currentTenant');
      if (tenantData) {
        const tenant = JSON.parse(tenantData);
        set({ currentTenant: tenant });
      }
    } catch (error) {
      console.error('Error loading tenant from storage:', error);
    }
  },

  // Utility to check if tenant is selected
  hasTenant: () => {
    const state = get();
    return !!(state.currentTenant?.tenant_id);
  }
}));

export default useFusekiStore;
