import { cn } from '@/lib/utils';

interface DropIndicatorProps {
  position: 'before' | 'after';
  level: number;
  isValid?: boolean;
}

export function DropIndicator({ position, level, isValid = true }: DropIndicatorProps) {
  const leftMargin = level * 24 + 8;

  return (
    <div
      className={cn(
        'h-0.5 rounded-full',
        'animate-pulse',
        position === 'before' ? 'mb-1' : 'mt-1',
        isValid ? 'bg-primary' : 'bg-destructive'
      )}
      style={{ marginLeft: `${leftMargin}px` }}
      role="presentation"
      aria-hidden="true"
    />
  );
}
