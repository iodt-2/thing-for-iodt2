import { useState } from "react";
import { Search, Tag, Filter, X, ChevronDown, Save, FileSearch, Clock, Code, Play, Download, Copy, CheckCheck, AlertCircle, Loader2, BookOpen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Link } from "react-router-dom";
import useFusekiStore from "@/store/useFusekiStore";
import { searchByPropertyValue } from "@/services/hybridSearchService";
import { useTranslation } from 'react-i18next';

const SearchThings = () => {
  const { t } = useTranslation();

  // Get store methods
  const {
    isLoading,
    error,
    searchThings,
    executeSparqlQuery,
    saveSearch,
  } = useFusekiStore();

  // Local state
  const [searchQuery, setSearchQuery] = useState("");
  const [advancedFiltersVisible, setAdvancedFiltersVisible] = useState(false);
  const [activeFilters, setActiveFilters] = useState([]);
  const [sparqlMode, setSparqlMode] = useState(false);
  const [searchMode, setSearchMode] = useState("standard"); // "standard" | "sparql" | "value"

  // Value search states
  const [valueSearchProperty, setValueSearchProperty] = useState("temperature");
  const [valueSearchOperator, setValueSearchOperator] = useState("gt");
  const [valueSearchValue, setValueSearchValue] = useState(30);

  // Default SPARQL query updated for GRAPH structure
  const [sparqlQuery, setSparqlQuery] = useState(`PREFIX wot: <https://www.w3.org/2019/wot/td#>
PREFIX ditto: <http://eclipse.org/ditto/ns/things#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?thing ?id ?title ?description
WHERE {
  GRAPH ?g {
    ?thing a wot:Thing .
    OPTIONAL { ?thing ditto:thingId ?id . }
    OPTIONAL { ?thing wot:title ?title . }
    OPTIONAL { ?thing wot:description ?description . }
  }
}
LIMIT 100`);

  const [isCopied, setIsCopied] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [activeTab, setActiveTab] = useState('saved');
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [searchName, setSearchName] = useState("");

  // Simple data structure for saved searches and search history
  const [savedSearches, setSavedSearches] = useState([
    { id: 1, name: t('search.sampleAllDevices'), query: "urn:dev:wot" },
    { id: 2, name: t('search.sampleSensors'), query: "sensor" }
  ]);
  const [searchHistory, setSearchHistory] = useState([]);

  // Query Templates Dialog state
  const [showTemplatesDialog, setShowTemplatesDialog] = useState(false);

  // SPARQL templates - Optimized for earthquake scenario
  const [sparqlTemplates] = useState([
    {
      id: 1,
      name: "All Things",
      description: "List all Things in the system",
      query: `PREFIX wot: <https://www.w3.org/2019/wot/td#>
PREFIX ditto: <http://eclipse.org/ditto/ns/things#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?thing ?id ?title
WHERE {
  GRAPH ?g {
    ?thing a wot:Thing .
    OPTIONAL { ?thing ditto:thingId ?id . }
    OPTIONAL { ?thing wot:title ?title . }
  }
}
LIMIT 100`
    },
    {
      id: 2,
      name: "Search by ID",
      description: "Find Things containing a specific ID",
      query: `PREFIX wot: <https://www.w3.org/2019/wot/td#>
PREFIX ditto: <http://eclipse.org/ditto/ns/things#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?thing ?id ?title
WHERE {
  GRAPH ?g {
    ?thing a wot:Thing .
    OPTIONAL { ?thing ditto:thingId ?id . }
    OPTIONAL { ?thing wot:title ?title . }
    FILTER(CONTAINS(STR(?thing), "urn:dev:wot"))
  }
}
LIMIT 50`
    },
    {
      id: 3,
      name: "Seismic Stations",
      description: "List all seismic monitoring stations",
      domain: "earthquake",
      query: `PREFIX eq: <https://earthquake.innova.com.tr/ont#>
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX wot: <https://www.w3.org/2019/wot/td#>

SELECT ?station ?title ?lat ?long
WHERE {
  GRAPH ?g {
    ?station a eq:SeismicStation .
    OPTIONAL { ?station wot:title ?title }
    OPTIONAL {
      ?station geo:location ?loc .
      ?loc geo:lat ?lat .
      ?loc geo:long ?long .
    }
  }
}
LIMIT 100`
    },
    {
      id: 4,
      name: "Sensor Data",
      description: "Query sensor data from stations",
      domain: "earthquake",
      query: `PREFIX eq: <https://earthquake.innova.com.tr/ont#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX wot: <https://www.w3.org/2019/wot/td#>

SELECT ?station ?sensor ?sensorType ?observes
WHERE {
  GRAPH ?g {
    ?station a eq:SeismicStation .
    ?station sosa:hosts ?sensor .
    OPTIONAL { ?sensor a ?sensorType }
    OPTIONAL { ?sensor sosa:observes ?observes }
  }
}
LIMIT 100`
    },
    {
      id: 5,
      name: "Location Based Search",
      description: "Find stations near specific coordinates",
      domain: "earthquake",
      query: `PREFIX eq: <https://earthquake.innova.com.tr/ont#>
PREFIX geo: <http://www.w3.org/2003/01/geo/wgs84_pos#>
PREFIX wot: <https://www.w3.org/2019/wot/td#>

SELECT ?station ?title ?lat ?long
WHERE {
  GRAPH ?g {
    ?station a eq:SeismicStation .
    OPTIONAL { ?station wot:title ?title }
    ?station geo:location ?loc .
    ?loc geo:lat ?lat .
    ?loc geo:long ?long .
    FILTER(?lat > 38.0 && ?lat < 42.0)
    FILTER(?long > 26.0 && ?long < 45.0)
  }
}
LIMIT 100`
    }
  ]);

  // Add filter
  const addFilter = (filter) => {
    if (!activeFilters.includes(filter)) {
      setActiveFilters([...activeFilters, filter]);
    }
  };

  // Remove filter
  const removeFilter = (filter) => {
    setActiveFilters(activeFilters.filter(f => f !== filter));
  };

  // Build search query from filters
  const buildFilteredQuery = () => {
    let query = searchQuery;

    // Add filters
    activeFilters.forEach(filter => {
      if (filter.startsWith("Type:")) {
        query += ` type:${filter.split(":")[1].trim().toLowerCase()}`;
      } else if (filter.startsWith("Status:")) {
        query += ` status:${filter.split(":")[1].trim().toLowerCase()}`;
      } else if (filter.startsWith("Location:")) {
        query += ` location:"${filter.split(":")[1].trim()}"`;
      } else if (filter.startsWith("Feature:")) {
        query += ` has:${filter.split(":")[1].trim().toLowerCase()}`;
      }
    });

    return query;
  };

  // Perform search
  const performSearch = async () => {
    try {
      setIsSearching(true);
      setSearchError(null);

      if (sparqlMode) {
        // Execute SPARQL query
        const results = await executeSparqlQuery(sparqlQuery);

        // Update results - ensure it's always an array
        setSearchResults(results || []);

        // Set active tab to results regardless of whether we found anything
        setActiveTab('results');

        // Add to search history
        const newSearch = {
          id: Date.now(),
          query: sparqlQuery.substring(0, 50) + (sparqlQuery.length > 50 ? '...' : ''),
          fullQuery: sparqlQuery,
          timestamp: new Date().toLocaleString(),
          type: 'sparql',
          count: results?.length || 0
        };

        setSearchHistory(prev => [newSearch, ...prev.slice(0, 9)]);
      } else {
        // Standard search
        const query = buildFilteredQuery();

        const results = await searchThings(query);

        // Update results - ensure it's always an array
        setSearchResults(results || []);

        // Set active tab to results regardless of whether we found anything
        setActiveTab('results');

        // Add to search history
        const newSearch = {
          id: Date.now(),
          query: query,
          timestamp: new Date().toLocaleString(),
          type: 'standard',
          count: results?.length || 0
        };

        setSearchHistory(prev => [newSearch, ...prev.slice(0, 9)]);
      }
    } catch (error) {
      console.error("Search error:", error);
      setSearchError(error.message);
      // Even when there's an error, we should make sure searchResults is an empty array
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Handle value search
  const handleValueSearch = async () => {
    try {
      setIsSearching(true);
      setSearchError(null);

      // Call hybrid search service
      const data = await searchByPropertyValue(
        valueSearchProperty,
        valueSearchOperator,
        valueSearchValue
      );

      setSearchResults(data.results || []);
      setActiveTab('results');

      // Add to history
      const newSearch = {
        id: Date.now(),
        query: `${valueSearchProperty} ${valueSearchOperator} ${valueSearchValue}`,
        timestamp: new Date().toLocaleString(),
        type: 'value',
        count: data.count,
        queryTime: data.query_time_ms
      };

      setSearchHistory(prev => [newSearch, ...prev.slice(0, 9)]);

    } catch (error) {
      console.error("Value search error:", error);
      setSearchError(error.message || "Search failed");
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Copy SPARQL query to clipboard
  const copyToClipboard = () => {
    navigator.clipboard.writeText(sparqlQuery);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  // Apply SPARQL template
  const applyTemplate = (templateQuery) => {
    setSparqlQuery(templateQuery);
  };

  // Export SPARQL query to file
  const exportQuery = () => {
    const content = sparqlQuery;
    const blob = new Blob([content], { type: 'application/sparql-query' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const timestamp = new Date().toISOString().replace(/:/g, '-').replace(/\..+/, '');
    a.href = url;
    a.download = `sparql-query-${timestamp}.rq`;
    document.body.appendChild(a);
    a.click();

    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 0);
  };

  // Save search
  const handleSaveSearch = async () => {
    if (!searchName.trim()) return;

    try {
      const newSavedSearch = await saveSearch(
        searchName,
        sparqlMode ? sparqlQuery : searchQuery,
        sparqlMode
      );

      setSavedSearches(prev => [...prev, newSavedSearch]);
      setShowSaveDialog(false);
      setSearchName("");
    } catch (error) {
      setSearchError(error.message);
    }
  };


  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">{t('search.title')}</h1>
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">{t('search.searchMode')}:</label>
          <Select value={searchMode} onValueChange={(value) => {
            setSearchMode(value);
            setSparqlMode(value === "sparql");
          }}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder={t('search.searchMode')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="standard">{t('search.standardSearch')}</SelectItem>
              <SelectItem value="value">{t('search.valueSearch')}</SelectItem>
              <SelectItem value="sparql">{t('search.sparqlSearch')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Error message */}
      {(error || searchError) && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {t('search.error')}: {error || searchError}
          </AlertDescription>
        </Alert>
      )}

      {/* Save Search Dialog */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('search.saveSearchDialog')}</DialogTitle>
            <DialogDescription>
              {t('search.saveSearchDialogDesc')}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="search-name">{t('search.searchName')}</Label>
              <Input
                id="search-name"
                value={searchName}
                onChange={(e) => setSearchName(e.target.value)}
                placeholder={t('search.searchNamePlaceholder')}
              />
            </div>
            <div className="space-y-2">
              <Label>{t('search.searchQuery')}</Label>
              <div className="bg-muted p-2 rounded-md text-sm">
                {sparqlMode ? (
                  <code className="whitespace-pre-wrap">{sparqlQuery.substring(0, 150)}...</code>
                ) : (
                  <span>{buildFilteredQuery()}</span>
                )}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSaveDialog(false)}>{t('search.cancel')}</Button>
            <Button onClick={handleSaveSearch}>{t('search.save')}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Standard Search Mode */}
      {searchMode === "standard" ? (
        <Card className="border shadow-sm">
          <CardHeader className="pb-3">
            <CardTitle className="text-xl flex items-center">
              <Search className="mr-2 h-5 w-5" />
              {t('search.searchCriteria')}
            </CardTitle>
            <CardDescription>
              {t('search.searchCriteriaDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Main search field */}
              <div className="flex space-x-2">
                <div className="relative flex-1">
                  <Input
                    placeholder={t('search.searchPlaceholder')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                </div>
                <Button onClick={performSearch} disabled={isSearching || isLoading}>
                  {isSearching ? t('search.searching') : t('search.search')}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setAdvancedFiltersVisible(!advancedFiltersVisible)}
                >
                  <Filter className="h-4 w-4 mr-2" />
                  {t('search.filters')}
                  <ChevronDown className={`h-4 w-4 ml-2 transition-transform ${advancedFiltersVisible ? "rotate-180" : ""}`} />
                </Button>
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        onClick={() => setShowSaveDialog(true)}
                      >
                        <Save className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{t('search.saveSearch')}</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </div>

              {/* Active filters */}
              {activeFilters.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {activeFilters.map((filter, index) => (
                    <Badge key={index} variant="secondary" className="flex items-center gap-1">
                      {filter}
                      <X
                        className="h-3 w-3 cursor-pointer"
                        onClick={() => removeFilter(filter)}
                      />
                    </Badge>
                  ))}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setActiveFilters([])}
                    className="h-6 text-xs"
                  >
                    {t('search.clearAll')}
                  </Button>
                </div>
              )}

              {/* Advanced filters */}
              {advancedFiltersVisible && (
                <div className="border rounded-md p-4 space-y-4 bg-muted/20">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">{t('search.domain')}</label>
                      <Select onValueChange={(value) => addFilter(`Domain: ${value}`)}>
                        <SelectTrigger>
                          <SelectValue placeholder={t('search.allDomains')} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="earthquake">Earthquake Monitoring</SelectItem>
                          <SelectItem value="smart_building">Smart Building</SelectItem>
                          <SelectItem value="environmental">Environmental</SelectItem>
                          <SelectItem value="energy">Energy</SelectItem>
                          {/* Temporarily disabled - not relevant for earthquake scenario
                          <SelectItem value="manufacturing">Manufacturing</SelectItem>
                          <SelectItem value="agriculture">Agriculture</SelectItem>
                          */}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">{t('search.thingType')}</label>
                      <Select onValueChange={(value) => addFilter(`Type: ${value}`)}>
                        <SelectTrigger>
                          <SelectValue placeholder={t('search.allTypes')} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Sensor">Sensor</SelectItem>
                          <SelectItem value="Actuator">Actuator</SelectItem>
                          <SelectItem value="Controller">Controller</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">{t('search.status')}</label>
                      <Select onValueChange={(value) => addFilter(`Status: ${value}`)}>
                        <SelectTrigger>
                          <SelectValue placeholder={t('search.anyStatus')} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Active">Active</SelectItem>
                          <SelectItem value="Inactive">Inactive</SelectItem>
                          <SelectItem value="Maintenance">Maintenance</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium">{t('search.location')}</label>
                      <Select onValueChange={(value) => addFilter(`Location: ${value}`)}>
                        <SelectTrigger>
                          <SelectValue placeholder={t('search.allLocations')} />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Building A">Building A</SelectItem>
                          <SelectItem value="Building B">Building B</SelectItem>
                          <SelectItem value="Warehouse">Warehouse</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Properties Accordion */}
                  <Accordion type="single" collapsible className="w-full">
                    <AccordionItem value="properties">
                      <AccordionTrigger className="text-sm">{t('search.properties')}</AccordionTrigger>
                      <AccordionContent>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                          <div className="space-y-2">
                            <div className="flex items-center space-x-2">
                              <Checkbox
                                id="feature-temperature"
                                onCheckedChange={(checked) => {
                                  if (checked) addFilter("Feature: Temperature");
                                  else removeFilter("Feature: Temperature");
                                }}
                              />
                              <label htmlFor="feature-temperature" className="text-sm">Has temperature feature</label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Checkbox
                                id="feature-humidity"
                                onCheckedChange={(checked) => {
                                  if (checked) addFilter("Feature: Humidity");
                                  else removeFilter("Feature: Humidity");
                                }}
                              />
                              <label htmlFor="feature-humidity" className="text-sm">Has humidity feature</label>
                            </div>
                          </div>
                          <div className="space-y-2">
                            <div className="flex items-center space-x-2">
                              <Checkbox
                                id="feature-status"
                                onCheckedChange={(checked) => {
                                  if (checked) addFilter("Feature: Status");
                                  else removeFilter("Feature: Status");
                                }}
                              />
                              <label htmlFor="feature-status" className="text-sm">Has status feature</label>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Checkbox
                                id="feature-energy"
                                onCheckedChange={(checked) => {
                                  if (checked) addFilter("Feature: Energy");
                                  else removeFilter("Feature: Energy");
                                }}
                              />
                              <label htmlFor="feature-energy" className="text-sm">Has energy feature</label>
                            </div>
                          </div>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>

                  {/* Filter buttons */}
                  <div className="flex justify-end space-x-2">
                    <Button variant="ghost" onClick={() => setAdvancedFiltersVisible(false)}>
                      {t('search.cancel')}
                    </Button>
                    <Button onClick={() => setAdvancedFiltersVisible(false)}>
                      {t('search.applyFilters')}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ) : searchMode === "value" ? (
        /* Value Search Mode */
        <Card className="border shadow-sm">
          <CardHeader>
            <CardTitle className="text-xl flex items-center">
              <Search className="mr-2 h-5 w-5" />
              {t('search.searchByPropertyValues')}
            </CardTitle>
            <CardDescription>
              {t('search.searchByPropertyValuesDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Property Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('search.property')}</label>
                <Select value={valueSearchProperty} onValueChange={setValueSearchProperty}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('search.selectProperty')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="temperature">Temperature</SelectItem>
                    <SelectItem value="humidity">Humidity</SelectItem>
                    <SelectItem value="pressure">Pressure</SelectItem>
                    <SelectItem value="co2">CO2</SelectItem>
                    <SelectItem value="motion">Motion</SelectItem>
                    <SelectItem value="brightness">Brightness</SelectItem>
                    <SelectItem value="voltage">Voltage</SelectItem>
                    <SelectItem value="current">Current</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Operator Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('search.operator')}</label>
                <Select value={valueSearchOperator} onValueChange={setValueSearchOperator}>
                  <SelectTrigger>
                    <SelectValue placeholder={t('search.selectOperator')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gt">Greater than (&gt;)</SelectItem>
                    <SelectItem value="gte">Greater or equal (≥)</SelectItem>
                    <SelectItem value="lt">Less than (&lt;)</SelectItem>
                    <SelectItem value="lte">Less or equal (≤)</SelectItem>
                    <SelectItem value="eq">Equals (=)</SelectItem>
                    <SelectItem value="ne">Not equals (≠)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Value Input */}
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('search.value')}</label>
                <Input
                  type="number"
                  value={valueSearchValue}
                  onChange={(e) => setValueSearchValue(parseFloat(e.target.value) || 0)}
                  placeholder={t('search.enterThresholdValue')}
                />
              </div>

              {/* Search Button */}
              <Button
                onClick={handleValueSearch}
                disabled={isSearching || isLoading}
                className="w-full"
              >
                {isSearching ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('search.searching')}
                  </>
                ) : (
                  <>
                    <Search className="mr-2 h-4 w-4" />
                    Search
                  </>
                )}
              </Button>

              {/* Info Box */}
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  This searches for things that:
                  <ul className="list-disc list-inside mt-2 space-y-1">
                    <li>Have <strong>{valueSearchProperty}</strong> property in their schema (SPARQL)</li>
                    <li>Current value {
                      valueSearchOperator === 'gt' ? '>' :
                        valueSearchOperator === 'gte' ? '≥' :
                          valueSearchOperator === 'lt' ? '<' :
                            valueSearchOperator === 'lte' ? '≤' :
                              valueSearchOperator === 'eq' ? '=' : '≠'
                    } <strong>{valueSearchValue}</strong> (Ditto)</li>
                  </ul>
                </AlertDescription>
              </Alert>
            </div>
          </CardContent>
        </Card>
      ) : (
        /* SPARQL Mode */
        <>
          <Card className="border shadow-sm">
            <CardHeader>
              <CardTitle className="text-xl flex items-center justify-between">
                <div className="flex items-center">
                  <Code className="mr-2 h-5 w-5" />
                  {t('search.sparqlQueryEditor')}
                </div>
                <Button
                  variant="outline"
                  onClick={() => setShowTemplatesDialog(true)}
                  className="gap-2"
                >
                  <BookOpen className="h-4 w-4" />
                  Query Templates
                </Button>
              </CardTitle>
              <CardDescription>
                {t('search.sparqlQueryEditorDesc')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Textarea
                  value={sparqlQuery}
                  onChange={(e) => setSparqlQuery(e.target.value)}
                  className="font-mono min-h-36 text-sm"
                  placeholder={t('search.enterSparqlQuery')}
                />

                <div className="flex justify-between">
                  <div className="flex gap-2">
                    <Button onClick={performSearch} className="gap-2" disabled={isSearching || isLoading}>
                      <Play className="h-4 w-4" />
                      {isSearching ? t('search.running') : t('search.runQuery')}
                    </Button>
                    <Button variant="outline" onClick={copyToClipboard} className="gap-2">
                      {isCopied ? (
                        <>
                          <CheckCheck className="h-4 w-4" />
                          {t('search.copied')}
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4" />
                          {t('search.copy')}
                        </>
                      )}
                    </Button>
                  </div>
                  <div className="flex gap-2">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="outline"
                            onClick={exportQuery}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Export query</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>

                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="outline"
                            onClick={() => setShowSaveDialog(true)}
                          >
                            <Save className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Save this query</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Query Templates Dialog */}
          <Dialog open={showTemplatesDialog} onOpenChange={setShowTemplatesDialog}>
            <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5" />
                  Query Templates
                </DialogTitle>
                <DialogDescription>
                  Select a pre-built SPARQL query template
                </DialogDescription>
              </DialogHeader>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 py-4">
                {sparqlTemplates.map((template) => (
                  <Card key={template.id} className="cursor-pointer hover:border-primary/50 transition-colors">
                    <CardHeader className="py-3">
                      <CardTitle className="text-base flex items-center gap-2">
                        {template.name}
                        {template.domain === "earthquake" && (
                          <Badge variant="destructive" className="text-xs">Earthquake</Badge>
                        )}
                      </CardTitle>
                      <CardDescription className="text-xs">{template.description}</CardDescription>
                    </CardHeader>
                    <CardFooter className="pt-0 pb-3">
                      <Button
                        variant="default"
                        size="sm"
                        className="w-full"
                        onClick={() => {
                          applyTemplate(template.query);
                          setShowTemplatesDialog(false);
                        }}
                      >
                        Use Template
                      </Button>
                    </CardFooter>
                  </Card>
                ))}
              </div>
            </DialogContent>
          </Dialog>

          {/* SPARQL Results - Query altında göster */}
          {searchResults.length > 0 && (
            <Card className="border shadow-sm mt-4">
              <CardHeader className="pb-3">
                <CardTitle className="text-xl flex items-center justify-between">
                  <div className="flex items-center">
                    <FileSearch className="mr-2 h-5 w-5" />
                    Query Results
                  </div>
                  <Badge variant="secondary">
                    {searchResults.length} {searchResults.length === 1 ? 'result' : 'results'}
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="divide-y max-h-96 overflow-y-auto">
                  {searchResults.map((thing, index) => {
                    const thingId = thing.id || thing["@id"] || thing.thingId || thing.thing || `result-${index}`;
                    const thingTitle = thing.title || thing.name || thing.label || (thingId ? thingId.split('/').pop() : 'Unnamed Thing');
                    const displayProps = Object.entries(thing).filter(([key]) => !['thing', 'id', 'title', 'description', 'name', 'label'].includes(key));

                    return (
                      <div key={thingId || index} className="py-3 hover:bg-muted/40 transition-colors rounded-md px-2">
                        <div className="flex justify-between items-start">
                          <div className="w-full">
                            <h3 className="font-medium text-base">{thingTitle}</h3>
                            {thingId && thingId !== `result-${index}` && (
                              <code className="bg-muted px-1 py-0.5 rounded text-xs break-all">
                                {thingId}
                              </code>
                            )}
                            {displayProps.length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-2">
                                {displayProps.map(([key, value]) => (
                                  <div key={key} className="bg-muted/50 text-xs px-2 py-1 rounded flex items-center gap-1">
                                    <span className="font-medium">{key}:</span>
                                    <span className="break-all">
                                      {typeof value === 'object' ?
                                        JSON.stringify(value).substring(0, 50) + (JSON.stringify(value).length > 50 ? '...' : '') :
                                        String(value).substring(0, 50) + (String(value).length > 50 ? '...' : '')}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {/* No Results Message */}
          {searchResults.length === 0 && activeTab === 'results' && (
            <Card className="border shadow-sm mt-4">
              <CardContent className="py-8">
                <div className="text-center text-muted-foreground">
                  <FileSearch className="h-12 w-12 mx-auto mb-2 opacity-20" />
                  <p className="text-lg font-medium">No results found</p>
                  <p className="text-sm mt-1">Try adjusting your query criteria</p>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Search Results */}
      {activeTab === 'results' && (
        <Card className="border shadow-sm mt-6">
          <CardHeader className="pb-3">
            <CardTitle className="text-xl flex items-center justify-between">
              <div className="flex items-center">
                <FileSearch className="mr-2 h-5 w-5" />
                Search Results
              </div>
              <Badge variant="secondary">
                {searchResults.length} {searchResults.length === 1 ? 'result' : 'results'}
              </Badge>
            </CardTitle>
            <CardDescription>
              {searchResults.length > 0
                ? "Click on any result to see details"
                : "No results found. Try adjusting your search criteria."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {searchResults.length > 0 ? (
              <div className="divide-y">
                {searchResults.map((thing, index) => {
                  // Handle both standard Thing format and SPARQL result format
                  const thingId = thing.id || thing["@id"] || thing.thingId || thing.thing || `result-${index}`;
                  const thingTitle = thing.title || thing.name || thing.label || (thingId ? thingId.split('/').pop() : 'Unnamed Thing');
                  const thingDescription = thing.description;

                  // For SPARQL results, check if it's a simple key-value object
                  const isSparqlResult = sparqlMode && !thing["@id"] && !thing.thingId;

                  // Extract displayable properties from SPARQL results
                  const displayProps = isSparqlResult
                    ? Object.entries(thing).filter(([key]) => !['thing', 'id', 'title', 'description', 'name', 'label'].includes(key))
                    : [];

                  return (
                    <div key={thingId || index}>
                      {isSparqlResult ? (
                        // SPARQL result display - show all returned fields
                        <div className="py-4 hover:bg-muted/40 transition-colors rounded-md px-2">
                          <div className="flex justify-between items-start">
                            <div className="w-full">
                              <h3 className="font-medium text-base">
                                {thingTitle}
                              </h3>
                              {thingId && thingId !== `result-${index}` && (
                                <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                                  <code className="bg-muted px-1 py-0.5 rounded text-xs break-all">
                                    {thingId}
                                  </code>
                                </div>
                              )}

                              {/* Display all SPARQL result fields */}
                              {displayProps.length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-2">
                                  {displayProps.map(([key, value]) => (
                                    <div key={key} className="bg-muted/50 text-xs px-2 py-1 rounded flex items-center gap-1">
                                      <span className="font-medium">{key}:</span>
                                      <span className="break-all">
                                        {typeof value === 'object' ?
                                          JSON.stringify(value).substring(0, 50) + (JSON.stringify(value).length > 50 ? '...' : '') :
                                          String(value).substring(0, 50) + (String(value).length > 50 ? '...' : '')}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ) : (
                        // Standard Thing display with link
                        <Link
                          to={`/app/things/wot/${encodeURIComponent(thingId)}/details`}
                          className="block text-inherit no-underline"
                        >
                          <div className="py-4 hover:bg-muted/40 transition-colors cursor-pointer rounded-md px-2">
                            <div className="flex justify-between items-start">
                              <div>
                                <h3 className="font-medium text-base">
                                  {thingTitle}
                                </h3>
                                <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                                  <code className="bg-muted px-1 py-0.5 rounded text-xs">
                                    {thingId}
                                  </code>
                                </div>
                              </div>
                            </div>

                            {thingDescription && (
                              <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                                {thingDescription}
                              </p>
                            )}

                            {/* Properties and features */}
                            {(thing.properties || thing.features) && (
                              <div className="mt-3 flex flex-wrap gap-2">
                                {Object.entries(thing.properties || {}).slice(0, 3).map(([key, value]) => (
                                  <div key={key} className="bg-muted/50 text-xs px-2 py-1 rounded flex items-center gap-1">
                                    <span className="font-medium">{key}:</span>
                                    <span>
                                      {typeof value === 'object' ?
                                        JSON.stringify(value).substring(0, 15) + '...' :
                                        String(value).substring(0, 15) + (String(value).length > 15 ? '...' : '')}
                                    </span>
                                  </div>
                                ))}

                                {Object.keys(thing.features || {}).slice(0, 3).map((feature) => (
                                  <div key={feature} className="bg-blue-100 dark:bg-blue-900/30 text-xs px-2 py-1 rounded text-blue-800 dark:text-blue-300">
                                    {feature}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </Link>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-8 text-center text-muted-foreground">
                <FileSearch className="h-12 w-12 mx-auto mb-2 opacity-20" />
                <p className="text-lg font-medium">No matching results found</p>
                <p className="text-sm mt-1">Try changing your search terms or filters</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Search sources tabs */}
      <Tabs defaultValue="saved" value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="saved" className="flex items-center">
            <Save className="h-4 w-4 mr-2" />
            {t('search.savedSearches')}
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center">
            <Clock className="h-4 w-4 mr-2" />
            {t('search.searchHistory')}
          </TabsTrigger>
          {searchResults && searchResults.length > 0 && (
            <TabsTrigger value="results" className="flex items-center">
              <FileSearch className="h-4 w-4 mr-2" />
              {t('search.results')} ({searchResults.length})
            </TabsTrigger>
          )}
        </TabsList>
        <TabsContent value="saved" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {savedSearches.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {savedSearches.map((saved) => (
                    <Card key={saved.id} className="hover:bg-muted/20 cursor-pointer transition-colors">
                      <CardHeader className="py-3">
                        <CardTitle className="text-base">{saved.name}</CardTitle>
                      </CardHeader>
                      <CardContent className="py-1">
                        <code className="text-xs bg-muted p-1 rounded">{saved.query}</code>
                      </CardContent>
                      <CardFooter className="py-2 flex justify-between">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (saved.type === 'sparql') {
                              setSparqlMode(true);
                              setSparqlQuery(saved.fullQuery || saved.query);
                            } else {
                              setSparqlMode(false);
                              setSearchQuery(saved.query);
                              setActiveFilters([]);
                            }
                          }}
                        >
                          {t('search.use')}
                        </Button>
                        <Button variant="ghost" size="sm">
                          <X className="h-4 w-4" />
                        </Button>
                      </CardFooter>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Tag className="h-12 w-12 mx-auto mb-2" />
                  <h3 className="text-lg font-medium">{t('search.noSavedSearches')}</h3>
                  <p className="mt-1">{t('search.saveFrequentSearches')}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {searchHistory.length > 0 ? (
                <div className="divide-y">
                  {searchHistory.map((history) => (
                    <div key={history.id} className="py-3 flex justify-between items-center group">
                      <div>
                        <code className="text-sm bg-muted p-1 rounded">{history.query}</code>
                        <div className="text-xs text-muted-foreground mt-1">{history.timestamp}</div>
                      </div>
                      <div className="space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (history.type === 'sparql') {
                              setSparqlMode(true);
                              setSparqlQuery(history.fullQuery || history.query);
                            } else {
                              setSparqlMode(false);
                              setSearchQuery(history.query);
                              setActiveFilters([]);
                            }
                          }}
                        >
                          Use
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setShowSaveDialog(true)}
                        >
                          <Save className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Clock className="h-12 w-12 mx-auto mb-2" />
                  <h3 className="text-lg font-medium">No search history</h3>
                  <p className="mt-1">Your searches will appear here</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {searchResults && searchResults.length > 0 && (
          <TabsContent value="results" className="mt-4">
            <div className="flex justify-between mb-4">
              <h3 className="text-lg font-medium">Search Results ({searchResults.length})</h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => performSearch()}
                disabled={isSearching}
              >
                <Search className="h-4 w-4 mr-2" />
                Search Again
              </Button>
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
};

export default SearchThings;