import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, Trash2 } from "lucide-react";
import PropTypes from 'prop-types';

const LinksInput = ({ links, onChange }) => {
    const handleAddLink = () => {
      onChange([...links, {
        href: '',
        rel: '',
        mediaType: ''
      }]);
    };
  
    const handleLinkChange = (index, field, value) => {
      const newLinks = [...links];
      newLinks[index] = { ...newLinks[index], [field]: value };
      onChange(newLinks);
    };
  
    const handleRemoveLink = (index) => {
      const newLinks = links.filter((_, i) => i !== index);
      onChange(newLinks);
    };
  
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <Label>Links</Label>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleAddLink}
          >
            <Plus className="w-4 h-4 mr-1" />
            Add Link
          </Button>
        </div>
  
        {links.map((link, index) => (
          <Card key={index} className="p-3">
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label>Href</Label>
                  <Input
                    placeholder="Link href"
                    value={link.href}
                    onChange={(e) => handleLinkChange(index, 'href', e.target.value)}
                  />
                </div>
                <div>
                  <Label>Relation</Label>
                  <Input
                    placeholder="Relation (e.g., controlledBy)"
                    value={link.rel}
                    onChange={(e) => handleLinkChange(index, 'rel', e.target.value)}
                  />
                </div>
                <div>
                  <Label>Media Type</Label>
                  <Input
                    placeholder="Media Type (e.g., application/td)"
                    value={link.mediaType}
                    onChange={(e) => handleLinkChange(index, 'mediaType', e.target.value)}
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <Button
                  variant="destructive"
                  size="icon"
                  onClick={() => handleRemoveLink(index)}
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  };
  
  LinksInput.propTypes = {
    links: PropTypes.arrayOf(PropTypes.shape({
      href: PropTypes.string,
      rel: PropTypes.string,
      mediaType: PropTypes.string
    })).isRequired,
    onChange: PropTypes.func.isRequired
  };

export default LinksInput;