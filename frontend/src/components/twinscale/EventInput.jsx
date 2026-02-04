// components/EventInput.jsx
import { useState } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import Editor from '@monaco-editor/react';
import { Plus, Trash2, ChevronDown, ChevronRight, Edit2 } from "lucide-react";
import FormsInput from './FormsInput';
import PropTypes from 'prop-types';

const EventInput = ({ event, onChange, onRemove, isExpanded, onToggleExpand }) => {
  // Internal expanded state if not controlled from parent
  const [internalExpanded, setInternalExpanded] = useState(false);

  const expanded = isExpanded !== undefined ? isExpanded : internalExpanded;
  const toggleExpand = onToggleExpand || (() => setInternalExpanded(!internalExpanded));

  const [fields, setFields] = useState(
    event.simpleSchema.fields || []
  );

  const handleAddField = () => {
    const newField = {
      name: '',
      schema: { type: 'string' }
    };
    setFields([...fields, newField]);

    const updatedEvent = {
      ...event,
      simpleSchema: {
        type: 'object',
        fields: [...fields, newField]
      }
    };
    onChange(updatedEvent);
  };

  const handleFieldChange = (index, field, value) => {
    const newFields = [...fields];
    if (field === 'schema') {
      newFields[index].schema = { type: value };
    } else {
      newFields[index][field] = value;
    }

    const updatedEvent = {
      ...event,
      simpleSchema: {
        type: 'object',
        fields: newFields
      }
    };
    onChange(updatedEvent);
  };

  const handleRemoveField = (index) => {
    const newFields = fields.filter((_, i) => i !== index);
    setFields(newFields);

    const updatedEvent = {
      ...event,
      simpleSchema: {
        type: 'object',
        fields: newFields
      }
    };
    onChange(updatedEvent);
  };

  const fieldCount = event.simpleSchema?.fields?.length || 0;

  return (
    <Card className="mb-2 overflow-hidden">
      {/* Collapsed Header - Always visible */}
      <div
        className={`flex items-center justify-between p-3 cursor-pointer hover:bg-muted/50 transition-colors ${expanded ? 'bg-muted/30 border-b' : ''}`}
        onClick={toggleExpand}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
          )}
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="font-medium text-sm truncate">
              {event.name || "New Event"}
            </span>
            <span className="text-xs bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300 px-2 py-0.5 rounded">
              {event.mode}
            </span>
            {fieldCount > 0 && (
              <span className="text-xs text-muted-foreground">
                {fieldCount} field{fieldCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={toggleExpand}
            className="h-8 w-8 p-0"
          >
            <Edit2 className="w-4 h-4" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 text-destructive hover:text-destructive"
            onClick={onRemove}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <CardContent className="p-4 space-y-4">
          {/* Event Key ve Mode Seçimi */}
          <div className="flex gap-4">
            <div className="flex-1 space-y-2">
              <Label>Event Key</Label>
              <Input
                placeholder="Event Name (e.g., overheated, statusChanged)"
                value={event.name}
                onChange={(e) => onChange({
                  ...event,
                  name: e.target.value
                })}
              />
            </div>
            <div className="space-y-2">
              <Label>Mode</Label>
              <Select
                value={event.mode}
                onValueChange={(value) => onChange({
                  ...event,
                  mode: value
                })}
              >
                <SelectTrigger className="w-[120px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="simple">Simple</SelectItem>
                  <SelectItem value="advanced">Advanced</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Schema Definition - Simple veya Advanced */}
          {event.mode === 'simple' ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <Label>Event Data Fields</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddField}
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add Field
                </Button>
              </div>

              {fields.map((field, index) => (
                <Card key={index} className="p-3">
                  <div className="space-y-3">
                    <div className="flex gap-3">
                      <div className="flex-1">
                        <Label>Field Name</Label>
                        <Input
                          placeholder="Field name (e.g., temperature, status)"
                          value={field.name}
                          onChange={(e) => handleFieldChange(index, 'name', e.target.value)}
                        />
                      </div>
                      <div className="w-[200px]">
                        <Label>Schema Type</Label>
                        <Select
                          value={field.schema.type}
                          onValueChange={(value) => handleFieldChange(index, 'schema', value)}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Type" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="string">String</SelectItem>
                            <SelectItem value="number">Number</SelectItem>
                            <SelectItem value="boolean">Boolean</SelectItem>
                            <SelectItem value="integer">Integer</SelectItem>
                            <SelectItem value="object">Object</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="flex items-end">
                        <Button
                          variant="destructive"
                          size="icon"
                          onClick={() => handleRemoveField(index)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              <Label>Advanced Schema Definition</Label>
              <div className="h-[300px] border rounded-md overflow-hidden">
                <Editor
                  height="100%"
                  defaultLanguage="json"
                  value={event.advancedSchema}
                  onChange={(value) => onChange({
                    ...event,
                    advancedSchema: value
                  })}
                  options={{
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    theme: 'vs-dark',
                    formatOnPaste: true,
                    formatOnType: true
                  }}
                />
              </div>
              <p className="text-sm text-muted-foreground">
                Define your event data schema in JSON format
              </p>
            </div>
          )}

          {/* Forms Input */}
          <FormsInput
            forms={event.forms}
            onChange={(newForms) => onChange({
              ...event,
              forms: newForms
            })}
          />
        </CardContent>
      )}
    </Card>
  );
};

EventInput.propTypes = {
  event: PropTypes.shape({
    name: PropTypes.string,
    mode: PropTypes.oneOf(['simple', 'advanced']),
    simpleSchema: PropTypes.shape({
      type: PropTypes.string,
      fields: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string,
        schema: PropTypes.shape({
          type: PropTypes.string
        })
      }))
    }),
    advancedSchema: PropTypes.string,
    forms: PropTypes.arrayOf(PropTypes.shape({
      href: PropTypes.string
    }))
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  isExpanded: PropTypes.bool,
  onToggleExpand: PropTypes.func
};

export default EventInput;
