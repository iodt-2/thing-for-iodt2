// components/FormsInput.jsx
import PropTypes from 'prop-types';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, Trash2 } from "lucide-react";

const FormsInput = ({ forms, onChange }) => {
  const handleFormChange = (index, field, value) => {
    const newForms = [...forms];
    newForms[index] = { ...newForms[index], [field]: value };
    onChange(newForms);
  };

  const addForm = () => {
    onChange([...forms, { href: '' }]);
  };

  const removeForm = (index) => {
    const newForms = forms.filter((_, i) => i !== index);
    onChange(newForms);
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <Label>Forms</Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={addForm}
        >
          <Plus className="w-4 h-4 mr-1" />
          Add Form
        </Button>
      </div>
      {forms.map((form, index) => (
        <div key={index} className="flex gap-2">
          <Input
            placeholder="Form href"
            value={form.href}
            onChange={(e) => handleFormChange(index, 'href', e.target.value)}
            className="flex-1"
          />
          <Button
            type="button"
            variant="destructive"
            size="icon"
            onClick={() => removeForm(index)}
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      ))}
    </div>
  );
};

FormsInput.propTypes = {
  forms: PropTypes.arrayOf(
    PropTypes.shape({
      href: PropTypes.string
    })
  ).isRequired,
  onChange: PropTypes.func.isRequired
};

export default FormsInput;