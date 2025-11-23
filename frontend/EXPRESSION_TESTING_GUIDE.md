# Expression Syntax Testing Guide

Step-by-step testing instructions for the expression syntax feature.

## Prerequisites

1. Development server running: `npm run dev`
2. Browser with dev tools open
3. Clean browser state (clear localStorage if needed)

## Test Suite 1: Basic Expression Insertion

### Test 1.1: Manual Expression Entry

**Steps:**
1. Navigate to `/workflow`
2. Add HttpTrigger node (drag from toolbar)
3. Add HttpRequest node
4. Connect HttpTrigger → HttpRequest
5. Click on HttpRequest node
6. In URL field, type: `{{$("HttpTrigger").data.callback_url}}`
7. Observe the preview box appears

**Expected:**
- ✅ URL field accepts the expression
- ✅ Preview shows: `https://example.com/webhook/callback`
- ✅ No validation errors
- ✅ Node border turns green (valid state)

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 1.2: Expression Builder Usage

**Steps:**
1. Continue from Test 1.1
2. Clear the URL field
3. Click "Insert Expression" button
4. Popover opens with available nodes
5. Click on "HttpTrigger" to expand
6. Click on "data" to expand
7. Click on "callback_url"

**Expected:**
- ✅ Popover opens with "HttpTrigger" listed
- ✅ Tree structure expands on click
- ✅ Expression `{{$("HttpTrigger").data.callback_url}}` inserted
- ✅ Popover closes automatically
- ✅ Preview appears

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 1.3: Multiple Expressions

**Steps:**
1. Add Extraction node between HttpTrigger and HttpRequest
2. Configure Extraction (select schema)
3. Click HttpRequest node
4. In URL field, enter:
   ```
   {{$("HttpTrigger").data.callback_url}}?invoice={{$("Extraction").data.invoice_number}}
   ```

**Expected:**
- ✅ Both expressions resolve correctly
- ✅ Preview shows: `https://example.com/webhook/callback?invoice=INV-2024-001`
- ✅ No validation errors

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

## Test Suite 2: Validation

### Test 2.1: Non-Existent Node

**Steps:**
1. In HttpRequest URL field, type: `{{$("NonExistent").data.field}}`
2. Observe validation error

**Expected:**
- ✅ Red error message appears
- ✅ Message: "Referenced node "NonExistent" does not exist"
- ✅ Node border turns red (invalid state)
- ✅ Error appears in validation errors section

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 2.2: Syntax Error

**Steps:**
1. In URL field, type: `{{$("HttpTrigger".data.field}}`
   (Missing closing parenthesis)
2. Observe validation

**Expected:**
- ✅ Validation error appears
- ✅ Clear error message about syntax
- ✅ Node marked as invalid

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 2.3: Node Rename Validation

**Steps:**
1. Create valid expression referencing "HttpTrigger"
2. Click on HttpTrigger node
3. Rename it to "Webhook"
4. Click on HttpRequest node again

**Expected:**
- ✅ HttpRequest shows validation error
- ✅ Error: "Referenced node "HttpTrigger" does not exist"
- ✅ Node marked as invalid

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

## Test Suite 3: Expression Builder UI

### Test 3.1: Tree Expansion

**Steps:**
1. Open expression builder
2. Expand "Extraction" node
3. Verify nested structure displays correctly

**Expected:**
- ✅ "data" field appears
- ✅ Child fields (invoice_number, total, date, vendor, items) appear
- ✅ Expand/collapse icons work
- ✅ Nested items array shows structure

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 3.2: Copy to Clipboard

**Steps:**
1. Open expression builder
2. Expand "HttpTrigger" → "data"
3. Hover over "callback_url"
4. Click copy icon
5. Paste into a text editor

**Expected:**
- ✅ Copy icon appears on hover
- ✅ Icon changes to checkmark after click
- ✅ Clipboard contains: `{{$("HttpTrigger").data.callback_url}}`
- ✅ Checkmark reverts to copy icon after 2 seconds

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 3.3: Available Nodes Filter

**Steps:**
1. Create workflow: HttpTrigger → HttpRequest1 → HttpRequest2
2. Click on HttpRequest1
3. Open expression builder
4. Note available nodes

**Expected:**
- ✅ Only "HttpTrigger" appears (previous node)
- ✅ "HttpRequest2" does NOT appear (subsequent node)

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

## Test Suite 4: Header Support

### Test 4.1: Header with Expression

**Steps:**
1. In HttpRequest node config
2. Add header with key: `Authorization`
3. In value field, type: `Bearer {{$("HttpTrigger").data.api_token}}`
4. Click "Add Header"

**Expected:**
- ✅ Header is added to list
- ✅ Expression is visible in header value
- ✅ No validation errors

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 4.2: Header Expression Builder

**Steps:**
1. Start adding new header
2. Enter key: `X-Invoice-ID`
3. Click "Insert Expression" button next to value field
4. Select expression from builder

**Expected:**
- ✅ Expression builder opens for header value
- ✅ Expression is inserted into value field
- ✅ Can add header with expression

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

## Test Suite 5: Extraction Node Prompt

### Test 5.1: Prompt with Expression

**Steps:**
1. Click on Extraction node
2. In Prompt field, type:
   ```
   Extract invoice data. Send results to {{$("HttpTrigger").data.callback_url}}
   ```
3. Observe preview

**Expected:**
- ✅ Expression resolves in preview
- ✅ Preview shows full prompt with resolved URL
- ✅ No validation errors

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 5.2: Prompt Expression Builder

**Steps:**
1. Clear prompt field
2. Click "Insert Expression" button
3. Select expression from builder

**Expected:**
- ✅ Expression builder opens
- ✅ Only "HttpTrigger" available (previous node)
- ✅ Expression inserts into prompt field
- ✅ Preview updates

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

## Test Suite 6: Edge Cases

### Test 6.1: Empty Expression

**Steps:**
1. Type: `{{}}`
2. Observe behavior

**Expected:**
- ✅ No crash
- ✅ Treated as invalid or ignored
- ✅ Appropriate error message

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 6.2: Nested Field Access

**Steps:**
1. Use expression: `{{$("PythonRunner").data.result.total_with_tax}}`
2. Verify resolution

**Expected:**
- ✅ Nested field resolves correctly
- ✅ Preview shows: `1375.55`
- ✅ No errors

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 6.3: Array in Data

**Steps:**
1. Use expression: `{{$("Extraction").data.items}}`
2. Observe preview

**Expected:**
- ✅ Array is stringified in preview
- ✅ Shows: `[{"description":"Product A",...},...]`
- ✅ No crash

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

## Test Suite 7: Performance

### Test 7.1: Large Workflow

**Steps:**
1. Create workflow with 10 nodes
2. Add expressions in multiple nodes
3. Observe performance

**Expected:**
- ✅ No lag when typing
- ✅ Preview updates quickly (<500ms)
- ✅ Expression builder opens quickly
- ✅ No memory leaks (check DevTools)

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 7.2: Rapid Typing

**Steps:**
1. Type expression quickly in URL field
2. Observe validation and preview

**Expected:**
- ✅ Validation debounced (doesn't run on every keystroke)
- ✅ Preview updates smoothly
- ✅ No errors in console

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

## Test Suite 8: Integration

### Test 8.1: Workflow Save/Load

**Steps:**
1. Create workflow with expressions
2. Save workflow (automatic)
3. Refresh page
4. Verify workflow loads

**Expected:**
- ✅ Expressions preserved in URL fields
- ✅ Expressions preserved in header values
- ✅ Expressions preserved in prompts
- ✅ Validation state correct after load
- ✅ Preview shows correct values

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

### Test 8.2: Workflow Export/Import

**Steps:**
1. Create workflow with expressions
2. Export workflow (JSON)
3. Clear workflow
4. Import exported JSON
5. Verify expressions intact

**Expected:**
- ✅ Expressions in exported JSON
- ✅ Expressions work after import
- ✅ Validation passes
- ✅ Previews show correct values

**Actual:**
- [ ] Pass
- [ ] Fail - Details: ___________

---

## Test Suite 9: Browser Compatibility

### Test 9.1: Chrome

**Browser:** Chrome (latest)
**Steps:** Run all tests above

**Result:**
- [ ] All Pass
- [ ] Some Fail - Details: ___________

---

### Test 9.2: Firefox

**Browser:** Firefox (latest)
**Steps:** Run all tests above

**Result:**
- [ ] All Pass
- [ ] Some Fail - Details: ___________

---

### Test 9.3: Safari

**Browser:** Safari (latest)
**Steps:** Run all tests above

**Result:**
- [ ] All Pass
- [ ] Some Fail - Details: ___________

---

## Console Error Check

After completing all tests, check browser console:

**Expected:**
- ✅ No errors
- ✅ No warnings (or only expected warnings)
- ✅ No memory leaks

**Actual:**
- [ ] Clean console
- [ ] Errors found - Details: ___________

---

## Test Results Summary

| Test Suite | Total Tests | Pass | Fail | Notes |
|------------|-------------|------|------|-------|
| 1. Basic Expression | 3 | | | |
| 2. Validation | 3 | | | |
| 3. Expression Builder UI | 3 | | | |
| 4. Header Support | 2 | | | |
| 5. Extraction Prompt | 2 | | | |
| 6. Edge Cases | 3 | | | |
| 7. Performance | 2 | | | |
| 8. Integration | 2 | | | |
| 9. Browser Compatibility | 3 | | | |
| **Total** | **23** | | | |

---

## Known Issues

Document any issues found during testing:

1. Issue: ___________
   - Severity: [ ] Critical [ ] High [ ] Medium [ ] Low
   - Steps to reproduce: ___________
   - Workaround: ___________

2. Issue: ___________
   - Severity: [ ] Critical [ ] High [ ] Medium [ ] Low
   - Steps to reproduce: ___________
   - Workaround: ___________

---

## Sign-Off

**Tester:** ___________
**Date:** ___________
**Overall Status:** [ ] Pass [ ] Fail [ ] Pass with Issues

**Comments:**
___________________________________________________________________________
___________________________________________________________________________
___________________________________________________________________________

---

**Testing Duration**: ~30-45 minutes
**Automation Potential**: High (most tests can be automated with Playwright)
**Next Steps**: Create Playwright test suite based on this guide
