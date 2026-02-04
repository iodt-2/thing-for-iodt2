import { create } from 'zustand';

/**
 * Placeholder Auth Store for TwinScale-Lite
 * No authentication in lite version - always returns null/false
 */
const useAuthStore = create((set) => ({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,

    // Placeholder methods - do nothing in lite version
    login: async () => { },
    logout: () => { },
    checkAuth: async () => { },
    setUser: (user) => set({ user }),
}));

export default useAuthStore;
