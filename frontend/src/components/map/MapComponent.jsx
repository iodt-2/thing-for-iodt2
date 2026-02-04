import React, { useCallback, useEffect, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import Map, { 
  Marker, 
  Popup,
  NavigationControl,
  ScaleControl,
  GeolocateControl
} from 'react-map-gl/maplibre'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { 
  MapPin, 
  Thermometer, 
  Wind, 
  Activity,
  CheckCircle,
  Clock,
  Gauge,
  Volume2
} from 'lucide-react'
import MapStyleSwitcher from './MapStyleSwitcher'
import 'maplibre-gl/dist/maplibre-gl.css'

/**
 * MapComponent - Interactive map for displaying sensor locations and data
 * 
 * Features:
 * - MapLibre GL JS powered maps
 * - Marker clustering for performance
 * - Real-time sensor data display
 * - Interactive popups with sensor details
 * - Custom markers for different sensor types
 */
const MapComponent = ({
  // Map configuration
  mapStyle = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json', // Free streets style
  center = { lat: 39.9334, lng: 32.8597 }, // Ankara default
  zoom = 16,
  
  // Style switcher configuration - fallback defaults if not provided from dashboard config
  availableStyles = [],
  styleSwitcherConfig = {
    enabled: false,
    position: 'top-right',
    showPreviews: true,
    animationDuration: 300
  },
  onStyleChange = () => {},
  
  // Marker configuration - fallback defaults if not provided from dashboard config
  markerConfig = {
    main_kozalak: {
      active_color: "#10b981",
      inactive_color: "#374151",
      warning_color: "#f59e0b", 
      error_color: "#ef4444",
      size: 36,
      border_width: 4,
      icon: "tower",
      glow_effect: true
    },
    side_kozalak: {
      active_color: "#3b82f6",
      inactive_color: "#4b5563",
      warning_color: "#f97316",
      error_color: "#dc2626", 
      size: 28,
      border_width: 3,
      icon: "sensor",
      glow_effect: true
    }
  },
  
  // Data props
  sensors = [], // Array of sensor data with coordinates
  selectedSensor = null,
  onSensorSelect = () => {},
  
  // Configuration
  enableClustering = true,
  clusterRadius = 50,
  showPopup = true,
  enableControls = true,
  
  // Real-time data
  realtimeData = {},
  lastUpdate = null,
  
  // Styling
  className = '',
  height = '100%',
  width = '100%',
  
  // Callbacks
  onMapLoad = () => {},
  onMapClick = () => {},
  onMarkerClick = () => {}
}) => {
  const mapRef = useRef(null)
  const [viewState, setViewState] = useState({
    longitude: center.lng,
    latitude: center.lat,
    zoom
  })
  const [currentMapStyle, setCurrentMapStyle] = useState(mapStyle)
  const [hoveredSensor, setHoveredSensor] = useState(null)
  const [hoverPopupInfo, setHoverPopupInfo] = useState(null)
  const [clickPopupInfo, setClickPopupInfo] = useState(null)
  const [isPopupHovered, setIsPopupHovered] = useState(false)
  const [mapError, setMapError] = useState(null)
  const hoverTimeoutRef = useRef(null)
  
  // Fallback styles for when primary style fails
  const fallbackStyles = [
    'https://demotiles.maplibre.org/style.json',
    'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
    {
      version: 8,
      sources: {},
      layers: []
    }
  ]

  // Update view state when center/zoom props change
  useEffect(() => {
    setViewState({
      longitude: center.lng,
      latitude: center.lat,
      zoom
    })
  }, [center, zoom])

  // Update current style when mapStyle prop changes
  useEffect(() => {
    setCurrentMapStyle(mapStyle)
  }, [mapStyle])

  /**
   * Handle map load errors (e.g., style not loading)
   */
  const handleMapError = useCallback((error) => {
    console.error('Map error:', error);
    setMapError(error);
    
    // Try fallback styles
    const currentIndex = fallbackStyles.findIndex(s => 
      typeof s === 'string' ? s === currentMapStyle : false
    );
    
    if (currentIndex < fallbackStyles.length - 1) {
      const nextStyle = fallbackStyles[currentIndex + 1];
      console.log('Trying fallback style:', nextStyle);
      setCurrentMapStyle(nextStyle);
      setMapError(null);
    }
  }, [currentMapStyle, fallbackStyles]);

  /**
   * Handle map style change from style switcher
   */
  const handleStyleChange = useCallback((newStyleUrl) => {
    setCurrentMapStyle(newStyleUrl)
    setMapError(null) // Clear any previous errors
    onStyleChange(newStyleUrl)
  }, [onStyleChange])

  /**
   * Handle map click events
   */
  const handleMapClick = useCallback((event) => {
    // Close popups on map click
    setClickPopupInfo(null)
    setHoverPopupInfo(null)
    onMapClick(event)
  }, [onMapClick])

  /**
   * Handle marker click events
   */
  const handleMarkerClick = useCallback((sensor, event) => {
    
    // Prevent map click event
    event?.originalEvent?.stopPropagation()
    
    // Set click popup info (different from hover popup)
    setClickPopupInfo({
      sensor,
      coordinates: [sensor.longitude, sensor.latitude]
    })
    
    // Clear hover popup when clicked
    setHoverPopupInfo(null)
    
    // Call parent callback
    onSensorSelect(sensor)
    onMarkerClick(sensor, event)
  }, [onSensorSelect, onMarkerClick])

  /**
   * Handle marker hover events
   */
  const handleMarkerHover = useCallback((sensor, isHovering) => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current)
      hoverTimeoutRef.current = null
    }

    if (isHovering) {
      setHoverPopupInfo({
        sensor,
        coordinates: [sensor.longitude, sensor.latitude]
      })
    } else {
      // Delay closing the popup to allow clicking the button
      hoverTimeoutRef.current = setTimeout(() => {
        if (!isPopupHovered) {
          setHoverPopupInfo(null)
        }
      }, 300) // 300ms delay
    }
  }, [isPopupHovered])

  /**
   * Handle popup hover to prevent closing
   */
  const handlePopupHover = useCallback((isHovering) => {
    setIsPopupHovered(isHovering)
    
    if (!isHovering) {
      // Close popup when mouse leaves both marker and popup
      hoverTimeoutRef.current = setTimeout(() => {
        setHoverPopupInfo(null)
      }, 200)
    } else if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current)
      hoverTimeoutRef.current = null
    }
  }, [])

  /**
   * Get marker icon based on sensor type
   */
  const getMarkerIcon = (sensor) => {
    const sensorType = sensor.type || 'side_kozalak'
    const config = markerConfig[sensorType] || markerConfig.side_kozalak
    const iconSize = config.size > 30 ? "w-8 h-8" : "w-6 h-6"
    
    if (sensorType === 'main_kozalak') {
      return <Activity className={iconSize} />
    }
    return <MapPin className={iconSize} />
  }

  /**
   * Get marker color based on sensor status
   */
  const getMarkerColor = (sensor) => {
    const sensorType = sensor.type || 'side_kozalak'
    const config = markerConfig[sensorType] || markerConfig.side_kozalak
    
    // Use sensor status directly (online/offline)
    const status = sensor.status || 'offline'
    
    // For future use - check for error conditions in sensor data
    const hasErrors = sensor.errorCount > 0 || (sensor.sensorData && 
      Object.values(sensor.sensorData).some(val => val === null || val === undefined))
    if (hasErrors) return config.error_color
    
    // For future use - check for warnings
    const hasWarnings = sensor.warningCount > 0
    if (hasWarnings) return config.warning_color
    
    // Online = active color, offline = inactive color
    return status === 'online' ? config.active_color : config.inactive_color
  }

  /**
   * Get marker size based on sensor type
   */
  const getMarkerSize = (sensor) => {
    const sensorType = sensor.type || 'side_kozalak'
    const config = markerConfig[sensorType] || markerConfig.side_kozalak
    return config.size
  }

  /**
   * Get marker border width based on sensor type
   */
  const getMarkerBorderWidth = (sensor) => {
    const sensorType = sensor.type || 'side_kozalak'
    const config = markerConfig[sensorType] || markerConfig.side_kozalak
    return config.border_width
  }

  /**
   * Check if marker should have glow effect
   */
  const getMarkerGlowEffect = (sensor) => {
    const sensorType = sensor.type || 'side_kozalak'
    const config = markerConfig[sensorType] || markerConfig.side_kozalak
    return config.glow_effect
  }

  /**
   * Format sensor data for popup display
   */
  const formatSensorData = (sensor) => {
    const sensorData = sensor.sensorData || {}
    const data = []
    
    // Temperature
    if (sensorData.temperature !== undefined) {
      data.push({
        icon: <Thermometer className="w-4 h-4 text-red-500 dark:text-red-400" />,
        label: 'Temperature',
        value: `${sensorData.temperature} °C`
      })
    }
    
    // CO2
    if (sensorData.co2 !== undefined) {
      data.push({
        icon: <Wind className="w-4 h-4 text-green-500" />,
        label: 'CO2',
        value: `${sensorData.co2} ppm`
      })
    }
    
    // Pressure
    if (sensorData.pressure !== undefined) {
      data.push({
        icon: <Gauge className="w-4 h-4 text-purple-500" />,
        label: 'Barometer',
        value: `${sensorData.pressure} hPa`
      })
    }
    
    // Sound Level
    if (sensorData.sound_level !== undefined) {
      data.push({
        icon: <Volume2 className="w-4 h-4 text-orange-500" />,
        label: 'Sound Level',
        value: `${sensorData.sound_level} dB`
      })
    }
    
    // VOC
    if (sensorData.voc !== undefined) {
      data.push({
        icon: <Wind className="w-4 h-4 text-yellow-500 dark:text-yellow-400" />,
        label: 'VOC',
        value: `${sensorData.voc} ppb`
      })
    }
    
    // CO
    if (sensorData.co !== undefined) {
      data.push({
        icon: <Wind className="w-4 h-4 text-gray-500" />,
        label: 'CO',
        value: `${sensorData.co} ppm`
      })
    }
    
    return data
  }

  /**
   * Get sensor status for display
   */
  const getSensorStatus = (sensor) => {
    // Use the sensor's own status field
    const status = sensor.status || 'offline'
    
    // Check if we have recent sensor data
    const hasRecentData = sensor.lastUpdate && 
      (new Date() - new Date(sensor.lastUpdate)) < 60 * 60 * 1000 // 1 hour
    
    if (status === 'online' && hasRecentData) {
      return { 
        status: 'online', 
        label: 'Online', 
        color: 'bg-green-500',
        icon: <CheckCircle className="w-3 h-3" />
      }
    }
    
    return { 
      status: 'online', 
      label: 'Online', 
      color: 'bg-green-500',
      icon: <CheckCircle className="w-3 h-3" /> // TODO fix icon
    }
  }

  /**
   * Format last update time
   */
  const formatLastUpdate = (timestamp) => {
    if (!timestamp) return 'uNKNOWN'
    
    const now = new Date()
    const updateTime = new Date(timestamp)
    const diffMs = now - updateTime
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'Az önce'
    if (diffMins < 60) return `${diffMins} minutes ago`
    
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours} hours ago`
    
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays} days ago`
  }

  return (
    <div className={`relative ${className}`} style={{ height, width }}>
      {/* Map style error warning */}
      {mapError && (
        <div className="absolute top-2 left-1/2 transform -translate-x-1/2 z-50 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg px-4 py-2 shadow-lg">
          <p className="text-sm text-yellow-800 dark:text-yellow-200">
            ⚠️ Map style failed to load. Using fallback style.
          </p>
        </div>
      )}
      
      <Map
        ref={mapRef}
        {...viewState}
        onMove={evt => setViewState(evt.viewState)}
        onClick={handleMapClick}
        onLoad={onMapLoad}
        onError={handleMapError}
        mapStyle={currentMapStyle}
        style={{ width: '100%', height: '100%' }}
        maxZoom={18}
        minZoom={2}
      >
        {/* Navigation Controls */}
        {enableControls && (
          <>
            <NavigationControl position="top-right" />
            <ScaleControl position="bottom-left" />
            <GeolocateControl position="top-right" />
          </>
        )}

        {/* Render sensors as markers */}
        {sensors.map((sensor) => (
          <Marker
            key={sensor.id}
            longitude={sensor.longitude}
            latitude={sensor.latitude}
            onClick={(e) => handleMarkerClick(sensor, e)}
            style={{ cursor: 'pointer' }}
          >
            <div
              className={`
                flex items-center justify-center rounded-full border-white shadow-lg 
                transition-all duration-300 hover:scale-110 
                ${getMarkerGlowEffect(sensor) ? 'shadow-2xl' : ''}
                ${hoveredSensor === sensor.id ? 'scale-110 z-10' : ''}
              `}
              style={{
                backgroundColor: getMarkerColor(sensor),
                borderWidth: `${getMarkerBorderWidth(sensor)}px`,
                borderColor: 'white',
                width: getMarkerSize(sensor),
                height: getMarkerSize(sensor),
                boxShadow: getMarkerGlowEffect(sensor) 
                  ? `0 0 25px ${getMarkerColor(sensor)}50, 0 0 10px ${getMarkerColor(sensor)}80, 0 6px 30px rgba(0,0,0,0.25)` 
                  : '0 6px 30px rgba(0,0,0,0.25)',
                border: `${getMarkerBorderWidth(sensor)}px solid white`
              }}
              onMouseEnter={() => {
                setHoveredSensor(sensor.id)
                handleMarkerHover(sensor, true)
              }}
              onMouseLeave={() => {
                setHoveredSensor(null)
                handleMarkerHover(sensor, false)
              }}
            >
              <div className="text-white">
                {getMarkerIcon(sensor)}
              </div>
            </div>
          </Marker>
        ))}

        {/* Hover Popup - shows on mouse hover */}
        {hoverPopupInfo && showPopup && (
          <Popup
            longitude={hoverPopupInfo.coordinates[0]}
            latitude={hoverPopupInfo.coordinates[1]}
            closeButton={false}
            closeOnClick={false}
            maxWidth="380px"
            offset={[0, -10]}
          >
            <div
              onMouseEnter={() => handlePopupHover(true)}
              onMouseLeave={() => handlePopupHover(false)}
            >
              <Card className="border-0 shadow-xl">
                <CardHeader className="pb-3 p-4">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-semibold">
                      {hoverPopupInfo.sensor.name || hoverPopupInfo.sensor.id}
                    </CardTitle>
                    <Badge 
                      variant="secondary" 
                      className={`${getSensorStatus(hoverPopupInfo.sensor).color} text-white text-sm`}
                    >
                      <span className="flex items-center gap-1">
                        {getSensorStatus(hoverPopupInfo.sensor).icon}
                        {getSensorStatus(hoverPopupInfo.sensor).label}
                      </span>
                    </Badge>
                  </div>
                  {hoverPopupInfo.sensor.description && (
                    <p className="text-sm text-muted-foreground mt-1">
                      {hoverPopupInfo.sensor.description}
                    </p>
                  )}
                </CardHeader>
                
                <CardContent className="pt-0 p-4">
                  {/* Sensor data grid */}
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    {formatSensorData(hoverPopupInfo.sensor).slice(0, 6).map((item, index) => (
                      <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg">
                        {item.icon}
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-medium text-gray-600">{item.label}</div>
                          <div className="text-sm font-semibold truncate">{item.value}</div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Location info */}
                  {hoverPopupInfo.sensor.address && (
                    <div className="text-xs text-muted-foreground mb-3 border-t pt-2">
                      📍 {hoverPopupInfo.sensor.address}
                    </div>
                  )}

                  {/* Action Button */}
                  <Button 
                    size="sm" 
                    className="w-full"
                    onClick={() => {
                      onSensorSelect(hoverPopupInfo.sensor)
                    }}
                  >
                    View Details
                  </Button>
                </CardContent>
              </Card>
            </div>
          </Popup>
        )}

        {/* Click Popup - shows on marker click (more detailed) */}
        {clickPopupInfo && showPopup && (
          <Popup
            longitude={clickPopupInfo.coordinates[0]}
            latitude={clickPopupInfo.coordinates[1]}
            onClose={() => setClickPopupInfo(null)}
            closeButton={true}
            closeOnClick={false}
            maxWidth="320px"
          >
            <Card className="border-0 shadow-none">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">
                    {clickPopupInfo.sensor.name || clickPopupInfo.sensor.id}
                  </CardTitle>
                  <Badge 
                    variant="secondary" 
                    className={`${getSensorStatus(clickPopupInfo.sensor).color} text-white text-xs`}
                  >
                    <span className="flex items-center gap-1">
                      {getSensorStatus(clickPopupInfo.sensor).icon}
                      {getSensorStatus(clickPopupInfo.sensor).label}
                    </span>
                  </Badge>
                </div>
                {clickPopupInfo.sensor.description && (
                  <p className="text-xs text-muted-foreground">
                    {clickPopupInfo.sensor.description}
                  </p>
                )}
              </CardHeader>
              
              <CardContent className="pt-0">
                {/* Full Sensor Data */}
                {/* <div className="space-y-2 mb-3">
                  {formatSensorData(clickPopupInfo.sensor).map((item, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {item.icon}
                        <span className="text-xs font-medium">{item.label}</span>
                      </div>
                      <span className="text-xs text-muted-foreground">{item.value}</span>
                    </div>
                  ))}
                </div> */}

                {/* Device Info */}
                {clickPopupInfo.sensor.manufacturer && (
                  <div className="space-y-1 mb-3 border-t pt-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium">Üretici:</span>
                      <span className="text-xs text-muted-foreground">{clickPopupInfo.sensor.manufacturer}</span>
                    </div>
                    {clickPopupInfo.sensor.model && (
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium">Model:</span>
                        <span className="text-xs text-muted-foreground">{clickPopupInfo.sensor.model}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Last Update */}
                <div className="flex items-center gap-1 text-xs text-muted-foreground border-t pt-2">
                  <Clock className="w-3 h-3" />
                  <span>
                    Son güncelleme: {formatLastUpdate(clickPopupInfo.sensor.lastUpdate)}
                  </span>
                </div>

                {/* Action Button */}
                <Button 
                  size="sm" 
                  className="w-full mt-3"
                  onClick={() => {
                    onSensorSelect(clickPopupInfo.sensor)
                  }}
                >
                  Detayları Görüntüle
                </Button>
              </CardContent>
            </Card>
          </Popup>
        )}
      </Map>

      {/* Map Style Switcher */}
      {styleSwitcherConfig.enabled && (
        <MapStyleSwitcher
          availableStyles={availableStyles}
          currentStyle={currentMapStyle}
          onStyleChange={handleStyleChange}
          position={styleSwitcherConfig.position}
          showPreviews={styleSwitcherConfig.showPreviews}
        />
      )}

      {/* Real-time status indicator */}
      {lastUpdate && (
        <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-2 shadow-sm">
          <div className="flex items-center gap-2 text-xs">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span>Canlı veri: {formatLastUpdate(lastUpdate)}</span>
          </div>
        </div>
      )}
    </div>
  )
}

MapComponent.propTypes = {
  // Map configuration
  mapStyle: PropTypes.string,
  center: PropTypes.shape({
    lat: PropTypes.number.isRequired,
    lng: PropTypes.number.isRequired
  }),
  zoom: PropTypes.number,
  
  // Style switcher configuration
  availableStyles: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    url: PropTypes.string.isRequired,
    preview: PropTypes.string,
    category: PropTypes.string.isRequired
  })),
  styleSwitcherConfig: PropTypes.shape({
    enabled: PropTypes.bool,
    position: PropTypes.string,
    showPreviews: PropTypes.bool,
    animationDuration: PropTypes.number
  }),
  onStyleChange: PropTypes.func,
  
  // Marker configuration
  markerConfig: PropTypes.shape({
    main_kozalak: PropTypes.shape({
      active_color: PropTypes.string,
      inactive_color: PropTypes.string,
      warning_color: PropTypes.string,
      error_color: PropTypes.string,
      size: PropTypes.number,
      border_width: PropTypes.number,
      icon: PropTypes.string,
      glow_effect: PropTypes.bool
    }),
    side_kozalak: PropTypes.shape({
      active_color: PropTypes.string,
      inactive_color: PropTypes.string,
      warning_color: PropTypes.string,
      error_color: PropTypes.string,
      size: PropTypes.number,
      border_width: PropTypes.number,
      icon: PropTypes.string,
      glow_effect: PropTypes.bool
    })
  }),
  
  // Data props
  sensors: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    longitude: PropTypes.number.isRequired,
    latitude: PropTypes.number.isRequired,
    type: PropTypes.string,
    status: PropTypes.string,
    name: PropTypes.string,
    description: PropTypes.string,
    sensorData: PropTypes.object,
    lastUpdate: PropTypes.string
  })),
  selectedSensor: PropTypes.object,
  onSensorSelect: PropTypes.func,
  
  // Configuration
  enableClustering: PropTypes.bool,
  clusterRadius: PropTypes.number,
  showPopup: PropTypes.bool,
  enableControls: PropTypes.bool,
  
  // Real-time data
  realtimeData: PropTypes.object,
  lastUpdate: PropTypes.string,
  
  // Styling
  className: PropTypes.string,
  height: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  width: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  
  // Callbacks
  onMapLoad: PropTypes.func,
  onMapClick: PropTypes.func,
  onMarkerClick: PropTypes.func
}

export default MapComponent