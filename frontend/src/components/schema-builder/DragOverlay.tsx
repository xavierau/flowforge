import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Property } from '@/store/schemaStore';

const TYPE_COLORS: Record<string, string> = {
  string: 'bg-slate-100 text-slate-700 border-slate-300',
  number: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  boolean: 'bg-violet-50 text-violet-700 border-violet-200',
  object: 'bg-amber-50 text-amber-700 border-amber-200',
  array: 'bg-sky-50 text-sky-700 border-sky-200',
};

interface DragOverlayContentProps {
  property: Property;
}

export function DragOverlayContent({ property }: DragOverlayContentProps) {
  const childCount = property.children?.length ?? 0;
  const hasChildren = childCount > 0;

  return (
    <div
      className={cn(
        'flex items-center gap-3 px-4 py-3',
        'bg-white rounded-lg border-2 border-primary shadow-lg',
        'min-w-[200px] max-w-[300px]',
        'cursor-grabbing'
      )}
    >
      {/* Property name */}
      <span className="font-medium text-slate-900 truncate flex-1">
        {property.name}
      </span>

      {/* Type badge */}
      <Badge
        variant="outline"
        className={cn('text-xs font-medium border shrink-0', TYPE_COLORS[property.type])}
      >
        {property.type}
      </Badge>

      {/* Child count indicator */}
      {hasChildren && (
        <span className="text-xs text-slate-500 shrink-0">
          ({childCount} {childCount === 1 ? 'child' : 'children'})
        </span>
      )}
    </div>
  );
}
