/**
 * useWorkflowWebSocket - Custom hook for workflow execution WebSocket connection
 * Manages connection lifecycle, message handling, and cleanup
 */

import { useEffect, useState, useCallback } from 'react';
import { workflowWebSocket } from '@/services/websocket.service';
import { getExecutionWebSocketUrl } from '@/services/workflow.service';
import type { WorkflowExecutionUpdate } from '@/types/workflow';

interface UseWorkflowWebSocketReturn {
  connected: boolean;
  error: string | null;
  lastMessage: WorkflowExecutionUpdate | null;
}

/**
 * Hook to connect to workflow execution WebSocket and receive real-time updates
 *
 * @param executionId - The execution ID to monitor (null to disconnect)
 * @param onMessage - Optional callback for handling messages
 * @returns Connection state and last received message
 */
export function useWorkflowWebSocket(
  executionId: string | null,
  onMessage?: (update: WorkflowExecutionUpdate) => void
): UseWorkflowWebSocketReturn {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WorkflowExecutionUpdate | null>(null);

  // Handle incoming messages
  const handleMessage = useCallback(
    (update: WorkflowExecutionUpdate) => {
      setLastMessage(update);

      // Call optional callback
      if (onMessage) {
        onMessage(update);
      }
    },
    [onMessage]
  );

  useEffect(() => {
    // No execution ID - don't connect
    if (!executionId) {
      setConnected(false);
      setError(null);
      setLastMessage(null);
      return;
    }

    // Get WebSocket URL
    const wsUrl = getExecutionWebSocketUrl(executionId);

    // Connect to WebSocket
    try {
      workflowWebSocket.connect({
        url: wsUrl,
        reconnectInterval: 3000,
        maxReconnectAttempts: 5,
      });

      setConnected(true);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect';
      setError(errorMessage);
      setConnected(false);
      console.error('[useWorkflowWebSocket] Connection error:', err);
    }

    // Subscribe to messages
    const unsubscribe = workflowWebSocket.on(handleMessage);

    // Monitor connection state
    const checkConnection = setInterval(() => {
      const isConnected = workflowWebSocket.isConnected;
      setConnected(isConnected);

      if (!isConnected && workflowWebSocket.readyState === WebSocket.CLOSED) {
        setError('WebSocket connection lost');
      } else if (isConnected) {
        setError(null);
      }
    }, 1000);

    // Cleanup on unmount or executionId change
    return () => {
      clearInterval(checkConnection);
      unsubscribe();
      workflowWebSocket.disconnect();
      setConnected(false);
      setError(null);
      setLastMessage(null);
    };
  }, [executionId, handleMessage]);

  return {
    connected,
    error,
    lastMessage,
  };
}
