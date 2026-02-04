/**
 * Placeholder Ditto Service for TwinScale-Lite
 * No Ditto integration in lite version
 */

const dittoService = {
    // Placeholder methods that do nothing
    connect: async () => {
        console.warn('Ditto service not available in TwinScale-Lite');
        return false;
    },

    disconnect: () => {
        console.warn('Ditto service not available in TwinScale-Lite');
    },

    getThing: async () => {
        console.warn('Ditto service not available in TwinScale-Lite');
        return null;
    },

    createThing: async () => {
        console.warn('Ditto service not available in TwinScale-Lite');
        return null;
    },

    updateThing: async () => {
        console.warn('Ditto service not available in TwinScale-Lite');
        return null;
    },

    deleteThing: async () => {
        console.warn('Ditto service not available in TwinScale-Lite');
        return false;
    },
};

export default dittoService;
