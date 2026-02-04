import { useState, useCallback, useEffect } from "react";
import PropTypes from "prop-types";
import Map, { Marker, NavigationControl, GeolocateControl } from "react-map-gl/maplibre";
import { MapPin, Map as MapIcon, X, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import "maplibre-gl/dist/maplibre-gl.css";

const LocationPicker = ({ location, onChange }) => {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [tempLocation, setTempLocation] = useState(null);

  const [viewport, setViewport] = useState({
    latitude: location?.latitude ? parseFloat(location.latitude) : 39.9334,
    longitude: location?.longitude ? parseFloat(location.longitude) : 32.8597,
    zoom: 10
  });

  const [marker, setMarker] = useState({
    latitude: location?.latitude ? parseFloat(location.latitude) : null,
    longitude: location?.longitude ? parseFloat(location.longitude) : null,
  });

  // Update marker when location prop changes
  useEffect(() => {
    if (location?.latitude && location?.longitude) {
      const lat = parseFloat(location.latitude);
      const lng = parseFloat(location.longitude);
      setMarker({ latitude: lat, longitude: lng });
      setViewport(prev => ({ ...prev, latitude: lat, longitude: lng }));
    }
  }, [location?.latitude, location?.longitude]);

  // Reset temp location when dialog opens
  useEffect(() => {
    if (isDialogOpen) {
      setTempLocation(null);
    }
  }, [isDialogOpen]);

  const handleMapClick = useCallback(async (event) => {
    const { lng, lat } = event.lngLat;
    setMarker({ latitude: lat, longitude: lng });

    // Reverse geocoding to get address
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`
      );
      const data = await response.json();

      const address = data.display_name || `${lat.toFixed(6)}, ${lng.toFixed(6)}`;

      // Try to get altitude from elevation API (optional - may not always work)
      let altitude = "";
      try {
        const elevResponse = await fetch(
          `https://api.open-elevation.com/api/v1/lookup?locations=${lat},${lng}`
        );
        const elevData = await elevResponse.json();
        if (elevData.results && elevData.results[0]) {
          altitude = elevData.results[0].elevation.toString();
        }
      } catch (error) {
        console.log("Could not fetch elevation data:", error);
      }

      const newLocation = {
        latitude: lat.toString(),
        longitude: lng.toString(),
        altitude: altitude,
        address: address
      };

      setTempLocation(newLocation);
    } catch (error) {
      console.error("Error fetching location details:", error);
      const newLocation = {
        latitude: lat.toString(),
        longitude: lng.toString(),
        altitude: "",
        address: `${lat.toFixed(6)}, ${lng.toFixed(6)}`
      };
      setTempLocation(newLocation);
    }
  }, []);

  const handleConfirm = () => {
    if (tempLocation) {
      onChange(tempLocation);
    }
    setIsDialogOpen(false);
  };

  const handleCancel = () => {
    // Reset marker to original location
    if (location?.latitude && location?.longitude) {
      setMarker({
        latitude: parseFloat(location.latitude),
        longitude: parseFloat(location.longitude)
      });
    } else {
      setMarker({ latitude: null, longitude: null });
    }
    setTempLocation(null);
    setIsDialogOpen(false);
  };

  const hasLocation = location?.latitude && location?.longitude;

  return (
    <>
      {/* Compact Location Card */}
      <div className="border rounded-lg p-3 bg-muted/20">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="h-5 w-5 text-muted-foreground" />
            <span className="font-medium text-sm">Location</span>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setIsDialogOpen(true)}
            className="gap-2"
          >
            <MapIcon className="h-4 w-4" />
            {hasLocation ? "Change" : "Select"}
          </Button>
        </div>

        {/* Location Preview */}
        {hasLocation ? (
          <div className="mt-3 space-y-1">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">Lat:</span>
                <span className="font-mono">{parseFloat(location.latitude).toFixed(6)}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">Long:</span>
                <span className="font-mono">{parseFloat(location.longitude).toFixed(6)}</span>
              </div>
            </div>
            {location.address && (
              <p className="text-xs text-muted-foreground line-clamp-2 mt-1">
                {location.address}
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground mt-2">
            No location selected. Click "Select" to choose on map.
          </p>
        )}
      </div>

      {/* Location Picker Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <MapPin className="h-5 w-5" />
              Select Location
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* Map */}
            <div className="w-full h-[400px] rounded-lg overflow-hidden border border-gray-300">
              <Map
                {...viewport}
                onMove={evt => setViewport(evt.viewState)}
                onClick={handleMapClick}
                mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
                style={{ width: "100%", height: "100%" }}
              >
                <NavigationControl position="top-right" />
                <GeolocateControl
                  position="top-right"
                  trackUserLocation
                  onGeolocate={(e) => {
                    const { latitude, longitude } = e.coords;
                    handleMapClick({ lngLat: { lng: longitude, lat: latitude } });
                  }}
                />

                {marker.latitude && marker.longitude && (
                  <Marker
                    latitude={marker.latitude}
                    longitude={marker.longitude}
                    anchor="bottom"
                  >
                    <MapPin className="w-8 h-8 text-red-500" fill="red" />
                  </Marker>
                )}
              </Map>
            </div>

            {/* Selected Location Info */}
            {tempLocation && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-3">
                <div className="flex items-center gap-2 text-green-700 dark:text-green-300 font-medium text-sm mb-2">
                  <Check className="h-4 w-4" />
                  Selected Location
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">Latitude: </span>
                    <span className="font-mono">{parseFloat(tempLocation.latitude).toFixed(6)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Longitude: </span>
                    <span className="font-mono">{parseFloat(tempLocation.longitude).toFixed(6)}</span>
                  </div>
                </div>
                {tempLocation.address && (
                  <p className="text-xs text-muted-foreground mt-2 line-clamp-2">
                    {tempLocation.address}
                  </p>
                )}
              </div>
            )}

            {!tempLocation && (
              <p className="text-sm text-muted-foreground text-center">
                Click on the map to select a location. Use the location button to get your current position.
              </p>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={handleCancel}>
              <X className="h-4 w-4 mr-2" />
              Cancel
            </Button>
            <Button onClick={handleConfirm} disabled={!tempLocation}>
              <Check className="h-4 w-4 mr-2" />
              Confirm Location
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
};

LocationPicker.propTypes = {
  location: PropTypes.shape({
    latitude: PropTypes.string,
    longitude: PropTypes.string,
    altitude: PropTypes.string,
    address: PropTypes.string,
  }),
  onChange: PropTypes.func.isRequired,
};

export default LocationPicker;
