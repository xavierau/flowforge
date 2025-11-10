import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { TreeNode } from './TreeNode';
import { PropertyEditor } from './PropertyEditor';
import { useSchemaStore } from '@/store/schemaStore';
import type { Property } from '@/store/schemaStore';

export function SchemaTree() {
  const { properties } = useSchemaStore();
  const [editingProperty, setEditingProperty] = useState<Property | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const handleAddRootProperty = () => {
    setIsCreating(true);
    setEditingProperty({
      id: 'new',
      name: 'new_property',
      type: 'string',
      required: false,
      level: 0,
      constraints: {},
    } as Property);
  };

  const handleCloseEditor = () => {
    setEditingProperty(null);
    setIsCreating(false);
  };

  return (
    <>
      <div className="flex flex-col">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="font-semibold">Properties</h3>
            <p className="text-sm text-muted-foreground">
              {properties.length} {properties.length === 1 ? 'property' : 'properties'}
            </p>
          </div>
          <Button onClick={handleAddRootProperty} size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Add Property
          </Button>
        </div>

        <div>
          {properties.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <p className="mb-2">No properties yet</p>
              <p className="text-sm">Click "Add Property" to get started</p>
            </div>
          ) : (
            <div className="space-y-1">
              {properties.map((property) => (
                <TreeNode
                  key={property.id}
                  property={property}
                  onEdit={setEditingProperty}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <PropertyEditor
        property={editingProperty}
        isOpen={editingProperty !== null}
        isCreating={isCreating}
        onClose={handleCloseEditor}
      />
    </>
  );
}
