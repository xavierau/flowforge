/**
 * WebSocket Service - Singleton manager for real-time workflow execution updates
 * Handles reconnection, message queuing, and event dispatching
 */

import type { WorkflowExecutionUpdate } from '@/types/workflow';

type EventCallback = (data: WorkflowExecutionUpdate) => void;

interface WebSocketConfig {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

/**
 * Singleton WebSocket manager with auto-reconnect
 */
class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string = '';
  private reconnectInterval: number = 3000;
  private maxReconnectAttempts: number = 5;
  private reconnectAttempts: number = 0;
  private reconnectTimeoutId: NodeJS.Timeout | null = null;
  private messageQueue: WorkflowExecutionUpdate[] = [];
  private callbacks: Set<EventCallback> = new Set();
  private isIntentionallyClosed: boolean = false;

  /**
   * Connect to WebSocket server
   */
  connect(config: WebSocketConfig): void {
    this.url = config.url;
    this.reconnectInterval = config.reconnectInterval || this.reconnectInterval;
    this.maxReconnectAttempts = config.maxReconnectAttempts || this.maxReconnectAttempts;
    this.isIntentionallyClosed = false;
    this.reconnectAttempts = 0;

    this.createConnection();
  }

  /**
   * Create WebSocket connection
   */
  private createConnection(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to', this.url);
        this.reconnectAttempts = 0;
        this.flushMessageQueue();
      };

      this.ws.onmessage = (event) => {
        try {
          const data: WorkflowExecutionUpdate = JSON.parse(event.data);
          this.emit(data);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };

      this.ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        this.ws = null;

        // Only attempt reconnection if not intentionally closed
        if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('[WebSocket] Connection failed:', error);
      this.scheduleReconnect();
    }
  }

  /**
   * Schedule reconnection attempt with exponential backoff
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
    }

    this.reconnectAttempts++;
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);

    console.log(
      `[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    this.reconnectTimeoutId = setTimeout(() => {
      this.createConnection();
    }, delay);
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;

    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.messageQueue = [];
    this.reconnectAttempts = 0;
  }

  /**
   * Send message to WebSocket server
   */
  send(data: unknown): void {
    const message = JSON.stringify(data);

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      console.warn('[WebSocket] Not connected, queueing message');
      // Queue message for sending when connected
      this.messageQueue.push(data as WorkflowExecutionUpdate);
    }
  }

  /**
   * Flush queued messages
   */
  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.send(message);
      }
    }
  }

  /**
   * Subscribe to WebSocket messages
   */
  on(callback: EventCallback): () => void {
    this.callbacks.add(callback);

    // Return unsubscribe function
    return () => {
      this.callbacks.delete(callback);
    };
  }

  /**
   * Emit event to all subscribers
   */
  private emit(data: WorkflowExecutionUpdate): void {
    this.callbacks.forEach((callback) => {
      try {
        callback(data);
      } catch (error) {
        console.error('[WebSocket] Callback error:', error);
      }
    });
  }

  /**
   * Get connection status
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get current state
   */
  get readyState(): number | null {
    return this.ws?.readyState ?? null;
  }
}

// Export singleton instance
export const workflowWebSocket = new WebSocketManager();
