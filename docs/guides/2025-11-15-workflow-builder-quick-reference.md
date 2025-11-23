# Workflow Builder - Quick Reference

**Date**: 2025-11-15
**Version**: 1.0

## 🚀 Quick Start (5 Minutes)

1. **Navigate**: `http://localhost:3003/workflows`
2. **Add Nodes**: Click buttons in left sidebar
3. **Connect**: Drag from output (bottom) to input (top)
4. **Configure**: Click node → Edit in right panel
5. **Save**: Auto-saves every second

---

## 📦 Node Types (5 Total)

| Icon | Node | Purpose | Inputs | Outputs |
|------|------|---------|--------|---------|
| 🌐 | **HTTP Trigger** | Workflow entry point | 0 | 1 |
| 📄 | **Extraction** | Extract document data | 1 | 1 |
| 🐍 | **Python Runner** | Transform data | 1 | 1 |
| 🌐 | **HTTP Request** | Call external API | 1 | 1 |
| 🌿 | **If** | Conditional branch | 1 | 2 (True/False) |

---

## 💡 Expression Syntax

### Basic Pattern
```javascript
{{$("NodeName").data.field}}
```

### Examples
```javascript
{{$("HttpTrigger").data.callback_url}}
{{$("Extraction").data.total}}
{{$("Python").data.grand_total}}
{{$("Extraction").data.vendor.name}}
```

### Where to Use
- ✅ HTTP Request URL
- ✅ HTTP Request headers
- ✅ If node conditions
- ✅ Extraction prompts

### Expression Builder
Click **⟨⟩** button → Select node → Click field → Insert!

---

## 🎯 Common Patterns

### Pattern 1: Simple Extract & Send
```
Trigger → Extraction → HTTP Request
```

### Pattern 2: Calculate & Route
```
Trigger → Extraction → Python → If → [True/False paths]
```

### Pattern 3: Multi-Step Transform
```
Trigger → Extraction → Python 1 → Python 2 → HTTP Request
```

---

## 🔧 Configuration Cheat Sheet

### HTTP Trigger
```
✓ No configuration needed
✓ Accepts webhook data at runtime
```

### Extraction
```
Required:
- Schema (dropdown)

Optional:
- File source
- Prompt (supports expressions)
```

### Python Runner
```python
# Input format
data = {"field1": "value1", "field2": 123}

# Access fields
field1 = data.get("field1", "default")

# Must return dict
return {"result": calculated_value}
```

### HTTP Request
```
Required:
- URL (supports expressions)
- Method (GET/POST/PUT/DELETE)

Optional:
- Headers (key-value pairs)
```

### If Node
```
Condition examples:
{{$("Extraction").data.total}} > 100
{{$("Python").data.score}} >= 0.8
{{$("Extraction").data.status}} == "approved"

Operators:
>, <, >=, <=, ==, !=, &&, ||, ()
```

---

## ⚡ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Delete | Delete selected node/edge |
| F | Fit view |
| Ctrl/Cmd + A | Select all |
| Ctrl/Cmd + C | Copy |
| Ctrl/Cmd + V | Paste |

---

## 🎨 Visual Indicators

### Node Border Colors
- 🟢 **Green**: Valid, ready to use
- 🔴 **Red**: Has validation errors
- ⚪ **Gray**: Not configured yet

### Edge Colors (If Node)
- 🟢 **Green "True"**: True path
- 🔴 **Red "False"**: False path

---

## 🐍 Python Quick Reference

### Safe Imports
```python
# ✅ Allowed
import json
import math
from datetime import datetime

# ❌ Blocked
import os        # Security risk
import sys       # Security risk
import subprocess  # Security risk
```

### Common Operations
```python
# Data access
value = data.get("field", default)

# Math
total = sum([item["amount"] for item in items])
average = total / len(items)
rounded = round(value, 2)

# Strings
upper = text.upper()
lower = text.lower()
contains = "substring" in text

# Lists
filtered = [x for x in items if x["amount"] > 100]
count = len(items)

# Dates
from datetime import datetime
date = datetime.fromisoformat("2025-11-15")

# Always return dict
return {"result": calculated_value}
```

---

## 🔍 Validation Checklist

### Before Saving
- [ ] All nodes have green borders
- [ ] All required fields filled
- [ ] Expressions reference existing nodes
- [ ] Python code has return statement
- [ ] URLs are valid format
- [ ] Conditions have comparison operators

---

## 🚨 Common Errors & Fixes

### "Schema selection is required"
**Fix**: Select a schema in Extraction node config

### "Condition must include operator"
**Fix**: Add comparison operator (>, <, ==, etc.) to If condition

### "Python code must have return statement"
**Fix**: Add `return {...}` at end of Python code

### "Referenced node does not exist"
**Fix**: Check node name in expression matches actual node label

### "Invalid URL format"
**Fix**: Ensure URL starts with http:// or https://

---

## 💾 Save & Load

### Auto-Save
- ✅ Saves every 1 second to localStorage
- ✅ Preserves all nodes, connections, config

### Export
- Click "Export" button
- Downloads `.json` file
- Backup for important workflows

### Import
- Click "Import" button
- Select `.json` file
- Restores complete workflow

### Clear
- Click "Clear" button
- Confirmation required
- Resets canvas completely

---

## 📊 Example: Invoice Approval (Copy-Paste)

### Goal
Route invoices based on amount threshold.

### Nodes
1. **HttpTrigger** → `InvoiceWebhook`
2. **Extraction** → `ExtractInvoice`
   - Schema: `invoice_schema_v1`
3. **Python** → `CalculateTax`
```python
total = data.get("total", 0)
tax = total * 0.08
return {"grand_total": round(total + tax, 2)}
```
4. **If** → `CheckAmount`
   - Condition: `{{$("CalculateTax").data.grand_total}} > 1000`
5. **HTTP Request** (True) → `ApprovalAPI`
   - URL: `https://api.example.com/invoices/approval`
6. **HTTP Request** (False) → `AutoProcess`
   - URL: `https://api.example.com/invoices/auto`

### Time: 10 minutes

---

## 🎓 Learning Path

### Beginner (30 min)
1. ✅ Create simple Trigger → Extraction → HTTP Request
2. ✅ Use Expression Builder to insert field
3. ✅ Export and import workflow

### Intermediate (1 hour)
1. ✅ Add If node with condition
2. ✅ Write Python transformation
3. ✅ Build complete approval workflow

### Advanced (2 hours)
1. ✅ Multi-condition nested workflow
2. ✅ Error handling with retries
3. ✅ Complex data enrichment pipeline

---

## 📚 Full Documentation

### User Guide
[2025-11-15-workflow-builder-user-guide.md](./2025-11-15-workflow-builder-user-guide.md)
- Complete feature reference
- Detailed node documentation
- Tips & best practices

### Architecture
[2025-11-15-workflow-builder-architecture.md](../architecture/2025-11-15-workflow-builder-architecture.md)
- Technical implementation
- State management
- Performance optimizations

### Examples
[2025-11-15-workflow-examples.md](./2025-11-15-workflow-examples.md)
- 7 real-world use cases
- Step-by-step configurations
- Expected outputs

### Expression Syntax
[EXPRESSION_SYNTAX.md](../../frontend/EXPRESSION_SYNTAX.md)
- Complete syntax reference
- Advanced patterns
- Troubleshooting

---

## 🆘 Need Help?

### Check These First
1. ✅ Node validation errors (red border)
2. ✅ Expression preview (below input)
3. ✅ Browser console for errors

### Common Questions

**Q: How do I reference a previous node?**
A: Use `{{$("NodeName").data.field}}` syntax

**Q: Can I have multiple If nodes?**
A: Yes! Chain them for complex logic

**Q: Where is data saved?**
A: localStorage (browser only, Phase 1)

**Q: How do I test my workflow?**
A: Check expression previews and validation

**Q: Can I share workflows?**
A: Export to JSON, share file (Phase 2: backend storage)

---

**Last Updated**: 2025-11-15
**Version**: 1.0
**Feedback**: GitHub Issues
