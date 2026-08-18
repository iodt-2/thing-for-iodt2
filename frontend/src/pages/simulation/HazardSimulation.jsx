import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Clock,
  Loader2,
  MapPin,
  Play,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useTranslation } from "react-i18next";
import SimulationService from "@/services/simulationService";

const PROVIDER = "netcad";

/** Kadıköy, where the demo scenario lives. */
const DEFAULT_SCENARIO = {
  latitude: 40.9836,
  longitude: 29.0303,
  magnitude: 6.5,
  depth_km: 10,
  radius_km: 25,
  tenant: "netcad",
  apply_status: false,
  persist: true,
};

const severityTone = (severity) => {
  if (severity >= 0.75) return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
  if (severity >= 0.5) return "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300";
  if (severity >= 0.25) return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  return "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300";
};

const percent = (value) => `${Math.round((value || 0) * 100)}%`;

const HazardSimulation = () => {
  const { t } = useTranslation();

  const [scenario, setScenario] = useState(DEFAULT_SCENARIO);
  const [events, setEvents] = useState([]);
  const [eventsError, setEventsError] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;

    SimulationService.listEvents(PROVIDER, { days: 30, minMagnitude: 4 })
      .then((data) => {
        if (!cancelled) setEvents((data?.events || []).slice(0, 8));
      })
      .catch((err) => {
        // The feed is a convenience; losing it must not block running a scenario
        if (!cancelled) setEventsError(err.message);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const update = (field) => (event) => {
    const value = event.target.value;
    setScenario((current) => ({ ...current, [field]: value }));
  };

  const useEvent = (event) => {
    setScenario((current) => ({
      ...current,
      latitude: event.latitude,
      longitude: event.longitude,
      magnitude: event.magnitude || current.magnitude,
      depth_km: event.depth_km || current.depth_km,
    }));
  };

  const run = async () => {
    setIsRunning(true);
    setError(null);
    setResult(null);
    try {
      const payload = {
        latitude: Number(scenario.latitude),
        longitude: Number(scenario.longitude),
        magnitude: Number(scenario.magnitude),
        depth_km: Number(scenario.depth_km),
        radius_km: Number(scenario.radius_km),
        tenant: scenario.tenant || undefined,
        apply_status: scenario.apply_status,
        persist: scenario.persist,
      };
      setResult(await SimulationService.runEarthquake(PROVIDER, payload));
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRunning(false);
    }
  };

  const failed = new Set(result?.failed || []);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Zap className="h-6 w-6 text-amber-500" />
          {t("simulation.title") || "Hazard Simulation"}
        </h1>
        <p className="text-muted-foreground mt-1">
          {t("simulation.subtitle") ||
            "The partner platform computes the shaking. The twin graph works out what stops working because of it."}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Scenario */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">
              {t("simulation.scenario") || "Scenario"}
            </CardTitle>
            <CardDescription>
              {t("simulation.scenarioHint") ||
                "Epicentre, magnitude, and how far around it to look for twins."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="latitude">{t("simulation.latitude") || "Latitude"}</Label>
                <Input id="latitude" value={scenario.latitude} onChange={update("latitude")} />
              </div>
              <div>
                <Label htmlFor="longitude">{t("simulation.longitude") || "Longitude"}</Label>
                <Input id="longitude" value={scenario.longitude} onChange={update("longitude")} />
              </div>
              <div>
                <Label htmlFor="magnitude">{t("simulation.magnitude") || "Magnitude"}</Label>
                <Input id="magnitude" value={scenario.magnitude} onChange={update("magnitude")} />
              </div>
              <div>
                <Label htmlFor="depth">{t("simulation.depth") || "Depth (km)"}</Label>
                <Input id="depth" value={scenario.depth_km} onChange={update("depth_km")} />
              </div>
              <div>
                <Label htmlFor="radius">{t("simulation.radius") || "Radius (km)"}</Label>
                <Input id="radius" value={scenario.radius_km} onChange={update("radius_km")} />
              </div>
              <div>
                <Label htmlFor="tenant">{t("simulation.tenant") || "Tenant"}</Label>
                <Input id="tenant" value={scenario.tenant} onChange={update("tenant")} />
              </div>
            </div>

            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="pr-3">
                <Label htmlFor="apply-status" className="text-sm">
                  {t("simulation.applyStatus") || "Degrade relationships"}
                </Label>
                <p className="text-xs text-muted-foreground mt-1">
                  {t("simulation.applyStatusHint") ||
                    "Writes ts:Degraded onto the affected relationships in the live graph."}
                </p>
              </div>
              <Switch
                id="apply-status"
                checked={scenario.apply_status}
                onCheckedChange={(checked) =>
                  setScenario((current) => ({ ...current, apply_status: checked }))
                }
              />
            </div>

            <Button className="w-full" onClick={run} disabled={isRunning}>
              {isRunning ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-2" />
              )}
              {t("simulation.run") || "Run scenario"}
            </Button>

            {error && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Real events */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="h-5 w-5" />
              {t("simulation.recentEvents") || "Recent earthquakes"}
            </CardTitle>
            <CardDescription>
              {t("simulation.recentEventsHint") ||
                "Read straight from the partner feed. Nothing is stored — pick one to start a scenario from something that really happened."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {eventsError && (
              <Alert>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{eventsError}</AlertDescription>
              </Alert>
            )}
            {!eventsError && events.length === 0 && (
              <p className="text-sm text-muted-foreground">
                {t("common.loading") || "Loading..."}
              </p>
            )}
            <div className="space-y-2">
              {events.map((event) => (
                <button
                  key={event.id}
                  onClick={() => useEvent(event)}
                  className="w-full flex items-center justify-between gap-3 rounded-lg border p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
                      M{event.magnitude}
                    </Badge>
                    <span className="truncate text-sm font-medium">{event.place}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                    <span>{event.time}</span>
                    <MapPin className="h-3 w-3" />
                    <span>
                      {event.latitude}, {event.longitude}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Results */}
      {result && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Activity className="h-5 w-5 text-red-500" />
                {t("simulation.directDamage") || "Direct damage"}
              </CardTitle>
              <CardDescription>
                {result.subjects} {t("simulation.subjectsSent") || "twins were sent to the partner model"}
                {result.run_id ? ` · ${result.run_id}` : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {result.direct.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  {result.note || t("simulation.noDamage") || "No twin was affected."}
                </p>
              )}
              <div className="space-y-2">
                {result.direct.map((impact) => (
                  <div
                    key={impact.thing}
                    className="flex items-center justify-between gap-3 rounded-lg border p-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{impact.thing}</p>
                      <p className="text-xs text-muted-foreground">
                        {impact.damage_state}
                        {impact.pga != null ? ` · PGA ${impact.pga}` : ""}
                        {impact.distance_km != null ? ` · ${impact.distance_km} km` : ""}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {failed.has(impact.thing) && (
                        <Badge variant="outline" className="text-xs">
                          {t("simulation.failed") || "out of service"}
                        </Badge>
                      )}
                      <Badge className={severityTone(impact.severity)}>
                        {percent(impact.severity)}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <ArrowRight className="h-5 w-5 text-indigo-500" />
                {t("simulation.knockOn") || "Knock-on effects"}
              </CardTitle>
              <CardDescription>
                {t("simulation.knockOnHint") ||
                  "Twins that were not shaken but lose their function through the graph."}
                {result.degraded_relationships > 0
                  ? ` · ${result.degraded_relationships} ${t("simulation.degraded") || "relationships degraded"}`
                  : ""}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {result.propagated.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  {t("simulation.noKnockOn") || "Nothing else depends on what failed."}
                </p>
              )}
              <div className="space-y-2">
                {result.propagated.map((impact) => (
                  <div
                    key={impact.thing}
                    className="flex items-center justify-between gap-3 rounded-lg border p-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{impact.thing}</p>
                      <p className="text-xs text-muted-foreground truncate">
                        {impact.via_thing} <span className="mx-1">→</span>
                        <span className="font-mono">{impact.via_type}</span>
                        <span className="mx-1">·</span>
                        {impact.depth} {t("simulation.hops") || "hop(s)"}
                      </p>
                    </div>
                    <Badge className={severityTone(impact.severity)}>
                      {percent(impact.severity)}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default HazardSimulation;
