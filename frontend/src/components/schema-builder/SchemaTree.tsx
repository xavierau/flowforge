import { useState } from 'react';
import { Plus } from 'lucide-react';
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCenter,
} from '@dnd-kit/core';
import { Button } from '@/components/ui/button';
import { TreeNode } from './TreeNode';
import { PropertyEditor } from './PropertyEditor';
import { DragOverlayContent } from './DragOverlay';
import { useSchemaStore } from '@/store/schemaStore';
import { useSchemaDnd } from '@/hooks/useSchemaDnd';
import type { Property } from '@/store/schemaStore';

export function SchemaTree() {
  const { properties } = useSchemaStore();
  const [editingProperty, setEditingProperty] = useState<Property | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Initialize DnD hook
  const { dragState, handlers, getActiveProperty, isValidDrop } = useSchemaDnd();

  // Configure sensors with activation constraints
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement before drag starts
      },
    }),
    useSensor(KeyboardSensor)
  );

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

  // Get the active property for drag overlay
  const activeProperty = getActiveProperty();

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handlers.onDragStart}
        onDragOver={handlers.onDragOver}
        onDragEnd={handlers.onDragEnd}
        onDragCancel={handlers.onDragCancel}
      >
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
                {properties.map((property, index) => (
                  <TreeNode
                    key={property.id}
                    property={property}
                    index={index}
                    parentId={null}
                    onEdit={setEditingProperty}
                    dragState={dragState}
                    isValidDrop={isValidDrop}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Drag overlay - shows a preview of the dragged item */}
        <DragOverlay dropAnimation={null}>
          {activeProperty ? (
            <DragOverlayContent property={activeProperty} />
          ) : null}
        </DragOverlay>
      </DndContext>

      <PropertyEditor
        property={editingProperty}
        isOpen={editingProperty !== null}
        isCreating={isCreating}
        onClose={handleCloseEditor}
      />
    </>
  );
}
