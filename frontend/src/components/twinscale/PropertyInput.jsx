// components/PropertyInput.jsx
import { useState } from 'react';
import PropTypes from 'prop-types';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Trash2, ChevronDown, ChevronRight, Edit2 } from "lucide-react";
import FormsInput from './FormsInput';

const PropertyInput = ({ property, onChange, onRemove, isExpanded, onToggleExpand }) => {
  // Internal expanded state if not controlled from parent
  const [internalExpanded, setInternalExpanded] = useState(false);

  const expanded = isExpanded !== undefined ? isExpanded : internalExpanded;
  const toggleExpand = onToggleExpand || (() => setInternalExpanded(!internalExpanded));

  const schemaType = property.schema?.type || (typeof property.schema === 'string' ? property.schema : 'string');

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
              {property.name || "New Property"}
            </span>
            <span className="text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 px-2 py-0.5 rounded">
              {schemaType}
            </span>
            {property.writable && (
              <span className="text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-2 py-0.5 rounded">
                writable
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
          {/* Property Key ve Schema Type row */}
          <div className="flex gap-4">
            <div className="flex-1 space-y-2">
              <Label>Property Key</Label>
              <Input
                placeholder="Property Key (e.g., brightness, status)"
                value={property.name}
                onChange={(e) => onChange({
                  ...property,
                  name: e.target.value
                })}
              />
            </div>
            <div className="space-y-2">
              <Label>Schema Type</Label>
              <Select
                value={property.schema?.type || (typeof property.schema === 'string' ? property.schema : '')}
                onValueChange={(value) => {
                  if (value === "range") {
                    onChange({
                      ...property,
                      schema: "range",
                      minimum: 0,
                      maximum: 100
                    });
                  } else {
                    onChange({
                      ...property,
                      schema: { type: value }
                    });
                  }
                }}
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="boolean">Boolean</SelectItem>
                  <SelectItem value="integer">Integer</SelectItem>
                  <SelectItem value="number">Number</SelectItem>
                  <SelectItem value="string">String</SelectItem>
                  <SelectItem value="object">Object</SelectItem>
                  <SelectItem value="range">Range</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Range Type için ek alanlar */}
          {property.schema === "range" && (
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Minimum Value</Label>
                <Input
                  type="number"
                  placeholder="Min value"
                  value={property.minimum}
                  onChange={(e) => onChange({
                    ...property,
                    minimum: parseInt(e.target.value)
                  })}
                />
              </div>
              <div className="space-y-2">
                <Label>Maximum Value</Label>
                <Input
                  type="number"
                  placeholder="Max value"
                  value={property.maximum}
                  onChange={(e) => onChange({
                    ...property,
                    maximum: parseInt(e.target.value)
                  })}
                />
              </div>
            </div>
          )}

          {/* Writable Checkbox */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id={`writable-${property.name}`}
              checked={property.writable}
              onCheckedChange={(checked) => onChange({
                ...property,
                writable: checked
              })}
            />
            <Label htmlFor={`writable-${property.name}`}>Writable</Label>
          </div>

          {/* Forms Input */}
          <FormsInput
            forms={property.forms}
            onChange={(newForms) => onChange({
              ...property,
              forms: newForms
            })}
          />
        </CardContent>
      )}
    </Card>
  );
};

PropertyInput.propTypes = {
  property: PropTypes.shape({
    name: PropTypes.string,
    writable: PropTypes.bool,
    schema: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.shape({
        type: PropTypes.string
      })
    ]),
    minimum: PropTypes.number,
    maximum: PropTypes.number,
    forms: PropTypes.arrayOf(PropTypes.shape({
      href: PropTypes.string
    }))
  }).isRequired,
  onChange: PropTypes.func.isRequired,
  onRemove: PropTypes.func.isRequired,
  isExpanded: PropTypes.bool,
  onToggleExpand: PropTypes.func
};

export default PropertyInput;
