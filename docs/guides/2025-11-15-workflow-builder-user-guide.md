# Workflow Builder - User Guide

**Date**: 2025-11-15
**Version**: 1.0
**Location**: `/workflows` route in frontend application

## Overview

The Workflow Builder is an n8n-style visual workflow editor that allows you to create automated document processing pipelines with conditional logic, data extraction, Python transformations, and external API integrations.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Node Types](#node-types)
3. [Expression Syntax](#expression-syntax)
4. [Building Your First Workflow](#building-your-first-workflow)
5. [Common Patterns](#common-patterns)
6. [Tips & Best Practices](#tips--best-practices)

---

## Getting Started

### Accessing the Workflow Builder

1. Navigate to `http://localhost:3003/workflows` (or your deployment URL)
2. You'll see a canvas with three sections:
   - **Left Sidebar**: Node types and workflow controls
   - **Center Canvas**: Visual workflow builder
   - **Right Panel**: Node configuration (appears when node is selected)

### Workflow Controls

- **Workflow Name**: Click the text at the top to rename your workflow
- **Add Nodes**: Click node type buttons in the left sidebar
- **Save**: Workflows auto-save to localStorage every second
- **Export**: Save workflow as JSON file
- **Import**: Load workflow from JSON file
- **Clear**: Reset canvas (with confirmation)

### Canvas Navigation

- **Pan**: Click and drag on empty space
- **Zoom**: Use controls in bottom-right or mouse wheel
- **Select Node**: Click on a node
- **Move Node**: Drag node to reposition
- **Connect Nodes**: Drag from output handle (bottom) to input handle (top)
- **Delete Connection**: Select edge and press Delete key
- **Minimap**: See overview in bottom-right corner

---

## Node Types

The workflow builder includes 5 node types for different tasks:

### 1. HTTP Trigger

**Purpose**: Entry point for your workflow

**Configuration**:
- No configuration required
- Accepts incoming data at runtime

**Input Format**:
```json
{
  "data": {
    "prompt": "Extract invoice data",
    "file_url": "https://example.com/invoice.pdf",
    "base64": "base64_encoded_pdf_data",
    "callback_url": "https://example.com/webhook"
  }
}
```

**Outputs**: 1 handle (passes trigger data to next node)

**Use Cases**:
- Webhook endpoint for external systems
- API trigger for workflow execution
- Starting point for all workflows

**Visual**: 🌐 Icon, blue accent

---

### 2. Extraction

**Purpose**: Extract structured data from documents using Vision Language Models (VLLMs)

**Configuration**:
- **File Source**: Select where the file comes from (trigger or upload)
- **Prompt**: Instructions for the extraction model
- **Schema**: Select a saved schema for structured output

**Example Configuration**:
```
Prompt: "Extract all line items, totals, and vendor information"
Schema: invoice_schema_v1
```

**Input**: Document data from previous node

**Output Format**:
```json
{
  "data": {
    "invoice_number": "INV-12345",
    "date": "2025-11-15",
    "total": 1250.50,
    "line_items": [
      {"description": "Product A", "amount": 500.00},
      {"description": "Product B", "amount": 750.50}
    ]
  }
}
```

**Use Cases**:
- Invoice data extraction
- Receipt processing
- Form data extraction
- Document classification

**Visual**: 📄 Icon with file symbol

---

### 3. Python Runner

**Purpose**: Transform, validate, or enrich data using Python code

**Configuration**:
- **Python Code**: Write transformation logic in embedded editor

**Code Environment**:
- Input is wrapped as `{data: extraction_result}`
- Access fields: `data.get("field_name", default_value)`
- Must return a dictionary/object
- Output is wrapped as `{data: python_result}`

**Example Code**:
```python
# Access previous node data
total = data.get("total", 0)
line_items = data.get("line_items", [])

# Transform data
tax_rate = 0.08
tax_amount = total * tax_rate
grand_total = total + tax_amount

# Calculate item count
item_count = len(line_items)

# Return new data structure
return {
    "original_total": total,
    "tax_amount": round(tax_amount, 2),
    "grand_total": round(grand_total, 2),
    "item_count": item_count,
    "requires_approval": grand_total > 1000
}
```

**Security Restrictions**:
- Dangerous imports are blocked: `os`, `sys`, `subprocess`, `eval`, `exec`
- Code must include a `return` statement
- Python syntax is validated in real-time

**Use Cases**:
- Calculate derived values (tax, totals)
- Data validation and enrichment
- Complex business logic
- Format transformations

**Visual**: 🐍 Icon with Python logo

---

### 4. If (Conditional)

**Purpose**: Branch workflow based on conditions

**Configuration**:
- **Condition**: Expression that evaluates to true or false

**Condition Syntax**:
```javascript
// Simple comparisons
{{$("Extraction").data.total}} > 100
{{$("Extraction").data.status}} == "approved"
{{$("Python").data.score}} >= 0.8

// Logical operators
{{$("Python").data.valid}} == true && {{$("Python").data.score}} > 0.8
({{$("Extraction").data.amount}} > 1000) || {{$("Extraction").data.priority}} == "high"
```

**Operators**:
- Comparison: `>`, `<`, `>=`, `<=`, `==`, `!=`
- Logical: `&&` (AND), `||` (OR)
- Grouping: `()` parentheses

**Outputs**: 2 handles
- **True** (green, left): Executes when condition is true
- **False** (red, right): Executes when condition is false

**Output Format**:
```json
{
  "data": {
    "condition": "{{$('Extraction').data.total}} > 100",
    "result": true,
    "evaluatedValue": 150
  }
}
```

**Use Cases**:
- Route high-value invoices differently
- Validate data quality before proceeding
- Implement approval workflows
- Error handling paths

**Visual**: 🌿 GitBranch icon, diamond shape, green/red outputs

---

### 5. HTTP Request

**Purpose**: Send data to external APIs or webhooks

**Configuration**:
- **URL**: API endpoint (supports expressions)
- **Method**: GET, POST, PUT, DELETE
- **Headers**: Key-value pairs for request headers

**Example Configuration**:
```
URL: {{$("HttpTrigger").data.callback_url}}
Method: POST
Headers:
  Content-Type: application/json
  Authorization: Bearer {{$("HttpTrigger").data.api_key}}
```

**Request Body**:
- Automatically includes data from all previous nodes
- Format: `{"node_name": {data: {...}}, ...}`

**Output Format**:
```json
{
  "data": {
    "status": 200,
    "response": {
      "success": true,
      "id": "webhook-123"
    }
  }
}
```

**Use Cases**:
- Send results to webhook
- Notify external systems
- Update CRM/ERP systems
- Trigger downstream processes

**Visual**: 🌐 Globe icon with arrows

---

## Expression Syntax

Expressions allow nodes to reference data from previous nodes using this syntax:

### Basic Syntax

```
{{$("NodeName").data.field}}
```

### Examples

```javascript
// Simple field access
{{$("HttpTrigger").data.callback_url}}
{{$("Extraction").data.invoice_number}}
{{$("Python").data.grand_total}}

// Nested field access
{{$("Extraction").data.vendor.name}}
{{$("Extraction").data.line_items[0].amount}}
{{$("Python").data.result.nested.value}}
```

### Where Expressions Work

Expressions can be used in:
- ✅ HTTP Request URL field
- ✅ HTTP Request header values
- ✅ If node conditions
- ✅ Extraction prompt field

### Expression Builder

Click the **⟨⟩ braces icon** next to expression-enabled fields to open the Expression Builder:

1. Shows all previous nodes in a tree structure
2. Expand nodes to see their data structure
3. Click a field to insert its expression
4. Use "Copy" button to copy expression to clipboard

### Live Preview

When you use expressions, a preview shows the resolved value below the input field:

```
Input:  {{$("Extraction").data.total}}
Preview: 1250.50
```

### Validation

- ❌ Referenced node must exist
- ❌ Invalid syntax shows error message
- ✅ Valid expressions show green border

---

## Building Your First Workflow

Let's create a simple invoice processing workflow:

### Workflow: Invoice Processing with Approval

**Goal**: Extract invoice data, check if amount requires approval, send to appropriate endpoint

**Steps**:

#### 1. Add HTTP Trigger Node
- Click "HTTP Trigger" in left sidebar
- No configuration needed
- This will receive invoice data

#### 2. Add Extraction Node
- Click "Extraction" in left sidebar
- Connect from HTTP Trigger output to Extraction input
- Configure:
  - Prompt: "Extract invoice number, date, total, and line items"
  - Schema: Select "invoice_schema"

#### 3. Add Python Runner Node
- Click "Python Runner" in left sidebar
- Connect from Extraction output to Python input
- Add code:
```python
total = data.get("total", 0)
tax_rate = 0.08
tax = total * tax_rate
grand_total = total + tax

return {
    "total": total,
    "tax": round(tax, 2),
    "grand_total": round(grand_total, 2),
    "requires_approval": grand_total > 1000
}
```

#### 4. Add If Node
- Click "If" in left sidebar
- Connect from Python output to If input
- Configure condition:
```
{{$("PythonRunner").data.grand_total}} > 1000
```

#### 5. Add HTTP Request Nodes (High Value Path)
- Click "HTTP Request" in left sidebar
- Connect from If **True** output
- Configure:
  - URL: `https://api.example.com/invoices/approval-required`
  - Method: POST

#### 6. Add HTTP Request Node (Standard Path)
- Click "HTTP Request" again
- Connect from If **False** output
- Configure:
  - URL: `https://api.example.com/invoices/auto-process`
  - Method: POST

#### 7. Test Your Workflow
- Save the workflow (auto-saved)
- Click "Export" to save as JSON
- Your workflow is ready!

**Flow Diagram**:
```
HTTP Trigger
     ↓
 Extraction
     ↓
Python Runner (calculate tax)
     ↓
    If (> 1000?)
     ↓           ↓
   True        False
     ↓           ↓
Approval API  Auto-process API
```

---

## Common Patterns

### Pattern 1: Multi-Step Data Enrichment

```
HTTP Trigger → Extraction → Python (validate) → Python (enrich) → HTTP Request
```

**Use Case**: Extract data, validate quality, add business logic, send to external system

---

### Pattern 2: Conditional Routing

```
HTTP Trigger → Extraction → If (condition)
                             ↓          ↓
                           True      False
                             ↓          ↓
                         Path A     Path B
```

**Use Case**: Route documents based on type, amount, or validation results

---

### Pattern 3: Error Handling

```
HTTP Trigger → Extraction → If (valid?)
                             ↓          ↓
                          Valid    Invalid
                             ↓          ↓
                       Process    Error Webhook
```

**Use Case**: Validate extraction results before processing

---

### Pattern 4: Multi-Condition Routing

```
HTTP Trigger → Extraction → If (amount > 1000)
                             ↓              ↓
                          High           Low
                             ↓              ↓
                      If (priority?)  Auto-process
                       ↓         ↓
                   Urgent   Standard
```

**Use Case**: Complex routing based on multiple conditions

---

### Pattern 5: Data Transformation Pipeline

```
HTTP Trigger → Extraction → Python (clean) → Python (validate) → Python (format) → HTTP Request
```

**Use Case**: Multi-stage data transformation

---

## Tips & Best Practices

### Naming Conventions

- ✅ **Use descriptive node names**: "ExtractInvoice", "ValidateData", "SendToERP"
- ❌ **Avoid generic names**: "Extraction", "Python", "If"
- 💡 **Tip**: Node names are used in expressions, make them memorable

### Workflow Organization

- 📐 **Arrange nodes top-to-bottom**: Easier to follow flow
- 🎯 **Group related nodes**: Keep validation, transformation, and routing together
- 🔄 **Use minimap**: Helpful for large workflows

### Expression Usage

- ✅ **Use Expression Builder**: Prevents typos in node names
- ✅ **Test expressions**: Check live preview before saving
- ⚠️ **Handle missing data**: Use default values in Python code

### Validation

- ✅ **Check node borders**: Green = valid, Red = errors, Gray = unconfigured
- ✅ **Fix errors immediately**: Invalid nodes prevent workflow execution
- ⚠️ **Test conditions**: Verify If node logic with sample data

### Python Code

- ✅ **Always return a dict**: `return {...}`
- ✅ **Use `.get()` for safety**: `data.get("field", default)`
- ✅ **Add comments**: Explain complex logic
- ❌ **Avoid dangerous operations**: No file I/O, no system calls

### Performance

- 🚀 **Minimize Python nodes**: Each adds processing time
- 🚀 **Combine logic**: One Python node is faster than multiple
- 🚀 **Optimize conditions**: Simple conditions evaluate faster

### Debugging

- 🔍 **Use live preview**: See resolved expression values
- 🔍 **Check node output data**: Review data structure in Expression Builder
- 🔍 **Test incrementally**: Add nodes one at a time

### Saving & Backup

- 💾 **Auto-save enabled**: Changes saved every second
- 💾 **Export regularly**: Save JSON backups of important workflows
- 💾 **Name workflows clearly**: "Invoice_Processing_v2", "Receipt_Validation"

---

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Delete selected node/edge | Delete or Backspace |
| Fit view to canvas | F |
| Select all | Ctrl/Cmd + A |
| Copy node | Ctrl/Cmd + C |
| Paste node | Ctrl/Cmd + V |

---

## Troubleshooting

### Node Shows Red Border

**Cause**: Validation errors

**Solution**:
1. Select the node
2. Check error messages in right panel
3. Fix configuration issues
4. Save and verify green border

### Expression Not Resolving

**Cause**: Referenced node doesn't exist or wrong field name

**Solution**:
1. Use Expression Builder to verify node name
2. Check field exists in previous node's output data
3. Verify node is connected before the current node

### Can't Connect Nodes

**Cause**: Invalid connection (e.g., connecting to HTTP Trigger input)

**Solution**:
- HTTP Trigger has no input handle (workflow entry point)
- Check source and target node types
- Some connections are prevented for workflow integrity

### Python Code Shows Error

**Cause**: Syntax error or dangerous imports

**Solution**:
1. Check for syntax errors (missing colons, incorrect indentation)
2. Remove dangerous imports (`os`, `sys`, `subprocess`)
3. Ensure code has `return` statement
4. Test with simple code first

### Workflow Not Saving

**Cause**: localStorage full or disabled

**Solution**:
1. Export workflow as JSON file
2. Clear browser localStorage
3. Import workflow from JSON
4. Check browser localStorage settings

---

## Next Steps

- ✅ [Workflow Architecture Guide](./2025-11-15-workflow-architecture.md) - Technical implementation details
- ✅ [Expression Syntax Reference](../../frontend/EXPRESSION_SYNTAX.md) - Complete expression documentation
- ✅ [Workflow Examples](./2025-11-15-workflow-examples.md) - Real-world use cases

---

**Last Updated**: 2025-11-15
**Version**: 1.0
**Feedback**: Report issues or suggestions via GitHub issues
