import { create } from 'zustand';

/**
 * Placeholder Ditto Store for TwinScale-Lite
 * No Ditto integration in lite version
 */
const useDittoStore = create((set) => ({
    isConnected: false,
    connectionStatus: 'disconnected',

    // Placeholder methods
    connect: async () => { },
    disconnect: () => { },
    checkConnection: async () => { },
}));

export default useDittoStore;
