/**
 * Sensor Template Service
 * Backend sensor template API integration
 */

import axiosInstance from './axios';

export class SensorTemplateService {
  constructor() {
    this.baseURL = '/v2/sensor-templates';
  }
  
  /**
   * Get all available sensor templates
   */
  static async getSensorTemplates() {
    try {
      const service = new SensorTemplateService();
      const response = await axiosInstance.get(`${service.baseURL}/templates`);
      return response.data;
    } catch (error) {
      console.error('Error fetching sensor templates:', error);
      throw error;
    }
  }
  
  /**
   * Get specific sensor template by type
   */
  static async getSensorTemplate(sensorType) {
    try {
      const service = new SensorTemplateService();
      const response = await axiosInstance.get(`${service.baseURL}/templates/${sensorType}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching sensor template ${sensorType}:`, error);
      throw error;
    }
  }
  
  /**
   * Generate default sensors for a kozalak
   */
  static async generateDefaultSensors(kozalakId, kozalakType = 'merkez') {
    try {
      const service = new SensorTemplateService();
      const response = await axiosInstance.post(
        `${service.baseURL}/generate-default-sensors/${kozalakId}?kozalak_type=${kozalakType}`
      );
      return response.data;
    } catch (error) {
      console.error(`Error generating default sensors for ${kozalakId}:`, error);
      throw error;
    }
  }
  
  /**
   * Validate sensor data against template
   */
  static async validateSensorData(instanceId, templateRef, data) {
    try {
      const service = new SensorTemplateService();
      const response = await axiosInstance.post(`${service.baseURL}/validate-sensor-data`, {
        instance_id: instanceId,
        template_ref: templateRef,
        data: data
      });
      return response.data;
    } catch (error) {
      console.error('Error validating sensor data:', error);
      throw error;
    }
  }
  
  /**
   * Get template options for UI dropdowns
   */
  static async getTemplateOptions() {
    try {
      const templatesData = await this.getSensorTemplates();
      
      // Null/undefined safety check
      if (!templatesData || !templatesData.templates) {
        console.warn('No templates data received from backend');
        return [];
      }
      
      const templates = templatesData.templates;
      
      return Object.entries(templates).map(([key, template]) => ({
        value: key,
        label: template.title,
        description: template.description,
        manufacturer: template.manufacturer,
        model: template.model,
        template_id: template.template_id,
        properties: template.properties,
        validation_rules: template.validation_rules
      }));
    } catch (error) {
      console.error('Error getting template options:', error);
      return [];
    }
  }
  
  /**
   * Create sensor instance configuration
   */
  static createSensorInstance(kozalakId, template, customName = null, metadata = {}) {
    const instanceName = customName || template.title;
    const instanceId = `${kozalakId}-${template.value}`;
    
    return {
      "@id": instanceId,
      "@type": ["sosa:Sensor"],
      "name": instanceName,
      "observes": `#${template.value}Property`,
      "sosa:implementedBy": template.template_id,
      "instance_metadata": {
        ...metadata,
        created_at: new Date().toISOString(),
        auto_generated: false
      }
    };
  }
  
  /**
   * Format sensor data for display
   */
  static formatSensorForDisplay(sensor) {
    return {
      id: sensor["@id"],
      name: sensor.name,
      type: sensor["@type"],
      template: sensor["sosa:implementedBy"] || sensor.template_ref,
      observes: sensor.observes,
      metadata: sensor.instance_metadata || {},
      displayName: sensor.name,
      isTemplate: !!sensor["sosa:implementedBy"]
    };
  }
  
  /**
   * Get validation info for sensor value
   */
  static getValidationInfo(templateRef, templates) {
    if (!templates || !templateRef) return null;
    
    // Find template by template_id
    for (const [key, template] of Object.entries(templates)) {
      if (template.template_id === templateRef) {
        return {
          sensor_type: key,
          template: template,
          properties: template.properties,
          validation_rules: template.validation_rules
        };
      }
    }
    
    return null;
  }
}

export default SensorTemplateService;