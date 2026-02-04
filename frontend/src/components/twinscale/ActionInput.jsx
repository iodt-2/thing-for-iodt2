// components/ActionInput.jsx
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

const ActionInput = ({ action, onChange, onRemove, isExpanded, onToggleExpand }) => {
  // Internal expanded state if not controlled from parent
  const [internalExpanded, setInternalExpanded] = useState(false);

  const expanded = isExpanded !== undefined ? isExpanded : internalExpanded;
  const toggleExpand = onToggleExpand || (() => setInternalExpanded(!internalExpanded));

  const [fields, setFields] = useState(
    action.simpleInput.fields || []
  );

  const handleAddField = () => {
    const newField = {
      name: '',
      schema: { type: 'string' }
    };
    setFields([...fields, newField]);

    const updatedAction = {
      ...action,
      simpleInput: {
        type: 'object',
        fields: [...fields, newField]
      }
    };
    onChange(updatedAction);
  };

  const handleFieldChange = (index, field, value) => {
    const newFields = [...fields];
    if (field === 'schema') {
      if (value === 'range') {
        newFields[index].schema = 'range';
      } else {
        newFields[index].schema = { type: value };
      }
    } else {
      newFields[index][field] = value;
    }

    const updatedAction = {
      ...action,
      simpleInput: {
        type: 'object',
        fields: newFields
      }
    };
    onChange(updatedAction);
  };

  const handleRemoveField = (index) => {
    const newFields = fields.filter((_, i) => i !== index);
    setFields(newFields);

    const updatedAction = {
      ...action,
      simpleInput: {
        type: 'object',
        fields: newFields
      }
    };
    onChange(updatedAction);
  };

  const fieldCount = action.simpleInput?.fields?.length || 0;

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
              {action.name || "New Action"}
            </span>
            <span className="text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 px-2 py-0.5 rounded">
              {action.mode}
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
          {/* Action Key ve Mode Seçimi */}
          <div className="flex gap-4">
            <div className="flex-1 space-y-2">
              <Label>Action Key</Label>
              <Input
                placeholder="Action Name (e.g., fade, toggle)"
                value={action.name}
                onChange={(e) => onChange({
                  ...action,
                  name: e.target.value
                })}
              />
            </div>
            <div className="space-y-2">
              <Label>Mode</Label>
              <Select
                value={action.mode}
                onValueChange={(value) => onChange({
                  ...action,
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

          {/* Input Schema - Simple veya Advanced */}
          {action.mode === 'simple' ? (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <Label>Input Fields</Label>
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
                          placeholder="Field name (e.g., from, to, duration)"
                          value={field.name}
                          onChange={(e) => handleFieldChange(index, 'name', e.target.value)}
                        />
                      </div>
                      <div className="w-[200px]">
                        <Label>Schema Type</Label>
                        <Select
                          value={field.schema.type || field.schema}
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
                            <SelectItem value="range">Range</SelectItem>
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

                    {field.schema === 'range' && (
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label>Minimum</Label>
                          <Input
                            type="number"
                            placeholder="Min value"
                            value={field.minimum || 0}
                            onChange={(e) => handleFieldChange(index, 'minimum', parseInt(e.target.value))}
                          />
                        </div>
                        <div>
                          <Label>Maximum</Label>
                          <Input
                            type="number"
                            placeholder="Max value"
                            value={field.maximum || 100}
                            onChange={(e) => handleFieldChange(index, 'maximum', parseInt(e.target.value))}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              <Label>Advanced Input Schema</Label>
              <div className="h-[300px] border rounded-md overflow-hidden">
                <Editor
                  height="100%"
                  defaultLanguage="json"
                  value={action.advancedInput}
                  onChange={(value) => onChange({
                    ...action,
                    advancedInput: value
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
                Define your input schema in JSON format
              </p>
            </div>
          )}

          {/* Forms Input */}
          <FormsInput
            forms={action.forms}
            onChange={(newForms) => onChange({
              ...action,
              forms: newForms
            })}
          />
        </CardContent>
      )}
    </Card>
  );
};

ActionInput.propTypes = {
  action: PropTypes.shape({
    name: PropTypes.string,
    mode: PropTypes.oneOf(['simple', 'advanced']),
    simpleInput: PropTypes.shape({
      type: PropTypes.string,
      fields: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string,
        schema: PropTypes.oneOfType([
          PropTypes.string,
          PropTypes.shape({
            type: PropTypes.string
          })
        ]),
        minimum: PropTypes.number,
        maximum: PropTypes.number
      }))
    }),
    advancedInput: PropTypes.string,
    forms: PropTypes.arrayOf(PropTypes.shape({
      href: PropTypes.string
    }))
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  isExpanded: PropTypes.bool,
  onToggleExpand: PropTypes.func
};

export default ActionInput;
