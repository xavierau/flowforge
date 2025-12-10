/**
 * Expression Parser - n8n-style expression syntax support
 * Allows referencing data from previous nodes using {{$("NodeName").data.field}}
 * Also supports:
 * - {{$secrets.SECRET_NAME}} - Secret reference
 * - {{$loop.item}} - Current loop item
 * - {{$loop.index}} - Current iteration index
 * - {{$loop.first}} - Is first iteration
 * - {{$loop.last}} - Is last iteration
 * - {{$loop.length}} - Total array length
 */

import type { WorkflowNode } from '@/types/workflow';

/**
 * Regex to match secret reference syntax: {{$secrets.SECRET_NAME}}
 */
const SECRET_EXPRESSION_REGEX = /\{\{\$secrets\.([a-zA-Z_][a-zA-Z0-9_]*)\}\}/g;

/**
 * Regex to match loop context syntax: {{$loop.property}}
 */
const LOOP_EXPRESSION_REGEX = /\{\{\$loop\.(item|index|first|last|length)\}\}/g;

/**
 * Combined regex for finding all expression types
 */
const EXPRESSION_REGEX = /\{\{\$(?:\("([^"]+)"\)\.data\.([^}]+)|secrets\.([a-zA-Z_][a-zA-Z0-9_]*)|loop\.(item|index|first|last|length))\}\}/g;

/**
 * Expression type discriminators
 */
export type ExpressionType = 'node' | 'secret' | 'loop';

export interface NodeExpression {
  type: 'node';
  nodeName: string;
  fieldPath: string;
}

export interface SecretExpression {
  type: 'secret';
  secretName: string;
}

export interface LoopExpression {
  type: 'loop';
  property: 'item' | 'index' | 'first' | 'last' | 'length';
}

export type ParsedExpression = NodeExpression | SecretExpression | LoopExpression;

/**
 * Extract node name and field path from expression string
 * Example: "{{$('NodeName').data.field}}" => { nodeName: "NodeName", fieldPath: "field" }
 */
export function parseExpression(expression: string): {
  nodeName: string;
  fieldPath: string;
} | null {
  const match = expression.match(/\$\("([^"]+)"\)\.data\.([^}]+)/);
  if (!match) return null;

  const [, nodeName, fieldPath] = match;
  return { nodeName, fieldPath };
}

/**
 * Parse any expression type and return structured result
 * @param expression - Raw expression string like "{{$secrets.API_KEY}}"
 * @returns Parsed expression object or null if invalid
 */
export function parseAnyExpression(expression: string): ParsedExpression | null {
  // Try node expression
  const nodeMatch = expression.match(/\$\("([^"]+)"\)\.data\.([^}]+)/);
  if (nodeMatch) {
    return {
      type: 'node',
      nodeName: nodeMatch[1],
      fieldPath: nodeMatch[2],
    };
  }

  // Try secret expression
  const secretMatch = expression.match(/\$secrets\.([a-zA-Z_][a-zA-Z0-9_]*)/);
  if (secretMatch) {
    return {
      type: 'secret',
      secretName: secretMatch[1],
    };
  }

  // Try loop expression
  const loopMatch = expression.match(/\$loop\.(item|index|first|last|length)/);
  if (loopMatch) {
    return {
      type: 'loop',
      property: loopMatch[1] as LoopExpression['property'],
    };
  }

  return null;
}

/**
 * Parse a secret expression
 * Example: "{{$secrets.API_KEY}}" => "API_KEY"
 */
export function parseSecretExpression(expression: string): string | null {
  const match = expression.match(/\$secrets\.([a-zA-Z_][a-zA-Z0-9_]*)/);
  return match ? match[1] : null;
}

/**
 * Parse a loop expression
 * Example: "{{$loop.item}}" => "item"
 */
export function parseLoopExpression(expression: string): string | null {
  const match = expression.match(/\$loop\.(item|index|first|last|length)/);
  return match ? match[1] : null;
}

/**
 * Get nested value from object using dot notation path
 * Example: getNestedValue({ a: { b: { c: 123 } } }, "a.b.c") => 123
 */
export function getNestedValue(obj: unknown, path: string): unknown {
  if (!obj || typeof obj !== 'object') return undefined;

  const keys = path.split('.');
  let current: unknown = obj;

  for (const key of keys) {
    if (
      current === null ||
      current === undefined ||
      typeof current !== 'object'
    ) {
      return undefined;
    }
    current = (current as Record<string, unknown>)[key];
  }

  return current;
}

/**
 * Find all expressions in a string (supports node, secret, and loop expressions)
 * Example: "URL: {{$('Node1').data.url}} ID: {{$('Node2').data.id}}"
 * Returns: ["{{$('Node1').data.url}}", "{{$('Node2').data.id}}"]
 */
export function findExpressions(input: string): string[] {
  const matches = input.match(EXPRESSION_REGEX);
  return matches || [];
}

/**
 * Find all secret expressions in a string
 * Example: "API Key: {{$secrets.API_KEY}} Token: {{$secrets.AUTH_TOKEN}}"
 * Returns: ["{{$secrets.API_KEY}}", "{{$secrets.AUTH_TOKEN}}"]
 */
export function findSecretExpressions(input: string): string[] {
  const matches = input.match(SECRET_EXPRESSION_REGEX);
  return matches || [];
}

/**
 * Find all loop expressions in a string
 * Example: "Item: {{$loop.item}} Index: {{$loop.index}}"
 * Returns: ["{{$loop.item}}", "{{$loop.index}}"]
 */
export function findLoopExpressions(input: string): string[] {
  const matches = input.match(LOOP_EXPRESSION_REGEX);
  return matches || [];
}

/**
 * Extract unique node names referenced in expressions
 * Example: "{{$('Node1').data.url}} {{$('Node1').data.id}} {{$('Node2').data.name}}"
 * Returns: ["Node1", "Node2"]
 */
export function extractReferencedNodes(input: string): string[] {
  const expressions = findExpressions(input);
  const nodeNames = new Set<string>();

  for (const expr of expressions) {
    const parsed = parseExpression(expr);
    if (parsed) {
      nodeNames.add(parsed.nodeName);
    }
  }

  return Array.from(nodeNames);
}

/**
 * Resolve a single expression to its value
 * Returns empty string if node/field not found
 */
export function resolveExpression(
  expression: string,
  nodes: WorkflowNode[]
): string {
  const parsed = parseExpression(expression);
  if (!parsed) return expression;

  const { nodeName, fieldPath } = parsed;

  // Find node by label
  const node = nodes.find((n) => n.data.label === nodeName);
  if (!node) return '';

  // Get output data from node
  const outputData = node.data.outputData;
  if (!outputData) return '';

  // Navigate nested fields
  const value = getNestedValue(outputData, fieldPath);

  // Convert to string
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

/**
 * Resolve all expressions in a string
 * Example: "URL: {{$('HttpTrigger').data.callback_url}}"
 * Returns: "URL: https://example.com/callback"
 */
export function resolveExpressions(
  input: string,
  nodes: WorkflowNode[]
): string {
  if (!input) return input;

  return input.replace(EXPRESSION_REGEX, (match) => {
    return resolveExpression(match, nodes);
  });
}

/**
 * Validate that all referenced nodes exist
 * Returns error message if invalid, null if valid
 */
export function validateExpression(
  input: string,
  nodes: WorkflowNode[]
): string | null {
  const expressions = findExpressions(input);
  if (expressions.length === 0) return null;

  for (const expr of expressions) {
    const parsed = parseExpression(expr);
    if (!parsed) {
      return `Invalid expression syntax: ${expr}`;
    }

    const { nodeName } = parsed;
    const nodeExists = nodes.some((n) => n.data.label === nodeName);
    if (!nodeExists) {
      return `Referenced node "${nodeName}" does not exist`;
    }
  }

  return null;
}

/**
 * Check if a string contains any expressions
 */
export function hasExpressions(input: string): boolean {
  return EXPRESSION_REGEX.test(input);
}

/**
 * Get available nodes for expression builder (nodes before current node)
 * Returns nodes that appear earlier in the workflow execution order
 */
export function getAvailableNodes(
  currentNodeId: string,
  allNodes: WorkflowNode[],
  edges: Array<{ source: string; target: string }>
): WorkflowNode[] {
  // Build adjacency list (reverse direction: target -> sources)
  const predecessors = new Map<string, Set<string>>();

  edges.forEach((edge) => {
    if (!predecessors.has(edge.target)) {
      predecessors.set(edge.target, new Set());
    }
    predecessors.get(edge.target)!.add(edge.source);
  });

  // BFS to find all nodes that can reach current node
  const available = new Set<string>();
  const queue: string[] = [currentNodeId];
  const visited = new Set<string>();

  while (queue.length > 0) {
    const nodeId = queue.shift()!;
    if (visited.has(nodeId)) continue;
    visited.add(nodeId);

    const sources = predecessors.get(nodeId);
    if (sources) {
      sources.forEach((sourceId) => {
        available.add(sourceId);
        queue.push(sourceId);
      });
    }
  }

  // Return nodes that are available (excluding current node)
  return allNodes.filter((node) => available.has(node.id));
}

/**
 * Format expression string for insertion
 * Example: formatExpression("HttpTrigger", "callback_url")
 * Returns: "{{$("HttpTrigger").data.callback_url}}"
 */
export function formatExpression(nodeName: string, fieldPath: string): string {
  return `{{$("${nodeName}").data.${fieldPath}}}`;
}

/**
 * Evaluate a condition expression to a boolean result
 * First resolves all expressions, then evaluates the condition
 *
 * Example:
 *   condition: "{{$('Extraction').data.total}} > 100"
 *   With Extraction.data.total = 150
 *   Returns: true
 *
 * Supports:
 *   - Comparison: >, <, >=, <=, ==, !=
 *   - Logical: && (AND), || (OR)
 *   - Parentheses for grouping
 *
 * @param condition - Condition string with expressions
 * @param nodes - All workflow nodes for expression resolution
 * @returns boolean result of the condition, false if evaluation fails
 */
export function evaluateCondition(
  condition: string,
  nodes: WorkflowNode[]
): boolean {
  if (!condition || condition.trim() === '') {
    return false;
  }

  try {
    // First resolve all expressions to their actual values
    const resolved = resolveExpressions(condition, nodes);

    // The resolved string should only contain numbers, booleans, and operators
    // This is a simplified approach - in production, use a proper expression parser
    // like mathjs or expr-eval for safer evaluation

    // Create a safe evaluation function
    const evaluator = new Function(`
      'use strict';
      try {
        return Boolean(${resolved});
      } catch (e) {
        return false;
      }
    `);

    return evaluator();
  } catch (error) {
    console.error('Error evaluating condition:', error);
    return false;
  }
}

/**
 * Test if a condition is syntactically valid
 * Checks for basic syntax errors without evaluating
 *
 * @param condition - Condition string to validate
 * @returns true if condition appears valid, false otherwise
 */
export function isValidCondition(condition: string): boolean {
  if (!condition || condition.trim() === '') {
    return false;
  }

  // Check for balanced parentheses
  let parenCount = 0;
  for (const char of condition) {
    if (char === '(') parenCount++;
    if (char === ')') parenCount--;
    if (parenCount < 0) return false; // Closing before opening
  }
  if (parenCount !== 0) return false; // Unbalanced

  // Check for at least one operator
  const operators = ['>', '<', '>=', '<=', '==', '!=', '&&', '||'];
  const hasOperator = operators.some((op) => condition.includes(op));

  return hasOperator;
}

/**
 * Format a secret expression for insertion
 * Example: formatSecretExpression("API_KEY")
 * Returns: "{{$secrets.API_KEY}}"
 */
export function formatSecretExpression(secretName: string): string {
  return `{{$secrets.${secretName}}}`;
}

/**
 * Format a loop expression for insertion
 * Example: formatLoopExpression("item")
 * Returns: "{{$loop.item}}"
 */
export function formatLoopExpression(
  property: 'item' | 'index' | 'first' | 'last' | 'length'
): string {
  return `{{$loop.${property}}}`;
}

/**
 * Check if a string contains any secret expressions
 */
export function hasSecretExpressions(input: string): boolean {
  return SECRET_EXPRESSION_REGEX.test(input);
}

/**
 * Check if a string contains any loop expressions
 */
export function hasLoopExpressions(input: string): boolean {
  return LOOP_EXPRESSION_REGEX.test(input);
}

/**
 * Extract unique secret names referenced in expressions
 * Example: "Key: {{$secrets.API_KEY}} Auth: {{$secrets.API_KEY}}"
 * Returns: ["API_KEY"]
 */
export function extractReferencedSecrets(input: string): string[] {
  const expressions = findSecretExpressions(input);
  const secretNames = new Set<string>();

  for (const expr of expressions) {
    const secretName = parseSecretExpression(expr);
    if (secretName) {
      secretNames.add(secretName);
    }
  }

  return Array.from(secretNames);
}

/**
 * Extract loop properties referenced in expressions
 * Example: "Item: {{$loop.item}} Index: {{$loop.index}}"
 * Returns: ["item", "index"]
 */
export function extractReferencedLoopProperties(input: string): string[] {
  const expressions = findLoopExpressions(input);
  const properties = new Set<string>();

  for (const expr of expressions) {
    const property = parseLoopExpression(expr);
    if (property) {
      properties.add(property);
    }
  }

  return Array.from(properties);
}

/**
 * Loop context for runtime expression resolution
 */
export interface LoopContext {
  /** Current item being processed */
  item: unknown;
  /** Current iteration index (0-based) */
  index: number;
  /** Whether this is the first iteration */
  first: boolean;
  /** Whether this is the last iteration */
  last: boolean;
  /** Total length of the array being iterated */
  length: number;
}

/**
 * Resolve loop expressions using provided context
 * Used during workflow execution to replace {{$loop.X}} with actual values
 *
 * @param input - String containing loop expressions
 * @param context - Current loop context
 * @returns String with loop expressions resolved
 */
export function resolveLoopExpressions(
  input: string,
  context: LoopContext
): string {
  if (!input) return input;

  return input.replace(LOOP_EXPRESSION_REGEX, (match, property) => {
    switch (property) {
      case 'item':
        if (context.item === null || context.item === undefined) return '';
        if (typeof context.item === 'object') return JSON.stringify(context.item);
        return String(context.item);
      case 'index':
        return String(context.index);
      case 'first':
        return String(context.first);
      case 'last':
        return String(context.last);
      case 'length':
        return String(context.length);
      default:
        return match;
    }
  });
}

/**
 * Secrets context for runtime expression resolution
 */
export type SecretsContext = Record<string, string>;

/**
 * Resolve secret expressions using provided context
 * Used during workflow execution to replace {{$secrets.X}} with actual values
 * NOTE: In production, this should be handled server-side to keep secrets secure
 *
 * @param input - String containing secret expressions
 * @param secrets - Map of secret names to values
 * @returns String with secret expressions resolved (or placeholder if not found)
 */
export function resolveSecretExpressions(
  input: string,
  secrets: SecretsContext
): string {
  if (!input) return input;

  return input.replace(SECRET_EXPRESSION_REGEX, (_match, secretName) => {
    const value = secrets[secretName];
    if (value === undefined) {
      // Return a placeholder to indicate missing secret
      return `[SECRET:${secretName}]`;
    }
    return value;
  });
}
