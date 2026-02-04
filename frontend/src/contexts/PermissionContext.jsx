import React, { createContext, useContext } from 'react';

/**
 * Placeholder Permission Context for TwinScale-Lite
 * No permissions/RBAC in lite version - all actions allowed
 */
const PermissionContext = createContext({
    can: () => true,
    hasPermission: () => true,
    canCreate: true,
    canEdit: true,
    canDelete: true,
    canView: true,
    isSuperAdmin: false,
    isAdmin: true,
    loading: false,
    permissions: {},
    userRole: 'admin',
});

export const PermissionProvider = ({ children }) => {
    const permissions = {
        can: () => true, // All permissions allowed
        hasPermission: () => true,
        canCreate: true,
        canEdit: true,
        canDelete: true,
        canView: true,
        isSuperAdmin: false, // No super admin in lite version
        isAdmin: true, // Everyone is admin in lite version
        loading: false,
        permissions: {},
        userRole: 'admin',
    };

    return (
        <PermissionContext.Provider value={permissions}>
            {children}
        </PermissionContext.Provider>
    );
};

export const usePermissions = () => {
    const context = useContext(PermissionContext);
    if (!context) {
        throw new Error('usePermissions must be used within PermissionProvider');
    }
    return context;
};

export default PermissionContext;
