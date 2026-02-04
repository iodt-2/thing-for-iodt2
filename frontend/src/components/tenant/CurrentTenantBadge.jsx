import { Building2, AlertCircle } from "lucide-react";
import PropTypes from 'prop-types';
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import useTenantStore from "../../store/useTenantStore";

const CurrentTenantBadge = ({ className = "", showDetails = false }) => {
  const { currentTenant, isLoading, error } = useTenantStore();

  // Don't render if loading and no current tenant
  if (isLoading && !currentTenant) {
    return null;
  }

  // Error state
  if (error && !currentTenant) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger>
            <Badge variant="destructive" className={`${className}`}>
              <AlertCircle className="h-3 w-3 mr-1" />
              No Tenant
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p>Error loading tenant: {error}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // No tenant selected
  if (!currentTenant) {
    return (
      <Badge variant="outline" className={`${className}`}>
        <Building2 className="h-3 w-3 mr-1" />
        No Tenant
      </Badge>
    );
  }

  // Default tenant
  if (currentTenant.tenant_id === "default") {
    const badgeContent = (
      <Badge variant="secondary" className={`${className}`}>
        <Building2 className="h-3 w-3 mr-1" />
        {showDetails ? currentTenant.name : "Default"}
      </Badge>
    );

    if (showDetails && currentTenant.description) {
      return (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger>
              {badgeContent}
            </TooltipTrigger>
            <TooltipContent>
              <div className="space-y-1">
                <p className="font-medium">{currentTenant.name}</p>
                <p className="text-sm text-muted-foreground">{currentTenant.description}</p>
                <p className="text-xs text-muted-foreground">ID: {currentTenant.tenant_id}</p>
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      );
    }

    return badgeContent;
  }

  // Regular tenant
  const badgeVariant = currentTenant.is_active ? "default" : "outline";
  const badgeContent = (
    <Badge variant={badgeVariant} className={`${className}`}>
      <Building2 className="h-3 w-3 mr-1" />
      {showDetails ? currentTenant.name : (currentTenant.name.length > 12 
        ? `${currentTenant.name.slice(0, 12)}...` 
        : currentTenant.name)}
      {!currentTenant.is_active && (
        <span className="ml-1 text-xs">(Inactive)</span>
      )}
    </Badge>
  );

  // Show tooltip with details if requested
  if (showDetails || currentTenant.description || !currentTenant.is_active) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger>
            {badgeContent}
          </TooltipTrigger>
          <TooltipContent>
            <div className="space-y-1">
              <p className="font-medium">{currentTenant.name}</p>
              {currentTenant.description && (
                <p className="text-sm text-muted-foreground">{currentTenant.description}</p>
              )}
              <p className="text-xs text-muted-foreground">ID: {currentTenant.tenant_id}</p>
              {!currentTenant.is_active && (
                <p className="text-xs text-orange-500">⚠️ Tenant is inactive</p>
              )}
              {currentTenant.max_things && (
                <p className="text-xs text-muted-foreground">
                  Max Things: {currentTenant.max_things}
                </p>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return badgeContent;
};

CurrentTenantBadge.propTypes = {
  className: PropTypes.string,
  showDetails: PropTypes.bool
};

export default CurrentTenantBadge; 