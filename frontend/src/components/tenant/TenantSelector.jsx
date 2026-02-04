import { useEffect } from "react";
import { Building2, Check, ChevronsUpDown, Loader2 } from "lucide-react";
import PropTypes from 'prop-types';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import useTenantStore from "../../store/useTenantStore";

const TenantSelector = ({ className = "" }) => {
  const {
    currentTenant,
    availableTenants,
    isLoading,
    error,
    fetchTenants,
    switchTenant,
    clearError
  } = useTenantStore();

  // Initialize on mount
  useEffect(() => {
    if (availableTenants.length === 0) {
      fetchTenants();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Clear error on mount
  useEffect(() => {
    if (error) {
      const timer = setTimeout(clearError, 5000);
      return () => clearTimeout(timer);
    }
  }, [error]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleTenantChange = async (tenantId) => {
    try {
      await switchTenant(tenantId);
      
      // Custom event dispatch et (aynı window'daki diğer componentler için)
      window.dispatchEvent(new CustomEvent('tenantChanged', {
        detail: { tenantId }
      }));
    } catch (error) {
      console.error("Failed to switch tenant:", error);
      // Error is handled by the store
    }
  };

  const handleRefresh = async () => {
    try {
      await fetchTenants();
    } catch (error) {
      console.error("Failed to refresh tenants:", error);
    }
  };

  if (isLoading && availableTenants.length === 0) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm text-muted-foreground">Loading tenants...</span>
      </div>
    );
  }

  if (error && availableTenants.length === 0) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Badge variant="destructive">
          <Building2 className="h-3 w-3 mr-1" />
          Error loading tenants
        </Badge>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          disabled={isLoading}
        >
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Select
        value={currentTenant?.tenant_id || ""}
        onValueChange={handleTenantChange}
        disabled={isLoading}
      >
        <SelectTrigger className="w-64">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4" />
            <SelectValue placeholder="Select tenant">
              {currentTenant ? (
                <div className="flex items-center gap-2">
                  <span>{currentTenant.name}</span>
                  {currentTenant.tenant_id === "default" && (
                    <Badge variant="secondary" className="text-xs">
                      Default
                    </Badge>
                  )}
                </div>
              ) : (
                "Select tenant"
              )}
            </SelectValue>
          </div>
        </SelectTrigger>
        
        <SelectContent>
          {availableTenants.map((tenant) => (
            <SelectItem key={tenant.tenant_id} value={tenant.tenant_id}>
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  <div className="flex flex-col">
                    <span className="font-medium">{tenant.name}</span>
                    {tenant.description && (
                      <span className="text-xs text-muted-foreground">
                        {tenant.description}
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center gap-1">
                  {tenant.tenant_id === "default" && (
                    <Badge variant="secondary" className="text-xs">
                      Default
                    </Badge>
                  )}
                  {!tenant.is_active && (
                    <Badge variant="outline" className="text-xs">
                      Inactive
                    </Badge>
                  )}
                  {currentTenant?.tenant_id === tenant.tenant_id && (
                    <Check className="h-4 w-4 text-primary" />
                  )}
                </div>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Refresh button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={handleRefresh}
        disabled={isLoading}
        className="px-2"
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ChevronsUpDown className="h-4 w-4" />
        )}
      </Button>

      {/* Error indicator */}
      {error && (
        <Badge variant="destructive" className="text-xs">
          Error
        </Badge>
      )}
    </div>
  );
};

TenantSelector.propTypes = {
  className: PropTypes.string
};

export default TenantSelector; 