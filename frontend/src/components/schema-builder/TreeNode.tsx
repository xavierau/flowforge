import { ChevronRight, ChevronDown, Plus, Trash2, Edit } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import type { Property } from '@/store/schemaStore';
import { useSchemaStore } from '@/store/schemaStore';
import { cn } from '@/lib/utils';
import { SCHEMA_CONFIG } from '@/config';

interface TreeNodeProps {
  property: Property;
  onEdit: (property: Property) => void;
}

const TYPE_COLORS: Record<string, string> = {
  string: 'bg-slate-100 text-slate-700 border-slate-300',
  number: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  boolean: 'bg-violet-50 text-violet-700 border-violet-200',
  object: 'bg-amber-50 text-amber-700 border-amber-200',
  array: 'bg-sky-50 text-sky-700 border-sky-200',
};

const BORDER_COLORS: Record<number, string> = {
  0: 'border-l-slate-400',
  1: 'border-l-slate-300',
  2: 'border-l-slate-200',
  3: 'border-l-slate-100',
};

export function TreeNode({ property, onEdit }: TreeNodeProps) {
  const { expandedNodeIds, toggleNode, deleteProperty, addProperty } = useSchemaStore();
  const isExpanded = expandedNodeIds.has(property.id);
  const hasChildren = property.children && property.children.length > 0;
  const canAddChildren = property.type === 'object' || property.type === 'array';
  const canNest = property.level < SCHEMA_CONFIG.MAX_NESTING_LEVEL;

  const handleAddChild = () => {
    if (!canNest) {
      alert(`Maximum nesting depth (${SCHEMA_CONFIG.MAX_NESTING_LEVEL} levels) reached`);
      return;
    }

    // For arrays, we add items schema; for objects, we add properties
    const childType = property.type === 'array' ? 'string' : 'string';
    const childName = property.type === 'array' ? 'items' : 'new_property';

    addProperty(
      {
        name: childName,
        type: childType,
        required: false,
        constraints: {},
        children: undefined,
      },
      property.id
    );
  };

  const handleDelete = () => {
    if (confirm(`Delete property "${property.name}"?`)) {
      deleteProperty(property.id);
    }
  };

  const indentLevel = property.level * 24; // 24px per level

  return (
    <div>
      <div
        className={cn(
          'group flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-slate-50 transition-all duration-200',
          'border-l-2',
          BORDER_COLORS[property.level as keyof typeof BORDER_COLORS] || 'border-l-slate-100'
        )}
        style={{ marginLeft: `${indentLevel}px` }}
      >
        {/* Expand/Collapse Button */}
        {canAddChildren && (
          <button
            onClick={() => toggleNode(property.id)}
            className="p-1 hover:bg-slate-200 rounded-md transition-colors text-slate-600"
            aria-label={isExpanded ? 'Collapse' : 'Expand'}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        )}

        {!canAddChildren && <div className="w-6" />}

        {/* Property Info */}
        <div className="flex-1 flex items-center gap-2 min-w-0">
          <span className="font-medium text-slate-900 truncate">{property.name}</span>
          <Badge
            variant="outline"
            className={cn('text-xs font-medium border', TYPE_COLORS[property.type])}
          >
            {property.type}
          </Badge>
          {property.required && (
            <Badge variant="outline" className="text-xs font-medium border bg-red-50 text-red-700 border-red-200">
              Required
            </Badge>
          )}
          {property.description && (
            <span className="text-xs text-slate-500 truncate italic">
              {property.description}
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          {canAddChildren && canNest && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleAddChild}
              className="h-7 w-7 p-0 hover:bg-slate-200 text-slate-600"
              title="Add child property"
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(property)}
            className="h-7 w-7 p-0 hover:bg-slate-200 text-slate-600"
            title="Edit property"
          >
            <Edit className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDelete}
            className="h-7 w-7 p-0 hover:bg-red-100 text-slate-600 hover:text-red-600"
            title="Delete property"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Recursive Children */}
      {canAddChildren && isExpanded && hasChildren && (
        <div className="mt-0.5">
          {property.children!.map((child) => (
            <TreeNode key={child.id} property={child} onEdit={onEdit} />
          ))}
        </div>
      )}
    </div>
  );
}
