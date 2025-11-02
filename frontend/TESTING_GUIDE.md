# JSON Schema Builder - Testing Guide

**Application URL:** http://localhost:3002/
**Status:** ✅ Running
**Last Updated:** 2025-11-02

---

## 🎯 Core Features to Test

### 1. Create Schema from Scratch

**Steps:**
1. Open http://localhost:3002/
2. Click the **"Add Property"** button in the left panel
3. In the dialog:
   - Name: `email`
   - Type: `string`
   - Description: `User's email address`
   - Required: ✓ (toggle on)
   - Format: `email`
4. Click **"Add Property"**

**Expected Result:**
- Property appears in the tree with blue "string" badge and red "Required" badge
- Right panel shows the schema JSON updating in real-time
- Sample data tab shows `"email": "example@email.com"`

---

### 2. Add Nested Properties (Objects)

**Steps:**
1. Create a root property:
   - Name: `address`
   - Type: `object`
   - Required: ✓
2. Click **Save**
3. Hover over the `address` property
4. Click the **➕ (Plus)** icon to add a child property
5. Add child property:
   - Name: `street`
   - Type: `string`
   - Required: ✓
6. Repeat to add `city`, `state`, `zip`

**Expected Result:**
- `address` property has expand/collapse chevron
- Nested properties are indented
- Different colored left border (blue for level 1)
- JSON preview shows nested structure:
  ```json
  {
    "address": {
      "type": "object",
      "properties": {
        "street": { "type": "string" },
        ...
      }
    }
  }
  ```

---

### 3. Add Array Properties

**Steps:**
1. Add root property:
   - Name: `phone_numbers`
   - Type: `array`
   - Min Items: `1`
   - Max Items: `5`
2. Click the ➕ icon on `phone_numbers`
3. Note: For arrays, the child is automatically named `items`
4. Edit the items schema:
   - Type: `string`
   - Format: none

**Expected Result:**
- Array property with pink "array" badge
- Items schema nested underneath
- Sample data shows: `"phone_numbers": ["Sample items"]`

---

### 4. Test 3-Level Nesting Limit

**Steps:**
1. Create: `root_object` (object) → `level_1` (object) → `level_2` (object) → `level_3` (string)
2. Try to add a child to `level_3`

**Expected Result:**
- Alert: "Maximum nesting depth (3 levels) reached"
- Cannot add level 4 properties
- Visual indicators: different colored borders for each level

---

### 5. Edit Property Constraints

**Steps:**
1. Create a `price` property (number type)
2. Click the ✏️ (edit) icon
3. Set constraints:
   - Minimum: `0`
   - Maximum: `10000`
   - Multiple Of: `0.01`
4. Save

**Expected Result:**
- Schema JSON shows all constraints
- Property editor reopens with saved values

---

### 6. Load Invoice Template

**Steps:**
1. Click **"Load Template"** button in header
2. Select **"Invoice Schema"** card
3. Confirm the replacement dialog

**Expected Result:**
- Left panel fills with invoice structure:
  - invoice_number (string)
  - invoice_date (string, date format)
  - vendor (object with nested properties)
  - customer (object)
  - line_items (array with complex items)
  - totals (numbers with constraints)
- Right panel shows complete invoice JSON schema
- Sample data shows realistic invoice structure

---

### 7. Load Resume Template

**Steps:**
1. Click **"Load Template"**
2. Select **"Resume/CV Schema"**
3. Confirm replacement

**Expected Result:**
- Schema loads with:
  - personal_info (object)
  - work_experience (array of objects)
  - education (array)
  - skills (object)
- All nested properly with 2-3 levels

---

### 8. Export Schema

**Steps:**
1. Load the invoice template (or create properties)
2. Click **"Export Schema"** button in header
3. Check Downloads folder

**Expected Result:**
- File downloads: `invoice_schema_schema.json`
- File contains valid JSON Schema (Draft 07)
- Can be opened and validated

---

### 9. Real-time Preview

**Steps:**
1. Open both preview tabs: "JSON Schema" and "Sample Data"
2. Add a new property
3. Watch both tabs

**Expected Result:**
- Both tabs update immediately
- No page refresh needed
- JSON viewer syntax highlighting works

---

### 10. Delete Properties

**Steps:**
1. Load invoice template
2. Hover over `discount` property
3. Click 🗑️ (trash) icon
4. Confirm deletion

**Expected Result:**
- Property removed from tree
- JSON preview updates
- If property had children, all are removed

---

## 🎨 Visual Features to Verify

### Type Color Coding
- String: Blue badge
- Number: Green badge
- Boolean: Purple badge
- Object: Orange badge
- Array: Pink badge

### Level Indicators
- Level 0: Primary blue left border
- Level 1: Blue left border
- Level 2: Green left border
- Level 3: Orange left border

### Interactive States
- **Hover**: Properties highlight with gray background
- **Expanded**: Chevron points down, children visible
- **Collapsed**: Chevron points right, children hidden
- **Actions visible on hover**: Edit, Delete, Add Child buttons appear

---

## 🔧 Property Editor Features to Test

### String Type
- ✅ Format dropdown (email, URI, date, date-time, UUID)
- ✅ Pattern (regex validation)
- ✅ Min/Max length
- ✅ Default value

### Number Type
- ✅ Minimum value
- ✅ Maximum value
- ✅ Multiple of (for decimals)
- ✅ Default value

### Array Type
- ✅ Min items
- ✅ Max items
- ✅ Unique items toggle
- ✅ Items schema editing

### Object Type
- ✅ Add child properties
- ✅ Nested objects up to 3 levels

### All Types
- ✅ Name (property key)
- ✅ Description
- ✅ Required toggle

---

## 🐛 Edge Cases to Test

### 1. Empty Schema
- Starting state with no properties
- "No properties yet" message displays
- Export button is disabled

### 2. Special Characters in Names
- Try property name: `user_name` (valid)
- Try property name: `user-name` (valid)
- Try property name: `user name` (with space - technically valid in JSON)

### 3. Deeply Nested Arrays
```
root_array (array)
  └─ items (object)
      └─ nested_array (array)
          └─ items (string)
```
Should work (3 levels total)

### 4. Rapid Editing
- Add property → immediately edit → save
- Verify no race conditions

### 5. Template Switching
- Load Invoice → Load Resume → Load Invoice again
- Verify clean replacement each time

---

## ✅ Success Criteria Checklist

- [ ] Can create properties from scratch
- [ ] Can edit all property types
- [ ] Can add nested properties (objects & arrays)
- [ ] 3-level nesting enforced
- [ ] Tree expand/collapse works
- [ ] Delete confirmation works
- [ ] Invoice template loads correctly
- [ ] Resume template loads correctly
- [ ] Export downloads valid JSON
- [ ] JSON preview updates in real-time
- [ ] Sample data generates correctly
- [ ] All type colors display properly
- [ ] Level indicators show correct colors
- [ ] Required badges display
- [ ] All constraint inputs work
- [ ] Format dropdown populates
- [ ] No console errors in browser

---

## 🌐 Browser Testing

Test in:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if on Mac)

Check:
- [ ] Layout renders correctly
- [ ] Dialogs open/close smoothly
- [ ] Buttons respond to clicks
- [ ] File download works

---

## 📱 Responsive Testing (Future)

Current design is optimized for desktop (2-column layout).

For future mobile support, test:
- [ ] Panels stack vertically
- [ ] Touch interactions work
- [ ] Dialogs fit on screen

---

## 🔍 Developer Console

Open browser DevTools (F12) and check:

### Console Tab
- [ ] No error messages
- [ ] No warning messages about React

### Network Tab
- [ ] Initial load is fast
- [ ] HMR (Hot Module Replacement) works during development

### React DevTools (if installed)
- [ ] Zustand store state updates correctly
- [ ] No unnecessary re-renders

---

## 🎓 User Workflow Examples

### Example 1: Create a Product Schema
```
1. Add Property: "name" (string, required)
2. Add Property: "price" (number, required, min: 0)
3. Add Property: "description" (string)
4. Add Property: "categories" (array, min items: 1)
   - Edit items: type = string
5. Export schema
```

### Example 2: Customize Invoice Template
```
1. Load "Invoice Schema"
2. Delete "discount" property (if not needed)
3. Add "tax_id" to vendor (string, required)
4. Edit "currency" pattern to limit to specific codes
5. Export customized schema
```

---

## 🚨 Known Limitations

1. **No validation in editor**: Invalid regex patterns not validated until schema use
2. **No undo/redo**: Changes are immediate
3. **No schema import**: Can only load pre-defined templates
4. **No backend persistence**: Data lost on page refresh
5. **Desktop-only layout**: Not optimized for mobile (future enhancement)

---

## 📊 Performance Benchmarks

Expected performance:
- [ ] Initial load: < 2 seconds
- [ ] Add property: < 100ms
- [ ] Edit property: Dialog opens instantly
- [ ] JSON preview update: < 50ms
- [ ] Export: Instant download

---

## 🎉 Ready for Demo!

The application is fully functional and ready to demonstrate all MVP features. Open http://localhost:3002/ in your browser and start building JSON schemas!
