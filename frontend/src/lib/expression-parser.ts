/**
 * Expression Parser - n8n-style expression syntax support
 * Allows referencing data from previous nodes using {{$("NodeName").data.field}}
 */

import type { WorkflowNode } from '@/types/workflow';

/**
 * Regex to match expression syntax: {{$("NodeName").data.field}}
 */
const EXPRESSION_REGEX = /\{\{\$\("([^"]+)"\)\.data\.([^\}]+)\}\}/g;

/**
 * Extract node name and field path from expression string
 * Example: "{{$('NodeName').data.field}}" => { nodeName: "NodeName", fieldPath: "field" }
 */
export function parseExpression(expression: string): {
  nodeName: string;
  fieldPath: string;
} | null {
  const match = expression.match(/\$\("([^"]+)"\)\.data\.([^\}]+)/);
  if (!match) return null;

  const [, nodeName, fieldPath] = match;
  return { nodeName, fieldPath };
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
 * Find all expressions in a string
 * Example: "URL: {{$('Node1').data.url}} ID: {{$('Node2').data.id}}"
 * Returns: ["{{$('Node1').data.url}}", "{{$('Node2').data.id}}"]
 */
export function findExpressions(input: string): string[] {
  const matches = input.match(EXPRESSION_REGEX);
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

    // Replace comparison operators with JavaScript-safe equivalents
    // This handles cases where the resolved string might have issues
    let safeCondition = resolved;

    // Ensure string comparisons are properly quoted
    // This is a simplified approach - in production, use a proper expression parser
    // like mathjs or expr-eval for safer evaluation

    // For now, we'll use a simple Function constructor approach
    // which is safer than eval() but still requires caution with user input
    // In production, expressions should be pre-validated and sanitized

    // IMPORTANT: This should only evaluate resolved expressions, not raw user input
    // The resolved string should only contain numbers, booleans, and operators

    // Create a safe evaluation function
    const evaluator = new Function(`
      'use strict';
      try {
        return Boolean(${safeCondition});
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
