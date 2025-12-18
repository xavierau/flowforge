import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { useSchemaStore } from '@/store/schemaStore';
import type { Property } from '@/store/schemaStore';

interface PropertyEditorProps {
  property: Property | null;
  isOpen: boolean;
  isCreating: boolean;
  onClose: () => void;
}

export function PropertyEditor({ property, isOpen, isCreating, onClose }: PropertyEditorProps) {
  const { addProperty, updateProperty } = useSchemaStore();

  const [formData, setFormData] = useState<Partial<Property>>({
    name: '',
    type: 'string',
    required: false,
    description: '',
    constraints: {},
  });

  useEffect(() => {
    if (property) {
      setFormData({
        name: property.name,
        type: property.type,
        required: property.required,
        description: property.description || '',
        constraints: { ...property.constraints },
      });
    }
  }, [property]);

  const handleSubmit = () => {
    if (!formData.name) {
      alert('Property name is required');
      return;
    }

    if (isCreating) {
      // Add new property at root level
      addProperty({
        name: formData.name,
        type: formData.type!,
        required: formData.required!,
        description: formData.description,
        constraints: formData.constraints!,
      });
    } else if (property) {
      // Update existing property
      updateProperty(property.id, {
        name: formData.name,
        type: formData.type,
        required: formData.required,
        description: formData.description,
        constraints: formData.constraints,
      });
    }

    onClose();
  };

  const handleConstraintChange = (key: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      constraints: {
        ...prev.constraints,
        [key]: value === '' ? undefined : value,
      },
    }));
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isCreating ? 'Add Property' : 'Edit Property'}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Basic Information */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Property Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., email, age, address"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="type">Type *</Label>
              <Select
                value={formData.type}
                onValueChange={(value) =>
                  setFormData({ ...formData, type: value as Property['type'] })
                }
              >
                <SelectTrigger id="type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="string">String</SelectItem>
                  <SelectItem value="number">Number</SelectItem>
                  <SelectItem value="boolean">Boolean</SelectItem>
                  <SelectItem value="object">Object</SelectItem>
                  <SelectItem value="array">Array</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Describe this property..."
                rows={2}
              />
            </div>

            <div className="flex items-center space-x-2">
              <Switch
                id="required"
                checked={formData.required}
                onCheckedChange={(checked) => setFormData({ ...formData, required: checked })}
              />
              <Label htmlFor="required">Required field</Label>
            </div>
          </div>

          <Separator />

          {/* Type-specific Constraints */}
          <div className="space-y-4">
            <h4 className="font-medium">Constraints</h4>

            {formData.type === 'string' && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="minLength">Min Length</Label>
                    <Input
                      id="minLength"
                      type="number"
                      value={formData.constraints?.minLength ?? ''}
                      onChange={(e) => handleConstraintChange('minLength', parseInt(e.target.value))}
                      min="0"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="maxLength">Max Length</Label>
                    <Input
                      id="maxLength"
                      type="number"
                      value={formData.constraints?.maxLength ?? ''}
                      onChange={(e) => handleConstraintChange('maxLength', parseInt(e.target.value))}
                      min="0"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="format">Format</Label>
                  <Select
                    value={formData.constraints?.format ?? 'none'}
                    onValueChange={(value) =>
                      handleConstraintChange('format', value === 'none' ? undefined : value)
                    }
                  >
                    <SelectTrigger id="format">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      <SelectItem value="email">Email</SelectItem>
                      <SelectItem value="uri">URI</SelectItem>
                      <SelectItem value="date">Date (YYYY-MM-DD)</SelectItem>
                      <SelectItem value="date-time">Date-Time</SelectItem>
                      <SelectItem value="uuid">UUID</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="pattern">Pattern (Regex)</Label>
                  <Input
                    id="pattern"
                    value={formData.constraints?.pattern ?? ''}
                    onChange={(e) => handleConstraintChange('pattern', e.target.value)}
                    placeholder="e.g., ^[A-Z]{3}$"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="enum">Enum Values</Label>
                  <Textarea
                    id="enum"
                    value={formData.constraints?.enum?.join('\n') ?? ''}
                    onChange={(e) => {
                      const value = e.target.value;
                      if (value.trim() === '') {
                        handleConstraintChange('enum', undefined);
                      } else {
                        const enumValues = value
                          .split('\n')
                          .map((v) => v.trim())
                          .filter((v) => v !== '');
                        handleConstraintChange('enum', enumValues.length > 0 ? enumValues : undefined);
                      }
                    }}
                    placeholder="Enter one value per line&#10;e.g.:&#10;pending&#10;approved&#10;rejected"
                    rows={4}
                  />
                  <p className="text-xs text-muted-foreground">
                    Leave empty for free-text string, or enter allowed values (one per line) to create an enum.
                  </p>
                </div>
              </>
            )}

            {formData.type === 'number' && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="minimum">Minimum</Label>
                  <Input
                    id="minimum"
                    type="number"
                    value={formData.constraints?.minimum ?? ''}
                    onChange={(e) => handleConstraintChange('minimum', parseFloat(e.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="maximum">Maximum</Label>
                  <Input
                    id="maximum"
                    type="number"
                    value={formData.constraints?.maximum ?? ''}
                    onChange={(e) => handleConstraintChange('maximum', parseFloat(e.target.value))}
                  />
                </div>
                <div className="space-y-2 col-span-2">
                  <Label htmlFor="multipleOf">Multiple Of</Label>
                  <Input
                    id="multipleOf"
                    type="number"
                    value={formData.constraints?.multipleOf ?? ''}
                    onChange={(e) =>
                      handleConstraintChange('multipleOf', parseFloat(e.target.value))
                    }
                    placeholder="e.g., 0.01 for cents"
                  />
                </div>
              </div>
            )}

            {formData.type === 'array' && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="minItems">Min Items</Label>
                  <Input
                    id="minItems"
                    type="number"
                    value={formData.constraints?.minItems ?? ''}
                    onChange={(e) => handleConstraintChange('minItems', parseInt(e.target.value))}
                    min="0"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="maxItems">Max Items</Label>
                  <Input
                    id="maxItems"
                    type="number"
                    value={formData.constraints?.maxItems ?? ''}
                    onChange={(e) => handleConstraintChange('maxItems', parseInt(e.target.value))}
                    min="0"
                  />
                </div>
                <div className="flex items-center space-x-2 col-span-2">
                  <Switch
                    id="uniqueItems"
                    checked={formData.constraints?.uniqueItems ?? false}
                    onCheckedChange={(checked) => handleConstraintChange('uniqueItems', checked)}
                  />
                  <Label htmlFor="uniqueItems">Unique items only</Label>
                </div>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="default">Default Value</Label>
              <Input
                id="default"
                value={formData.constraints?.default ?? ''}
                onChange={(e) => handleConstraintChange('default', e.target.value)}
                placeholder="Optional default value"
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>{isCreating ? 'Add' : 'Save'} Property</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
