/**
 * Domain Ontology Service
 * Backend domain_ontologies.py ile senkronize
 * Farklı IoT domain'leri için ontoloji konfigürasyonları
 */

// Domain ontology configurations - backend ile senkronize
export const DOMAIN_ONTOLOGIES = {
  earthquake: {
    prefix: "eq",
    namespace: "https://earthquake.innova.com.tr/ont#",
    label: "Deprem İzleme",
    labelEn: "Earthquake Monitoring",
    color: "red",
    bgColor: "bg-red-100",
    textColor: "text-red-700",
    darkBgColor: "dark:bg-red-900/30",
    darkTextColor: "dark:text-red-300",
    icon: "Activity",
    types: ["SeismicStation", "Seismometer", "Accelerograph", "DataLogger"],
    properties: ["magnitude", "depth", "pga", "pgv", "intensity", "epicenter"],
  },
  // Deprem senaryosu dışındaki domainler - geçici olarak devre dışı
  // manufacturing: {
  //   prefix: "mfg",
  //   namespace: "https://manufacturing.innova.com.tr/ont#",
  //   label: "Üretim",
  //   labelEn: "Manufacturing",
  //   color: "blue",
  //   bgColor: "bg-blue-100",
  //   textColor: "text-blue-700",
  //   darkBgColor: "dark:bg-blue-900/30",
  //   darkTextColor: "dark:text-blue-300",
  //   icon: "Factory",
  //   types: ["ProductionLine", "Machine", "Robot", "Conveyor", "QualityStation"],
  //   properties: ["cycleTime", "oee", "throughput", "defectRate", "availability"],
  // },
  smart_building: {
    prefix: "bldg",
    namespace: "https://smartbuilding.innova.com.tr/ont#",
    label: "Akıllı Bina",
    labelEn: "Smart Building",
    color: "green",
    bgColor: "bg-green-100",
    textColor: "text-green-700",
    darkBgColor: "dark:bg-green-900/30",
    darkTextColor: "dark:text-green-300",
    icon: "Building2",
    types: ["Building", "Floor", "Room", "HVAC", "Elevator", "ParkingLot"],
    properties: ["occupancy", "energyConsumption", "comfortIndex", "airQuality"],
  },
  environmental: {
    prefix: "env",
    namespace: "https://environment.innova.com.tr/ont#",
    label: "Çevresel",
    labelEn: "Environmental",
    color: "yellow",
    bgColor: "bg-yellow-100",
    textColor: "text-yellow-700",
    darkBgColor: "dark:bg-yellow-900/30",
    darkTextColor: "dark:text-yellow-300",
    icon: "Cloud",
    types: ["WeatherStation", "AirQualityMonitor", "WaterQualityMonitor", "NoiseMonitor"],
    properties: ["pm25", "pm10", "humidity", "windSpeed", "precipitation", "uvIndex"],
  },
  // agriculture: {
  //   prefix: "agri",
  //   namespace: "https://agriculture.innova.com.tr/ont#",
  //   label: "Tarım",
  //   labelEn: "Agriculture",
  //   color: "emerald",
  //   bgColor: "bg-emerald-100",
  //   textColor: "text-emerald-700",
  //   darkBgColor: "dark:bg-emerald-900/30",
  //   darkTextColor: "dark:text-emerald-300",
  //   icon: "Leaf",
  //   types: ["Greenhouse", "Field", "IrrigationSystem", "WeatherStation"],
  //   properties: ["soilMoisture", "soilPH", "cropHealth", "yieldPrediction"],
  // },
  energy: {
    prefix: "nrg",
    namespace: "https://energy.innova.com.tr/ont#",
    label: "Enerji",
    labelEn: "Energy",
    color: "orange",
    bgColor: "bg-orange-100",
    textColor: "text-orange-700",
    darkBgColor: "dark:bg-orange-900/30",
    darkTextColor: "dark:text-orange-300",
    icon: "Zap",
    types: ["PowerPlant", "Substation", "SmartMeter", "SolarPanel", "WindTurbine"],
    properties: ["powerOutput", "gridFrequency", "voltage", "loadFactor"],
  },
};

// NOTE: A conflicting relationship type vocabulary used to live here. It named
// types differently from the ontology (containedIn vs isContainedIn) and gave
// them a third, unrelated colour scheme. The vocabulary is published by the
// backend now — use useOntologyStore / ontologyService instead.

/**
 * Domain'e gore Thing type'larini dondur
 * @param {string} domain - Domain key (earthquake, manufacturing, etc.)
 * @returns {string[]} - Prefixed type listesi (eq:SeismicStation, etc.)
 */
export const getDomainTypes = (domain) => {
  const config = DOMAIN_ONTOLOGIES[domain];
  if (!config) return ["saref:Device", "sosa:Platform"];
  return config.types.map((t) => `${config.prefix}:${t}`);
};

/**
 * Type string'den domain'i bul
 * @param {string} typeString - Type string (eq:SeismicStation, etc.)
 * @returns {string|null} - Domain key veya null
 */
export const getDomainFromType = (typeString) => {
  if (!typeString || !typeString.includes(":")) return null;

  const prefix = typeString.split(":")[0];
  for (const [key, config] of Object.entries(DOMAIN_ONTOLOGIES)) {
    if (config.prefix === prefix) {
      return key;
    }
  }
  return null;
};

/**
 * Type string icin badge renk class'larini dondur
 * @param {string} typeString - Type string
 * @returns {string} - Tailwind CSS class'lari
 */
export const getDomainBadgeClasses = (typeString) => {
  const domain = getDomainFromType(typeString);
  if (domain && DOMAIN_ONTOLOGIES[domain]) {
    const config = DOMAIN_ONTOLOGIES[domain];
    return `${config.bgColor} ${config.textColor} ${config.darkBgColor} ${config.darkTextColor}`;
  }
  // Varsayilan WoT/SAREF/SOSA tipleri icin
  return "bg-primary/10 text-primary dark:bg-primary/20";
};

/**
 * Domain listesini frontend icin formatli dondur
 * @returns {Array} - Domain bilgileri listesi
 * @note label ve labelEn deprecated - UI'da t('wot.domains.${key}') kullanin
 */
export const listDomains = () => {
  return Object.entries(DOMAIN_ONTOLOGIES).map(([key, config]) => ({
    key,
    prefix: config.prefix,
    label: config.label, // deprecated - use i18n
    labelEn: config.labelEn, // deprecated - use i18n
    icon: config.icon,
    color: config.color,
  }));
};

export default {
  DOMAIN_ONTOLOGIES,
  getDomainTypes,
  getDomainFromType,
  getDomainBadgeClasses,
  listDomains,
};
