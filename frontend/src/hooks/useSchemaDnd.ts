import { useState, useCallback, useMemo } from 'react';
import type {
  DragStartEvent,
  DragEndEvent,
  DragOverEvent,
  DragCancelEvent,
  UniqueIdentifier,
} from '@dnd-kit/core';
import { useSchemaStore, findPropertyById, type Property } from '@/store/schemaStore';
import {
  canMoveProperty,
  getDropPosition,
  findPropertyIndex,
  type DropPosition,
  type ValidationResult,
} from '@/lib/dnd-utils';

/**
 * Data attached to draggable and droppable elements
 */
export interface DndData {
  property: Property;
  index: number;
  parentId: string | null;
}

/**
 * Current drag state
 */
export interface DragState {
  activeId: UniqueIdentifier | null;
  overId: UniqueIdentifier | null;
  overParentId: string | null;
  dropPosition: DropPosition;
}

/**
 * Drag and drop handlers
 */
export interface DndHandlers {
  onDragStart: (event: DragStartEvent) => void;
  onDragOver: (event: DragOverEvent) => void;
  onDragEnd: (event: DragEndEvent) => void;
  onDragCancel: (event: DragCancelEvent) => void;
}

/**
 * Return type for useSchemaDnd hook
 */
export interface UseSchemaDndResult {
  dragState: DragState;
  handlers: DndHandlers;
  getActiveProperty: () => Property | null;
  isDragging: boolean;
  isValidDrop: boolean;
}

const initialDragState: DragState = {
  activeId: null,
  overId: null,
  overParentId: null,
  dropPosition: null,
};

/**
 * Custom hook for managing drag-and-drop state in the schema builder
 *
 * Encapsulates all DnD logic including:
 * - Tracking active drag item
 * - Calculating drop positions
 * - Validating moves
 * - Executing property moves
 */
export function useSchemaDnd(): UseSchemaDndResult {
  const [dragState, setDragState] = useState<DragState>(initialDragState);

  const { properties, moveProperty } = useSchemaStore((state) => ({
    properties: state.properties,
    moveProperty: state.moveProperty,
  }));

  /**
   * Reset drag state to initial values
   */
  const resetDragState = useCallback(() => {
    setDragState(initialDragState);
  }, []);

  /**
   * Get the property currently being dragged
   */
  const getActiveProperty = useCallback((): Property | null => {
    if (!dragState.activeId) {
      return null;
    }
    return findPropertyById(properties, String(dragState.activeId));
  }, [dragState.activeId, properties]);

  /**
   * Handle drag start event
   */
  const onDragStart = useCallback((event: DragStartEvent) => {
    setDragState({
      activeId: event.active.id,
      overId: null,
      overParentId: null,
      dropPosition: null,
    });
  }, []);

  /**
   * Handle drag over event
   */
  const onDragOver = useCallback((event: DragOverEvent) => {
    const { over } = event;

    if (!over) {
      setDragState((prev) => ({
        ...prev,
        overId: null,
        overParentId: null,
        dropPosition: null,
      }));
      return;
    }

    // Get data from the over element
    const overData = over.data.current as DndData | undefined;
    const overProperty = overData?.property;
    const overParentId = overData?.parentId ?? null;

    // Calculate drop position based on cursor position
    let dropPosition: DropPosition = null;

    if (over.rect && event.activatorEvent) {
      // Get cursor Y position from the event
      let clientY = 0;
      const activatorEvent = event.activatorEvent;

      if ('clientY' in activatorEvent && typeof activatorEvent.clientY === 'number') {
        // MouseEvent
        clientY = activatorEvent.clientY;
      } else if (
        'touches' in activatorEvent &&
        (activatorEvent as TouchEvent).touches?.length > 0
      ) {
        // TouchEvent
        clientY = (activatorEvent as TouchEvent).touches[0].clientY;
      }

      // Determine if the over element can have children
      const canHaveChildren =
        overProperty &&
        (overProperty.type === 'object' || overProperty.type === 'array');

      dropPosition = getDropPosition(
        clientY,
        over.rect.top,
        over.rect.height,
        !!canHaveChildren
      );
    }

    setDragState((prev) => ({
      ...prev,
      overId: over.id,
      overParentId,
      dropPosition,
    }));
  }, []);

  /**
   * Handle drag end event - execute the move
   */
  const onDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;

      // Reset state if no valid drop target
      if (!over) {
        resetDragState();
        return;
      }

      const activeId = String(active.id);
      const overId = String(over.id);

      // Get data from the over element
      const overData = over.data.current as DndData | undefined;
      const overParentId = overData?.parentId ?? null;

      // Get the current drop position
      const dropPosition: DropPosition = dragState.dropPosition;

      // Determine destination parent based on drop position
      let destinationParentId: string | null;

      if (dropPosition === 'inside') {
        // Dropping inside the over element
        destinationParentId = overId;
      } else {
        // Dropping before/after the over element
        destinationParentId = overParentId;
      }

      // Check if move is valid
      const validationResult: ValidationResult = canMoveProperty(
        activeId,
        destinationParentId,
        properties
      );

      if (!validationResult.valid) {
        resetDragState();
        return;
      }

      // Calculate destination index
      let destinationIndex: number;

      if (dropPosition === 'inside') {
        // Insert at the end of the parent's children
        const targetProperty = findPropertyById(properties, overId);
        destinationIndex = targetProperty?.children?.length ?? 0;
      } else {
        // Find siblings to calculate index
        const siblings = destinationParentId
          ? findPropertyById(properties, destinationParentId)?.children ?? []
          : properties;

        const overIndex = findPropertyIndex(siblings, overId);

        if (overIndex === -1) {
          // Fallback: append at end
          destinationIndex = siblings.length;
        } else {
          destinationIndex = dropPosition === 'before' ? overIndex : overIndex + 1;
        }
      }

      // Execute the move
      if (moveProperty) {
        moveProperty(activeId, destinationParentId, destinationIndex);
      }

      // Reset drag state
      resetDragState();
    },
    [properties, dragState.dropPosition, moveProperty, resetDragState]
  );

  /**
   * Handle drag cancel event
   */
  const onDragCancel = useCallback(
    (_event: DragCancelEvent) => {
      resetDragState();
    },
    [resetDragState]
  );

  /**
   * Check if current drag state represents a valid drop
   */
  const isValidDrop = useMemo((): boolean => {
    if (!dragState.activeId || !dragState.overId || !dragState.dropPosition) {
      return false;
    }

    const activeId = String(dragState.activeId);
    let destinationParentId: string | null;

    if (dragState.dropPosition === 'inside') {
      destinationParentId = String(dragState.overId);
    } else {
      destinationParentId = dragState.overParentId;
    }

    const validationResult = canMoveProperty(activeId, destinationParentId, properties);
    return validationResult.valid;
  }, [
    dragState.activeId,
    dragState.overId,
    dragState.overParentId,
    dragState.dropPosition,
    properties,
  ]);

  /**
   * Whether a drag operation is currently in progress
   */
  const isDragging = dragState.activeId !== null;

  return {
    dragState,
    handlers: {
      onDragStart,
      onDragOver,
      onDragEnd,
      onDragCancel,
    },
    getActiveProperty,
    isDragging,
    isValidDrop,
  };
}

export default useSchemaDnd;
