import { create } from 'zustand';

/**
 * Placeholder Sidebar Store for TwinScale-Lite
 * Simplified version without complex sidebar state
 */
const useSidebarStore = create((set) => ({
    isOpen: true,
    isCollapsed: false,

    toggleSidebar: () => set((state) => ({ isOpen: !state.isOpen })),
    toggleCollapse: () => set((state) => ({ isCollapsed: !state.isCollapsed })),
    setSidebarOpen: (isOpen) => set({ isOpen }),
    setSidebarCollapsed: (isCollapsed) => set({ isCollapsed }),
}));

export default useSidebarStore;
