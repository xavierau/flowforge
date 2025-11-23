# Workflow Builder - Examples & Use Cases

**Date**: 2025-11-15
**Version**: 1.0

## Overview

This guide provides real-world workflow examples and use cases for the Workflow Builder. Each example includes a visual diagram, step-by-step configuration, and implementation notes.

## Table of Contents

1. [Basic Invoice Processing](#example-1-basic-invoice-processing)
2. [Invoice Approval Workflow](#example-2-invoice-approval-workflow)
3. [Receipt Validation & Classification](#example-3-receipt-validation--classification)
4. [Multi-Stage Data Enrichment](#example-4-multi-stage-data-enrichment)
5. [Error Handling & Retry](#example-5-error-handling--retry)
6. [Conditional Routing by Document Type](#example-6-conditional-routing-by-document-type)
7. [Complex Multi-Condition Workflow](#example-7-complex-multi-condition-workflow)

---

## Example 1: Basic Invoice Processing

### Use Case
Extract invoice data and send to accounting system.

### Workflow Diagram
```
HTTP Trigger
     ↓
 Extraction
     ↓
HTTP Request (Send to ERP)
```

### Configuration

#### 1. HTTP Trigger Node
- **Name**: `InvoiceWebhook`
- **Config**: None (accepts webhook data)

#### 2. Extraction Node
- **Name**: `ExtractInvoiceData`
- **Config**:
  - File Source: From trigger
  - Prompt: `Extract invoice number, date, vendor, line items, subtotal, tax, and total amount`
  - Schema: `invoice_schema_v1`

#### 3. HTTP Request Node
- **Name**: `SendToERP`
- **Config**:
  - URL: `https://erp.company.com/api/invoices`
  - Method: POST
  - Headers:
    ```
    Content-Type: application/json
    Authorization: Bearer API_KEY_HERE
    ```

### Expected Data Flow

**HTTP Trigger Output**:
```json
{
  "data": {
    "file_url": "https://storage.example.com/invoice-2025-001.pdf",
    "prompt": "Extract invoice data"
  }
}
```

**Extraction Output**:
```json
{
  "data": {
    "invoice_number": "INV-2025-001",
    "date": "2025-11-15",
    "vendor": {
      "name": "ABC Supplies Inc",
      "address": "123 Main St"
    },
    "line_items": [
      {"description": "Office Supplies", "quantity": 10, "unit_price": 25.00, "amount": 250.00},
      {"description": "Printer Toner", "quantity": 2, "unit_price": 75.00, "amount": 150.00}
    ],
    "subtotal": 400.00,
    "tax": 32.00,
    "total": 432.00
  }
}
```

**HTTP Request Sends**:
All previous node data to ERP system.

### Implementation Time
⏱️ **5 minutes**

---

## Example 2: Invoice Approval Workflow

### Use Case
Route high-value invoices to approval queue, auto-process low-value invoices.

### Workflow Diagram
```
HTTP Trigger
     ↓
 Extraction
     ↓
Python Runner (Calculate tax)
     ↓
    If (Total > $1000?)
     ↓              ↓
   True          False
     ↓              ↓
Approval API  Auto-process API
```

### Configuration

#### 1. HTTP Trigger Node
- **Name**: `InvoiceWebhook`

#### 2. Extraction Node
- **Name**: `ExtractInvoiceData`
- **Config**:
  - Prompt: `Extract invoice number, date, line items, and total`
  - Schema: `invoice_schema_v1`

#### 3. Python Runner Node
- **Name**: `CalculateTax`
- **Config**:
```python
# Get total from extraction
subtotal = data.get("total", 0)
line_items = data.get("line_items", [])

# Calculate tax (8%)
tax_rate = 0.08
tax_amount = subtotal * tax_rate
grand_total = subtotal + tax_amount

# Calculate totals
item_count = len(line_items)
avg_item_value = subtotal / item_count if item_count > 0 else 0

return {
    "subtotal": subtotal,
    "tax_rate": tax_rate,
    "tax_amount": round(tax_amount, 2),
    "grand_total": round(grand_total, 2),
    "item_count": item_count,
    "avg_item_value": round(avg_item_value, 2),
    "requires_approval": grand_total > 1000
}
```

#### 4. If Node
- **Name**: `CheckApprovalRequired`
- **Config**:
  - Condition: `{{$("CalculateTax").data.grand_total}} > 1000`

#### 5. HTTP Request Node (True Path)
- **Name**: `SendToApprovalQueue`
- **Config**:
  - URL: `https://approval.company.com/api/invoices/pending`
  - Method: POST

#### 6. HTTP Request Node (False Path)
- **Name**: `AutoProcessInvoice`
- **Config**:
  - URL: `https://accounting.company.com/api/invoices/auto-process`
  - Method: POST

### Expected Behavior

**If total = $1,250**:
- ✅ Grand total with tax = $1,350
- ✅ Condition evaluates to `true`
- ✅ Routed to approval queue

**If total = $750**:
- ✅ Grand total with tax = $810
- ✅ Condition evaluates to `false`
- ✅ Auto-processed immediately

### Implementation Time
⏱️ **10 minutes**

---

## Example 3: Receipt Validation & Classification

### Use Case
Validate receipt data quality and classify by type (meal, transportation, supplies).

### Workflow Diagram
```
HTTP Trigger
     ↓
 Extraction
     ↓
Python Runner (Validate & Classify)
     ↓
If (Valid?)
     ↓              ↓
   Valid        Invalid
     ↓              ↓
If (Type?)     Error Webhook
├─ Meal
├─ Transport
└─ Supplies
```

### Configuration

#### Python Runner - Validation & Classification
```python
# Get receipt data
merchant = data.get("merchant", "")
amount = data.get("amount", 0)
date = data.get("date", "")
category = data.get("category", "").lower()

# Validation
is_valid = True
errors = []

if not merchant or len(merchant) < 2:
    is_valid = False
    errors.append("Invalid merchant name")

if amount <= 0 or amount > 10000:
    is_valid = False
    errors.append("Amount out of range")

if not date:
    is_valid = False
    errors.append("Date missing")

# Classification
receipt_type = "unknown"
meal_keywords = ["restaurant", "cafe", "food", "dining"]
transport_keywords = ["uber", "lyft", "taxi", "gas", "parking"]
supplies_keywords = ["office", "supplies", "depot", "staples"]

if any(kw in merchant.lower() for kw in meal_keywords) or category == "meals":
    receipt_type = "meal"
elif any(kw in merchant.lower() for kw in transport_keywords) or category == "transport":
    receipt_type = "transportation"
elif any(kw in merchant.lower() for kw in supplies_keywords) or category == "supplies":
    receipt_type = "supplies"

return {
    "is_valid": is_valid,
    "validation_errors": errors,
    "receipt_type": receipt_type,
    "merchant": merchant,
    "amount": amount,
    "date": date
}
```

#### If Node - Validity Check
- **Condition**: `{{$("ValidateReceipt").data.is_valid}} == true`

#### If Node - Type Classification
- **Condition**: `{{$("ValidateReceipt").data.receipt_type}} == "meal"`
- (Add similar nodes for transportation and supplies)

### Expected Outputs

**Valid Meal Receipt**:
```json
{
  "is_valid": true,
  "validation_errors": [],
  "receipt_type": "meal",
  "merchant": "Joe's Restaurant",
  "amount": 45.50,
  "date": "2025-11-15"
}
```

**Invalid Receipt**:
```json
{
  "is_valid": false,
  "validation_errors": ["Amount out of range", "Invalid merchant name"],
  "receipt_type": "unknown"
}
```

### Implementation Time
⏱️ **15 minutes**

---

## Example 4: Multi-Stage Data Enrichment

### Use Case
Extract invoice data, validate, enrich with vendor lookup, calculate discounts, and send to multiple systems.

### Workflow Diagram
```
HTTP Trigger
     ↓
 Extraction
     ↓
Python (Validate)
     ↓
Python (Vendor Lookup)
     ↓
Python (Calculate Discounts)
     ↓
    If (Discount > 10%?)
     ↓              ↓
   True          False
     ↓              ↓
 Alert System   Process Normal
```

### Configuration

#### Python 1 - Validation
```python
# Basic data validation
invoice_num = data.get("invoice_number", "")
total = data.get("total", 0)
vendor_id = data.get("vendor_id", "")

errors = []
if not invoice_num or len(invoice_num) < 5:
    errors.append("Invalid invoice number")
if total <= 0:
    errors.append("Invalid total")
if not vendor_id:
    errors.append("Missing vendor ID")

return {
    "is_valid": len(errors) == 0,
    "validation_errors": errors,
    "invoice_number": invoice_num,
    "total": total,
    "vendor_id": vendor_id
}
```

#### Python 2 - Vendor Lookup
```python
# Simulate vendor lookup (in real workflow, call API)
vendor_id = data.get("vendor_id", "")

# Mock vendor database
vendor_db = {
    "VND-001": {"name": "ABC Corp", "tier": "platinum", "discount_rate": 0.15},
    "VND-002": {"name": "XYZ Inc", "tier": "gold", "discount_rate": 0.10},
    "VND-003": {"name": "123 LLC", "tier": "silver", "discount_rate": 0.05}
}

vendor_info = vendor_db.get(vendor_id, {
    "name": "Unknown",
    "tier": "standard",
    "discount_rate": 0.0
})

return {
    "vendor_id": vendor_id,
    "vendor_name": vendor_info["name"],
    "vendor_tier": vendor_info["tier"],
    "discount_rate": vendor_info["discount_rate"]
}
```

#### Python 3 - Calculate Discounts
```python
total = data.get("total", 0)
discount_rate = data.get("discount_rate", 0)

discount_amount = total * discount_rate
final_total = total - discount_amount

return {
    "original_total": total,
    "discount_rate": discount_rate,
    "discount_amount": round(discount_amount, 2),
    "final_total": round(final_total, 2),
    "savings_percentage": round(discount_rate * 100, 1)
}
```

### Expected Flow

**Input**: Invoice with vendor_id = "VND-001"

**After Validation**:
```json
{"is_valid": true, "invoice_number": "INV-2025-001", "total": 1000.00}
```

**After Vendor Lookup**:
```json
{"vendor_name": "ABC Corp", "tier": "platinum", "discount_rate": 0.15}
```

**After Discount Calculation**:
```json
{"original_total": 1000.00, "discount_amount": 150.00, "final_total": 850.00}
```

### Implementation Time
⏱️ **20 minutes**

---

## Example 5: Error Handling & Retry

### Use Case
Extract document data with quality checks and retry mechanism.

### Workflow Diagram
```
HTTP Trigger
     ↓
 Extraction
     ↓
Python (Quality Check)
     ↓
If (High Quality?)
     ↓              ↓
   Yes            No
     ↓              ↓
  Process      If (Retry Count < 3?)
                    ↓              ↓
                  Yes            No
                    ↓              ↓
              Re-extract    Manual Review
```

### Configuration

#### Python - Quality Check
```python
# Check extraction quality
confidence = data.get("confidence", 0)
field_count = len(data.keys())
required_fields = ["invoice_number", "date", "total", "vendor"]
missing_fields = [f for f in required_fields if f not in data]

# Quality metrics
is_high_quality = (
    confidence >= 0.85 and
    field_count >= 5 and
    len(missing_fields) == 0
)

retry_count = data.get("retry_count", 0)

return {
    "is_high_quality": is_high_quality,
    "confidence": confidence,
    "field_count": field_count,
    "missing_fields": missing_fields,
    "retry_count": retry_count,
    "can_retry": retry_count < 3
}
```

#### If Node 1 - Quality Check
- **Condition**: `{{$("QualityCheck").data.is_high_quality}} == true`

#### If Node 2 - Retry Check
- **Condition**: `{{$("QualityCheck").data.can_retry}} == true`

### Expected Behavior

**High Quality (confidence = 0.92)**:
- ✅ Passes quality check
- ✅ Proceeds to processing

**Low Quality, First Attempt (confidence = 0.65, retry_count = 0)**:
- ❌ Fails quality check
- ✅ Retry count < 3
- 🔄 Triggers re-extraction

**Low Quality, Third Attempt (confidence = 0.70, retry_count = 3)**:
- ❌ Fails quality check
- ❌ Retry count = 3
- 👤 Sends to manual review

### Implementation Time
⏱️ **15 minutes**

---

## Example 6: Conditional Routing by Document Type

### Use Case
Classify document type and route to appropriate processing pipeline.

### Workflow Diagram
```
HTTP Trigger
     ↓
 Extraction (Classify)
     ↓
Python (Parse Type)
     ↓
If (Invoice?)
├─ Yes → Invoice Pipeline
└─ No → If (Receipt?)
        ├─ Yes → Receipt Pipeline
        └─ No → If (Contract?)
                ├─ Yes → Contract Pipeline
                └─ No → Unknown Handler
```

### Configuration

#### Extraction - Document Classification
- **Prompt**: `Classify this document as invoice, receipt, contract, or other. Extract document type and key identifying features.`

#### Python - Parse Classification
```python
doc_type = data.get("document_type", "unknown").lower()
confidence = data.get("confidence", 0)

# Normalize type
if "invoice" in doc_type:
    normalized_type = "invoice"
elif "receipt" in doc_type:
    normalized_type = "receipt"
elif "contract" in doc_type or "agreement" in doc_type:
    normalized_type = "contract"
else:
    normalized_type = "unknown"

return {
    "document_type": normalized_type,
    "original_type": doc_type,
    "confidence": confidence,
    "is_invoice": normalized_type == "invoice",
    "is_receipt": normalized_type == "receipt",
    "is_contract": normalized_type == "contract"
}
```

#### Conditional Chain
1. **If Invoice**: `{{$("ParseType").data.is_invoice}} == true`
2. **If Receipt**: `{{$("ParseType").data.is_receipt}} == true`
3. **If Contract**: `{{$("ParseType").data.is_contract}} == true`

### Routing Table

| Document Type | Pipeline | Endpoint |
|---------------|----------|----------|
| Invoice | Accounts Payable | `/api/invoices/process` |
| Receipt | Expense Management | `/api/expenses/process` |
| Contract | Legal Review | `/api/contracts/process` |
| Unknown | Manual Classification | `/api/documents/classify` |

### Implementation Time
⏱️ **20 minutes**

---

## Example 7: Complex Multi-Condition Workflow

### Use Case
Process invoices with complex routing based on amount, vendor tier, and urgency.

### Workflow Diagram
```
HTTP Trigger
     ↓
 Extraction
     ↓
Python (Enrich Data)
     ↓
If (Amount > $5000?)
├─ Yes → If (Vendor Tier = Premium?)
│        ├─ Yes → Priority Processing
│        └─ No → Standard High-Value
└─ No → If (Urgent?)
         ├─ Yes → Expedited Processing
         └─ No → Standard Processing
```

### Configuration

#### Python - Data Enrichment
```python
# Extract and enrich
amount = data.get("total", 0)
vendor_id = data.get("vendor_id", "")
due_date = data.get("due_date", "")
submission_date = data.get("submission_date", "")

# Vendor lookup
vendor_tiers = {
    "VND-001": "premium",
    "VND-002": "standard",
    "VND-003": "standard"
}
vendor_tier = vendor_tiers.get(vendor_id, "standard")

# Urgency calculation (simple date diff)
from datetime import datetime
try:
    due = datetime.fromisoformat(due_date)
    submitted = datetime.fromisoformat(submission_date)
    days_until_due = (due - submitted).days
    is_urgent = days_until_due <= 3
except:
    is_urgent = False
    days_until_due = 999

return {
    "amount": amount,
    "vendor_id": vendor_id,
    "vendor_tier": vendor_tier,
    "is_premium_vendor": vendor_tier == "premium",
    "is_urgent": is_urgent,
    "days_until_due": days_until_due,
    "is_high_value": amount > 5000
}
```

#### Conditional Logic

1. **First Split - Amount**
   - Condition: `{{$("EnrichData").data.amount}} > 5000`

2. **High Value Branch - Vendor Tier**
   - Condition: `{{$("EnrichData").data.is_premium_vendor}} == true`

3. **Low Value Branch - Urgency**
   - Condition: `{{$("EnrichData").data.is_urgent}} == true`

### Routing Matrix

| Amount | Vendor Tier | Urgency | Destination |
|--------|-------------|---------|-------------|
| > $5000 | Premium | Any | Priority Processing |
| > $5000 | Standard | Any | Standard High-Value |
| ≤ $5000 | Any | Urgent | Expedited Processing |
| ≤ $5000 | Any | Normal | Standard Processing |

### Expected Behavior Examples

**Example 1**: Amount = $6000, Vendor = Premium, Days = 10
- ✅ High value path
- ✅ Premium vendor
- 🎯 **Priority Processing**

**Example 2**: Amount = $6000, Vendor = Standard, Days = 2
- ✅ High value path
- ❌ Not premium
- 🎯 **Standard High-Value**

**Example 3**: Amount = $500, Vendor = Standard, Days = 2
- ❌ Not high value
- ✅ Urgent (≤3 days)
- 🎯 **Expedited Processing**

**Example 4**: Amount = $500, Vendor = Standard, Days = 10
- ❌ Not high value
- ❌ Not urgent
- 🎯 **Standard Processing**

### Implementation Time
⏱️ **25 minutes**

---

## Tips for Building Complex Workflows

### 1. Start Simple, Add Complexity Gradually
- ✅ Build basic path first
- ✅ Test thoroughly
- ✅ Add conditional branches incrementally

### 2. Use Descriptive Node Names
```
❌ Bad:  "Extraction", "Python", "If"
✅ Good: "ExtractInvoiceData", "CalculateTax", "CheckHighValue"
```

### 3. Document Your Logic
Add comments in Python nodes:
```python
# Calculate tax at 8% rate
tax_rate = 0.08
tax_amount = subtotal * tax_rate

# Round to 2 decimal places for currency
return {"tax": round(tax_amount, 2)}
```

### 4. Test Each Branch
- ✅ Test True path with valid data
- ✅ Test False path with invalid data
- ✅ Test edge cases (null, zero, empty)

### 5. Handle Missing Data Gracefully
```python
# ✅ Good: Use .get() with defaults
amount = data.get("total", 0)
items = data.get("line_items", [])

# ❌ Bad: Direct access can fail
amount = data["total"]  # KeyError if missing
```

### 6. Use Expression Builder
- ✅ Prevents typos in node names
- ✅ Shows available fields
- ✅ Validates expressions

### 7. Monitor Validation Status
- 🟢 Green border = Ready
- 🔴 Red border = Errors
- ⚪ Gray border = Not configured

---

## Common Patterns Summary

| Pattern | Use Case | Complexity |
|---------|----------|------------|
| Linear Pipeline | Simple extraction → process | ⭐ Easy |
| Single Condition | High/low value routing | ⭐⭐ Medium |
| Multi-Stage Transform | Enrich → validate → format | ⭐⭐ Medium |
| Nested Conditions | Complex routing logic | ⭐⭐⭐ Advanced |
| Error Handling | Retry with fallback | ⭐⭐⭐ Advanced |
| Type Classification | Route by document type | ⭐⭐⭐ Advanced |

---

## Next Steps

- 📖 [User Guide](./2025-11-15-workflow-builder-user-guide.md) - Complete feature reference
- 🏗️ [Architecture Guide](../architecture/2025-11-15-workflow-builder-architecture.md) - Technical details
- 📝 [Expression Syntax](../../frontend/EXPRESSION_SYNTAX.md) - Expression reference

---

**Last Updated**: 2025-11-15
**Version**: 1.0
**Need Help?**: Refer to the User Guide or report issues via GitHub
