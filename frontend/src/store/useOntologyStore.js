/**
 * Ontology Store
 *
 * Holds the relationship type vocabulary fetched from the backend ontology.
 * Every screen that renders a relationship type — the create form, the graph
 * view, the detail page — reads it from here, so a type looks and behaves the
 * same everywhere and a new type needs no frontend change.
 *
 * If the backend is unreachable the store falls back to the vocabulary as it
 * stood when this file was written, so the UI keeps working.
 */

import { create } from "zustand";
import OntologyService from "../services/ontologyService";

// Last-resort copy, used only when the ontology endpoint cannot be reached.
// Keep in step with RELATIONSHIP_TYPES in backend/app/core/twin_ontology.py.
const FALLBACK_TYPES = [
  { name: "feeds", inverse: "isFedBy", ui_color: "#f59e0b", is_derived: false, propagation_direction: "source-to-target" },
  { name: "controls", inverse: "isControlledBy", ui_color: "#ef4444", is_derived: false, propagation_direction: "target-to-source" },
  { name: "contains", inverse: "isContainedIn", ui_color: "#8b5cf6", is_derived: false, propagation_direction: "bidirectional" },
  { name: "monitors", inverse: "isMonitoredBy", ui_color: "#10b981", is_derived: false, propagation_direction: "source-to-target" },
  { name: "dependsOn", inverse: "isDependedOnBy", ui_color: "#6366f1", is_derived: false, propagation_direction: "target-to-source" },
  { name: "isFedBy", inverse: "feeds", ui_color: "#f59e0b", is_derived: true, propagation_direction: "source-to-target" },
  { name: "isControlledBy", inverse: "controls", ui_color: "#ef4444", is_derived: true, propagation_direction: "target-to-source" },
  { name: "isContainedIn", inverse: "contains", ui_color: "#8b5cf6", is_derived: true, propagation_direction: "bidirectional" },
  { name: "isMonitoredBy", inverse: "monitors", ui_color: "#10b981", is_derived: true, propagation_direction: "source-to-target" },
  { name: "isDependedOnBy", inverse: "dependsOn", ui_color: "#6366f1", is_derived: true, propagation_direction: "target-to-source" },
].map((t) => ({ ...t, label: t.name, description: "", uri: "", on_target_deleted: "Deactivate" }));

const NEUTRAL_COLOR = "#64748b";

const useOntologyStore = create((set, get) => ({
  relationshipTypes: [],
  version: null,
  isLoaded: false,
  isLoading: false,
  usingFallback: false,
  error: null,

  /**
   * Load the vocabulary once. Safe to call from every component that needs it —
   * concurrent calls share the in-flight request.
   */
  loadRelationshipTypes: async (force = false) => {
    const { isLoaded, isLoading } = get();
    if ((isLoaded && !force) || isLoading) return get().relationshipTypes;

    set({ isLoading: true, error: null });
    try {
      const data = await OntologyService.getRelationshipTypes(true);
      set({
        relationshipTypes: data.types || [],
        version: data.version || null,
        isLoaded: true,
        isLoading: false,
        usingFallback: false,
      });
    } catch (error) {
      console.error("Ontology unavailable, using fallback vocabulary:", error);
      set({
        relationshipTypes: FALLBACK_TYPES,
        isLoaded: true,
        isLoading: false,
        usingFallback: true,
        error: error.message,
      });
    }
    return get().relationshipTypes;
  },

  /** Types a user can assert — inverse types are generated, not chosen. */
  getSelectableTypes: () => get().relationshipTypes.filter((t) => !t.is_derived),

  /** Look up one type by name. */
  getType: (name) => get().relationshipTypes.find((t) => t.name === name) || null,

  /** Colour for a type; a neutral grey for anything unknown. */
  getTypeColor: (name) => get().getType(name)?.ui_color || NEUTRAL_COLOR,

  /** True when the name is an inverse (derived) type. */
  isDerivedType: (name) => Boolean(get().getType(name)?.is_derived),

  /** Inline styles for a badge rendering this type, light and dark safe. */
  getTypeBadgeStyle: (name) => {
    const color = get().getTypeColor(name);
    return {
      color,
      backgroundColor: `${color}1f`, // ~12% alpha, readable on both themes
      borderColor: `${color}59`,
    };
  },
}));

export { FALLBACK_TYPES, NEUTRAL_COLOR };
export default useOntologyStore;
