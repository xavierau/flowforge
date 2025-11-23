# Expression Syntax Documentation

n8n-style expression syntax support for referencing data from previous workflow nodes.

## Overview

The workflow builder now supports dynamic expressions that allow nodes to reference data from previous nodes in the execution flow. This enables powerful data transformation and composition patterns similar to n8n.

## Syntax

```
{{$("NodeName").data.field}}
```

- `{{...}}` - Expression delimiters
- `$("NodeName")` - Reference to a node by its label/name
- `.data.field` - Access to the node's output data

## Supported Features

### 1. Basic Field Access

Reference simple fields from previous nodes:

```
{{$("HttpTrigger").data.callback_url}}
{{$("Extraction").data.invoice_number}}
```

### 2. Nested Field Access

Use dot notation to access nested fields:

```
{{$("Extraction").data.result.total}}
{{$("PythonRunner").data.result.total_with_tax}}
```

### 3. Multiple Expressions

Use multiple expressions in a single field:

```
https://api.example.com/webhook?id={{$("HttpTrigger").data.callback_url}}&invoice={{$("Extraction").data.invoice_number}}
```

### 4. Expression in Headers

HTTP headers support expressions in both keys and values:

```
Authorization: Bearer {{$("HttpTrigger").data.api_token}}
X-Invoice-ID: {{$("Extraction").data.invoice_number}}
```

## Where Expressions Work

### HttpRequest Node
- **URL field**: Full expression support for dynamic endpoints
- **Header values**: Reference tokens, IDs, or other data
- **Header keys**: Use dynamic header names (advanced)

**Example:**
```
URL: https://api.example.com/invoices/{{$("Extraction").data.invoice_number}}/callback?url={{$("HttpTrigger").data.callback_url}}
```

### Extraction Node
- **Prompt field**: Include data from previous nodes in extraction prompts

**Example:**
```
Extract invoice data. Use callback URL: {{$("HttpTrigger").data.callback_url}} for notifications.
```

### PythonRunner Node
- **Code field**: Use expressions in template strings or comments

**Example:**
```python
# Process invoice: {{$("Extraction").data.invoice_number}}
callback_url = "{{$("HttpTrigger").data.callback_url}}"
```

## Expression Builder UI

### Accessing the Builder

1. Navigate to the node configuration panel
2. Look for the "Insert Expression" button next to supported fields
3. Click to open the expression builder popover

### Using the Builder

1. **Browse Available Nodes**: Only previous nodes in the execution flow are shown
2. **Expand Node Data**: Click on a node to see its output data structure
3. **Select Field**: Click on any field to insert its expression
4. **Copy Expression**: Hover over a field and click the copy icon

### Visual Feedback

- **Syntax Highlighting**: Expressions are highlighted in the UI
- **Live Preview**: See resolved values in real-time (if sample data available)
- **Validation**: Invalid expressions (referencing non-existent nodes) show errors

## Validation

### Automatic Validation

Expressions are validated automatically:

1. **Node Existence**: Referenced node must exist in the workflow
2. **Connection Order**: Only nodes earlier in the execution flow can be referenced
3. **Syntax Validity**: Expression syntax must be correct

### Error Messages

Common validation errors:

- `Referenced node "NodeName" does not exist` - Node not found
- `Invalid expression syntax` - Malformed expression
- `Invalid URL format` - URL with unresolved expressions

## Sample Data Structure

Each node type has default sample output data for testing:

### HttpTrigger
```json
{
  "data": {
    "prompt": "Extract invoice data from the document",
    "callback_url": "https://example.com/webhook/callback",
    "file_url": "https://example.com/files/invoice.pdf"
  }
}
```

### Extraction
```json
{
  "data": {
    "invoice_number": "INV-2024-001",
    "total": 1250.50,
    "date": "2024-11-15",
    "vendor": "Acme Corporation",
    "items": [
      { "description": "Product A", "quantity": 2, "price": 500.00 },
      { "description": "Product B", "quantity": 1, "price": 250.50 }
    ]
  }
}
```

### PythonRunner
```json
{
  "data": {
    "result": {
      "processed": true,
      "total_with_tax": 1375.55,
      "summary": "Invoice processed successfully"
    }
  }
}
```

## Example Workflows

### Example 1: Webhook Callback

**Workflow**: HttpTrigger → Extraction → HttpRequest

**HttpRequest URL**:
```
{{$("HttpTrigger").data.callback_url}}?invoice={{$("Extraction").data.invoice_number}}&total={{$("Extraction").data.total}}
```

**Resolved**:
```
https://example.com/webhook/callback?invoice=INV-2024-001&total=1250.50
```

### Example 2: Dynamic Authorization

**Workflow**: HttpTrigger → Extraction → HttpRequest

**HttpRequest Headers**:
```
Authorization: Bearer {{$("HttpTrigger").data.api_token}}
X-Invoice-ID: {{$("Extraction").data.invoice_number}}
Content-Type: application/json
```

### Example 3: Context-Aware Prompt

**Workflow**: HttpTrigger → Extraction

**Extraction Prompt**:
```
Extract invoice data from the document.
After extraction, send results to: {{$("HttpTrigger").data.callback_url}}
```

## Implementation Details

### File Structure

```
frontend/src/
├── lib/
│   └── expression-parser.ts          # Expression parsing utilities
├── components/
│   └── workflow/
│       ├── ExpressionBuilder.tsx     # Expression builder UI
│       ├── NodeConfigPanel.tsx       # Updated with expression support
│       └── nodes/
│           └── HttpRequestNode.tsx   # Updated with expression hints
├── store/
│   └── workflowStore.ts              # Updated validation logic
└── types/
    └── workflow.ts                   # Updated with outputData field
```

### Key Functions

#### `expression-parser.ts`

- `parseExpression(expr: string)` - Parse expression syntax
- `resolveExpression(expr: string, nodes: WorkflowNode[])` - Resolve to value
- `resolveExpressions(input: string, nodes: WorkflowNode[])` - Resolve all expressions in string
- `validateExpression(input: string, nodes: WorkflowNode[])` - Validate expression
- `getAvailableNodes(nodeId: string, nodes: WorkflowNode[], edges: Edge[])` - Get previous nodes
- `formatExpression(nodeName: string, fieldPath: string)` - Format expression string

#### `ExpressionBuilder.tsx`

- Tree view for node data structure
- Click-to-insert interaction
- Copy expression to clipboard
- Nested field expansion

### Store Integration

The workflow store automatically validates expressions when:
1. Node data is updated
2. Connections are added/removed
3. Nodes are renamed

### Performance Considerations

- Expression resolution is memoized using `useMemo`
- Tree rendering uses React best practices
- Validation is debounced (1 second) to prevent excessive computation

## Best Practices

### 1. Name Nodes Descriptively

Use clear, descriptive names for nodes that will be referenced:

```
✅ "InvoiceExtraction" instead of "Extraction1"
✅ "PaymentWebhook" instead of "HttpTrigger"
```

### 2. Test with Sample Data

Use the sample output data to test expressions before deploying:

1. Create workflow
2. Add expressions
3. Verify preview shows expected values
4. Test with real data

### 3. Handle Missing Data

Expressions return empty strings if data is missing:

```
URL: https://api.example.com/invoices/{{$("Extraction").data.invoice_number}}
```

If `invoice_number` is missing, resolves to:
```
https://api.example.com/invoices/
```

### 4. Avoid Circular References

The workflow engine prevents cycles, but be mindful of data flow:

```
❌ NodeA references NodeB, NodeB references NodeA (prevented by validation)
✅ NodeA → NodeB → NodeC (linear flow)
```

### 5. Keep Expressions Simple

Use simple field paths for maintainability:

```
✅ {{$("Node").data.id}}
✅ {{$("Node").data.result.total}}
❌ {{$("Node").data.items[0].nested.deep.field}} (works but hard to maintain)
```

## Troubleshooting

### Expression Not Resolving

**Problem**: Expression shows in preview but doesn't resolve

**Solutions**:
1. Check node name matches exactly (case-sensitive)
2. Verify node is connected earlier in flow
3. Check field path is correct
4. Ensure sample/runtime data structure matches

### Validation Errors

**Problem**: "Referenced node does not exist"

**Solutions**:
1. Check node name spelling
2. Verify node is connected
3. Ensure node appears before current node

### URL Format Errors

**Problem**: "Invalid URL format" with expressions

**Solutions**:
1. Expressions with unresolved values are allowed
2. Ensure base URL structure is valid
3. Use placeholder values for testing

## Future Enhancements

Potential features for future development:

1. **Expression Functions**: `{{$("Node").data.total.toFixed(2)}}`
2. **Array Indexing**: `{{$("Node").data.items[0].price}}`
3. **Conditional Expressions**: `{{$("Node").data.total > 1000 ? "high" : "low"}}`
4. **String Operations**: `{{$("Node").data.name.toUpperCase()}}`
5. **Date Formatting**: `{{$("Node").data.date.format("YYYY-MM-DD")}}`
6. **Math Operations**: `{{$("Node").data.price * 1.1}}`

## API Reference

See [expression-parser.ts](./src/lib/expression-parser.ts) for complete API documentation.

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0
**Author**: AI Document Processing Team
