# Expression Syntax - Quick Start Guide

Get started with n8n-style expressions in 5 minutes.

## What Are Expressions?

Expressions let you reference data from previous workflow nodes:

```
{{$("NodeName").data.field}}
```

## Quick Example

### Workflow: HttpTrigger → Extraction → HttpRequest

1. **HttpTrigger** outputs:
   ```json
   {
     "data": {
       "callback_url": "https://example.com/callback"
     }
   }
   ```

2. **Extraction** outputs:
   ```json
   {
     "data": {
       "invoice_number": "INV-2024-001",
       "total": 1250.50
     }
   }
   ```

3. **HttpRequest** uses expressions in URL:
   ```
   {{$("HttpTrigger").data.callback_url}}?invoice={{$("Extraction").data.invoice_number}}&total={{$("Extraction").data.total}}
   ```

4. **Result**:
   ```
   https://example.com/callback?invoice=INV-2024-001&total=1250.50
   ```

## How to Use

### Step 1: Create Workflow

1. Open workflow builder
2. Add nodes: HttpTrigger → HttpRequest
3. Connect them with an edge

### Step 2: Open Configuration

1. Click on HttpRequest node
2. Configuration panel opens on right
3. Find the URL field

### Step 3: Insert Expression

**Option A: Type Manually**
```
{{$("HttpTrigger").data.callback_url}}
```

**Option B: Use Expression Builder**
1. Click "Insert Expression" button
2. Expand "HttpTrigger" node
3. Click on "callback_url" field
4. Expression is inserted automatically

### Step 4: See Preview

The preview box shows the resolved value:
```
Preview: https://example.com/callback
```

## Common Patterns

### 1. Dynamic Webhook URL

```
{{$("HttpTrigger").data.callback_url}}
```

### 2. Pass Multiple Values

```
https://api.example.com/invoice?id={{$("Extraction").data.invoice_number}}&total={{$("Extraction").data.total}}
```

### 3. Authentication Header

```
Authorization: Bearer {{$("HttpTrigger").data.api_token}}
```

### 4. Nested Field Access

```
{{$("PythonRunner").data.result.total_with_tax}}
```

### 5. Context-Aware Prompt

```
Extract invoice data and send to {{$("HttpTrigger").data.callback_url}}
```

## Supported Fields

| Node Type | Field | Support |
|-----------|-------|---------|
| HttpRequest | URL | ✅ Full |
| HttpRequest | Headers | ✅ Full |
| Extraction | Prompt | ✅ Full |
| PythonRunner | Code | ⚠️ Limited |

## Visual Guide

### Expression Builder Interface

```
┌─────────────────────────────────────┐
│ Available Nodes                     │
│                                     │
│ ▼ HttpTrigger                       │
│   ├─ data                           │
│   │  ├─ prompt         Copy  "..."  │
│   │  ├─ callback_url   Copy  "..."  │
│   │  └─ file_url       Copy  "..."  │
│                                     │
│ ▼ Extraction                        │
│   ├─ data                           │
│   │  ├─ invoice_number Copy  "..."  │
│   │  ├─ total          Copy  1250.50│
│   │  └─ date           Copy  "..."  │
└─────────────────────────────────────┘
```

### Configuration Panel

```
┌─────────────────────────────────────┐
│ URL                [Insert Expression]│
│ ┌─────────────────────────────────┐ │
│ │ {{$("HttpTrigger").data.callback│ │
│ └─────────────────────────────────┘ │
│                                     │
│ Preview:                            │
│ ┌─────────────────────────────────┐ │
│ │ https://example.com/callback    │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Validation

Expressions are validated in real-time:

✅ **Valid**
```
{{$("HttpTrigger").data.callback_url}}
```

❌ **Invalid** - Node doesn't exist
```
{{$("NonExistentNode").data.field}}
Error: Referenced node "NonExistentNode" does not exist
```

❌ **Invalid** - Syntax error
```
{{$("HttpTrigger".data.field}}
Error: Invalid expression syntax
```

## Tips & Tricks

### 1. Use Descriptive Node Names

```
✅ "InvoiceExtraction" instead of "Extraction1"
✅ "PaymentWebhook" instead of "HttpRequest"
```

### 2. Check Preview Before Running

Always verify the preview shows expected values.

### 3. Start Simple

Begin with simple expressions, then combine:

**Step 1:**
```
{{$("HttpTrigger").data.callback_url}}
```

**Step 2:**
```
{{$("HttpTrigger").data.callback_url}}?id={{$("Extraction").data.invoice_number}}
```

### 4. Copy from Expression Builder

Use the copy icon to get exact syntax.

### 5. Test with Sample Data

The workflow comes with sample data for testing.

## Troubleshooting

### Expression Not Working?

1. **Check node name** - Must match exactly (case-sensitive)
2. **Check connection** - Node must be connected before current node
3. **Check field path** - Use exact field names from data structure
4. **Check validation** - Look for red error messages

### Preview Not Showing?

1. **Sample data** - Node needs outputData for preview
2. **Valid expression** - Must be syntactically correct
3. **Connected nodes** - Nodes must be properly connected

### Common Mistakes

| Mistake | Fix |
|---------|-----|
| `{{$("Node").field}}` | ❌ Missing `.data` |
| `{{$("Node").data.field}}` | ✅ Correct |
| `{{$('Node').data.field}}` | ⚠️ Use double quotes |
| `{{$("Node").data.field}}` | ✅ Correct |

## Next Steps

1. ✅ Read [EXPRESSION_SYNTAX.md](./EXPRESSION_SYNTAX.md) for complete documentation
2. ✅ Try creating a simple workflow
3. ✅ Experiment with nested fields
4. ✅ Test with multiple expressions
5. ✅ Explore advanced patterns

## Need Help?

- 📖 Full Documentation: [EXPRESSION_SYNTAX.md](./EXPRESSION_SYNTAX.md)
- 🔍 Implementation Details: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- 💡 Code Reference: [expression-parser.ts](./src/lib/expression-parser.ts)

---

**Quick Start**: 5 minutes
**Complexity**: Beginner-friendly
**Power**: Production-ready
