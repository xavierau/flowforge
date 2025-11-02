# JSON Schema Builder - Accessibility Checklist

**Version:** 1.0
**Last Updated:** 2025-11-02
**Compliance Target:** WCAG 2.1 Level AA

---

## Overview

This checklist ensures the JSON Schema Builder meets accessibility standards for users with disabilities. Use this during development, code review, and QA testing.

---

## 1. Keyboard Navigation

### Global Navigation

- [ ] **Tab Order:** Logical tab sequence (left to right, top to bottom)
  - Header → Schema name input → Tree panel → Preview panel
  - Test: Navigate entire app with Tab key only

- [ ] **Focus Indicators:** Visible focus outline on all interactive elements
  - Minimum: 2px outline, high contrast color
  - Test: Tab through all elements, verify focus is always visible

- [ ] **Skip Links:** (Optional) "Skip to main content" for keyboard users
  - Test: First Tab should reveal skip link

### Tree-Specific Navigation

- [ ] **Arrow Keys:** Navigate between tree nodes
  - ↑/↓: Previous/Next node
  - →: Expand collapsed node or move to first child
  - ←: Collapse expanded node or move to parent
  - Test: Navigate tree without using mouse

- [ ] **Enter:** Activate selected node (open edit dialog)
  - Test: Select node with arrows, press Enter

- [ ] **Space:** Toggle checkbox or switch
  - Test: Focus "Required" switch, press Space

- [ ] **Delete:** Delete selected node (after confirmation)
  - Test: Select node, press Delete, confirm

- [ ] **Escape:** Close dialogs/dropdowns
  - Test: Open dialog, press Escape

### Keyboard Shortcuts

- [ ] **Ctrl/Cmd + S:** Save schema
  - Test: Make changes, press shortcut

- [ ] **Ctrl/Cmd + N:** Add new property (if implemented)
  - Test: Press shortcut, verify dialog opens

- [ ] **Ctrl/Cmd + Z:** Undo (if implemented)
  - Test: Make change, undo with shortcut

- [ ] **No Keyboard Traps:** Can escape all UI components
  - Test: Enter all dialogs/menus, verify can exit with Esc or Tab

---

## 2. Screen Reader Support

### ARIA Landmarks

- [ ] **Header:** `<header role="banner">`
  - Test with screen reader: Should announce "banner" region

- [ ] **Main Content:** `<main role="main">`
  - Test: Should announce "main" region

- [ ] **Tree:** `role="tree"` on container
  - Test: Should announce "tree" with item count

### Tree ARIA Attributes

- [ ] **Tree Items:** Each node has correct ARIA attributes
  ```html
  <div
    role="treeitem"
    aria-expanded="true"  <!-- for expandable nodes -->
    aria-level="2"        <!-- nesting level -->
    aria-setsize="5"      <!-- total siblings -->
    aria-posinset="3"     <!-- position in siblings -->
    tabIndex={isSelected ? 0 : -1}
  >
  ```
  - Test: Navigate tree with screen reader, verify announcements

- [ ] **Expanded/Collapsed State:** Announced correctly
  - Test: Expand/collapse node, verify "expanded" or "collapsed" announced

### Form Labels

- [ ] **All Inputs Labeled:** Every form field has associated label
  ```tsx
  <Label htmlFor="propertyName">Property Name</Label>
  <Input id="propertyName" />
  ```
  - Test: Focus input, verify label is read

- [ ] **Required Fields:** Indicated with `aria-required="true"`
  - Test: Focus required field, verify "required" announced

- [ ] **Error Messages:** Associated with inputs
  ```tsx
  <Input
    aria-invalid={hasError}
    aria-describedby={hasError ? "name-error" : undefined}
  />
  <p id="name-error" role="alert">{errorMessage}</p>
  ```
  - Test: Trigger validation error, verify error message read

### Live Regions

- [ ] **Status Updates:** Schema validation status announced
  ```tsx
  <div role="status" aria-live="polite" aria-atomic="true">
    Schema is valid
  </div>
  ```
  - Test: Make change, verify status update announced

- [ ] **Toast Notifications:** Use `role="alert"` for important messages
  - Test: Trigger save, verify success message announced

### Button Labels

- [ ] **Icon Buttons:** All have accessible labels
  ```tsx
  <Button aria-label="Edit property">
    <Pencil className="h-4 w-4" />
    <span className="sr-only">Edit property</span>
  </Button>
  ```
  - Test: Focus icon button, verify label read

- [ ] **Disabled State:** Reason for disabled state communicated
  ```tsx
  <Tooltip>
    <TooltipTrigger>
      <Button disabled aria-disabled="true">
        <Plus />
      </Button>
    </TooltipTrigger>
    <TooltipContent>
      Maximum nesting depth reached
    </TooltipContent>
  </Tooltip>
  ```
  - Test: Focus disabled button, verify tooltip read

---

## 3. Color & Contrast

### Text Contrast

- [ ] **Normal Text:** Minimum 4.5:1 contrast ratio
  - Body text on background
  - Muted text on background
  - Test tool: WCAG Color Contrast Checker

- [ ] **Large Text (18px+):** Minimum 3:1 contrast ratio
  - Headings
  - Button text
  - Test tool: WCAG Color Contrast Checker

- [ ] **Error Text:** Sufficient contrast
  - Red error text on white: 3.9:1 (acceptable for large text)
  - Test: Verify error messages are readable

### UI Component Contrast

- [ ] **Borders:** Minimum 3:1 contrast against adjacent colors
  - Button borders
  - Input borders
  - Test: Verify borders visible in both light/dark modes

- [ ] **Focus Indicators:** Minimum 3:1 contrast
  - Focus ring color vs. background
  - Test: Tab through components, verify focus visible

### Color Independence

- [ ] **No Color-Only Information:** Information not conveyed by color alone
  - Required fields: Red asterisk + "Required" badge
  - Validation: Icon + text message (not just red border)
  - Property types: Icon + text badge (not just color)
  - Test: Use grayscale mode, verify all information accessible

- [ ] **Dark Mode Support:** All contrast ratios maintained
  - Test: Switch to dark mode, re-verify contrast

---

## 4. Focus Management

### Dialog Focus

- [ ] **Auto-Focus:** Dialog opens with focus on first interactive element
  - Property Editor: Focus "Property Name" input
  - Test: Open dialog, verify cursor in first field

- [ ] **Focus Trap:** Focus cycles within dialog
  - Tab from last element returns to first
  - Shift+Tab from first returns to last
  - Test: Tab through entire dialog

- [ ] **Focus Return:** Focus returns to trigger after dialog closes
  - Close with Escape or Cancel
  - Test: Open dialog from button, close, verify focus returns

### Tree Focus

- [ ] **Roving TabIndex:** Only one node tabbable at a time
  - Selected node: `tabIndex={0}`
  - Other nodes: `tabIndex={-1}`
  - Test: Tab to tree, only selected node receives focus

- [ ] **Visual Focus:** Selected node has visible indicator
  - Border or background color change
  - Test: Navigate tree with arrows, verify selection visible

---

## 5. Responsive & Zoom Support

### Layout Adaptation

- [ ] **Mobile Responsive:** Usable on small screens (≥320px width)
  - Test: Resize to 320px, verify all content accessible

- [ ] **Tablet Responsive:** Optimized for tablets (768px-1024px)
  - Test: Resize to 768px, verify layout adapts

- [ ] **200% Zoom:** All content and functionality available at 200% zoom
  - Test: Browser zoom to 200%, verify no horizontal scrolling

- [ ] **Text Resize:** Text readable when scaled to 200% (browser settings)
  - Test: Increase browser text size to 200%

### Touch Targets

- [ ] **Minimum Size:** Touch targets ≥44x44px (mobile)
  - Buttons
  - Tree nodes (expand/collapse)
  - Test: Use mobile device, verify all targets tappable

---

## 6. Forms & Validation

### Input Labeling

- [ ] **Visible Labels:** All inputs have visible labels
  - Test: Review all form fields

- [ ] **Placeholder as Enhancement:** Placeholder text supplements, not replaces labels
  - Test: Verify labels present even with placeholders

### Error Prevention

- [ ] **Inline Validation:** Real-time feedback as user types
  - Property name validation
  - Test: Enter invalid name, verify immediate error

- [ ] **Clear Error Messages:** Specific, actionable messages
  - ❌ "Invalid input"
  - ✅ "Property name must start with letter or underscore"
  - Test: Trigger all validation errors, verify clarity

### Error Recovery

- [ ] **Error Identification:** Errors clearly marked
  - Red border + icon + text message
  - Test: Submit invalid form, verify errors visible

- [ ] **Error Association:** Errors linked to inputs (aria-describedby)
  - Test: Focus input with error, verify error message read

- [ ] **Error Focus:** First error receives focus on submit
  - Test: Submit form with errors, verify focus moves to error

---

## 7. Media & Content

### Images

- [ ] **Alt Text:** All images have descriptive alt text
  - Icons: Use aria-label or sr-only text
  - Decorative: `aria-hidden="true"`
  - Test: Review all images

### Icons

- [ ] **Icon + Text:** Icons paired with text labels
  - Toolbar buttons: Icon + visible text
  - Or: Icon + aria-label
  - Test: Verify all icons have labels

### Animations

- [ ] **Reduced Motion:** Respect `prefers-reduced-motion`
  ```css
  @media (prefers-reduced-motion: reduce) {
    * {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```
  - Test: Enable reduced motion, verify animations disabled

---

## 8. Semantic HTML

### Structure

- [ ] **Headings:** Logical heading hierarchy (H1 → H2 → H3)
  - H1: App title
  - H2: Section titles (Tree, Preview)
  - H3: Dialog titles
  - Test: Use heading navigation (screen reader), verify hierarchy

- [ ] **Lists:** Use `<ul>`, `<ol>` for lists
  - Tree nodes could use list semantics
  - Test: Navigate lists with screen reader

- [ ] **Buttons vs Links:** Correct element for action
  - Actions: `<button>`
  - Navigation: `<a>`
  - Test: Review all interactive elements

---

## 9. Testing Checklist

### Automated Testing

- [ ] **Axe DevTools:** Run in browser, fix all violations
  - Install: Chrome/Firefox extension
  - Run on every page/state

- [ ] **Lighthouse Accessibility:** Score ≥90
  - Run: Chrome DevTools → Lighthouse
  - Target: 100 score

- [ ] **ESLint Plugin:** `eslint-plugin-jsx-a11y` configured
  - Catches common ARIA mistakes in development

### Manual Testing

- [ ] **Keyboard-Only Navigation:** Complete all tasks without mouse
  - Create schema
  - Edit properties
  - Delete properties
  - Save/export

- [ ] **Screen Reader Testing:**
  - **Windows:** NVDA (free) or JAWS
  - **Mac:** VoiceOver (built-in)
  - **Test:** Navigate tree, edit properties, hear validation

- [ ] **Zoom Testing:** Test at 100%, 150%, 200% zoom
  - No horizontal scrolling
  - All content visible

- [ ] **Color Blindness:** Use color blindness simulator
  - Chrome extension: "Color Blindness Simulator"
  - Test: Verify information not color-dependent

---

## 10. Documentation

- [ ] **Keyboard Shortcuts:** Documented in app (help menu or tooltip)
  - Test: User can discover shortcuts

- [ ] **Accessibility Statement:** (Optional) Page describing accessibility features
  - Contact for accessibility issues

- [ ] **User Guide:** Includes keyboard navigation instructions
  - Test: Review documentation

---

## Testing Tools

### Browser Extensions

| Tool | Purpose | Link |
|------|---------|------|
| **Axe DevTools** | Automated accessibility testing | [Chrome](https://chrome.google.com/webstore/detail/axe-devtools) |
| **WAVE** | Visual accessibility checker | [Chrome](https://chrome.google.com/webstore/detail/wave) |
| **Lighthouse** | Built-in Chrome DevTools | Press F12 → Lighthouse tab |
| **Color Contrast Analyzer** | WCAG contrast checker | [Chrome](https://chrome.google.com/webstore/detail/color-contrast-analyzer) |

### Screen Readers

| Platform | Screen Reader | Free |
|----------|--------------|------|
| **Windows** | NVDA | ✅ Yes |
| **Windows** | JAWS | ❌ Paid (trial available) |
| **Mac** | VoiceOver | ✅ Built-in (Cmd+F5) |
| **Linux** | Orca | ✅ Yes |
| **Mobile (iOS)** | VoiceOver | ✅ Built-in (Settings → Accessibility) |
| **Mobile (Android)** | TalkBack | ✅ Built-in (Settings → Accessibility) |

### Testing Workflow

1. **Development:** Run Axe DevTools after each feature
2. **Code Review:** Check ARIA attributes and keyboard support
3. **QA:** Complete this checklist before release
4. **User Testing:** Test with real assistive technology users (if possible)

---

## Quick Verification Script

Run this checklist on every major release:

```bash
# 1. Automated tests
npm run test:a11y  # (if implemented)

# 2. Browser DevTools
# - Open Chrome DevTools
# - Run Lighthouse accessibility audit
# - Target: 100 score

# 3. Keyboard navigation
# - Disconnect mouse
# - Navigate entire app with keyboard only
# - Verify all functions accessible

# 4. Screen reader
# - Enable VoiceOver (Mac) or NVDA (Windows)
# - Navigate tree, edit properties
# - Verify meaningful announcements

# 5. Zoom
# - Zoom to 200%
# - Verify no horizontal scrolling
# - Verify all content readable

# 6. Color contrast
# - Run Axe DevTools contrast check
# - Verify all text meets 4.5:1 ratio

# 7. Dark mode
# - Switch to dark mode
# - Re-run contrast checks
# - Verify focus indicators visible
```

---

## Priority Levels

### 🔴 Critical (Block Release)
- Keyboard navigation broken
- Form inputs not labeled
- Color contrast below 3:1
- Keyboard traps
- Missing ARIA on interactive elements

### 🟡 High (Fix Before Release)
- Missing focus indicators
- Unclear error messages
- ARIA attribute errors
- Poor heading hierarchy

### 🟢 Medium (Fix in Next Sprint)
- Suboptimal keyboard shortcuts
- Missing tooltips
- Inconsistent ARIA patterns

---

## Accessibility Champion Checklist

Assign an "Accessibility Champion" for each sprint to verify:

- [ ] All new components have keyboard support
- [ ] All new forms have proper labels and validation
- [ ] All new icons have accessible labels
- [ ] Axe DevTools shows 0 violations
- [ ] Tested with at least one screen reader
- [ ] All interactive elements have focus indicators

---

## Common ARIA Patterns (Quick Reference)

### Button
```tsx
<button aria-label="Delete property">
  <Trash2 />
</button>
```

### Checkbox/Switch
```tsx
<Switch
  id="required"
  aria-checked={isRequired}
  aria-labelledby="required-label"
/>
<Label id="required-label">Required</Label>
```

### Combobox (Select)
```tsx
<Select
  aria-labelledby="type-label"
  aria-expanded={isOpen}
  aria-controls="type-listbox"
>
```

### Dialog
```tsx
<Dialog
  role="dialog"
  aria-labelledby="dialog-title"
  aria-describedby="dialog-description"
  aria-modal="true"
>
```

### Tree
```tsx
<div role="tree" aria-label="Schema properties">
  <div
    role="treeitem"
    aria-level={2}
    aria-expanded={isExpanded}
    aria-setsize={siblings.length}
    aria-posinset={index + 1}
  >
```

---

## Resources

### WCAG Guidelines
- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [WebAIM Articles](https://webaim.org/articles/)

### ARIA Patterns
- [ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/)
- [Tree View Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/treeview/)

### Testing Guides
- [Keyboard Testing Guide](https://webaim.org/articles/keyboard/)
- [Screen Reader Testing](https://webaim.org/articles/screenreader_testing/)

---

**Document Version:** 1.0
**Compliance Target:** WCAG 2.1 Level AA
**Author:** Aura, UI/UX Designer Agent
**Date:** 2025-11-02
