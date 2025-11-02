# JSON Schema Builder - Frontend Documentation

**Complete UI/UX Design System and Implementation Guide**

---

## Overview

This documentation suite provides a comprehensive, developer-ready specification for building the JSON Schema Builder frontend application. The design prioritizes **task efficiency**, **error prevention**, and **accessibility** while maintaining a clean, modern aesthetic aligned with shadcn/ui and Tailwind CSS conventions.

---

## Documentation Structure

### 📘 [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)
**The Complete Design Specification**

**What's Inside:**
- Primary Job-to-be-Done (JTBD) analysis
- Optimal task flow breakdowns
- Layout and information architecture
- Visual hierarchy principles
- Detailed component specifications (15 components)
- Color system and theming
- Typography scale
- Spacing and layout grid
- Iconography mapping
- Accessibility requirements (WCAG 2.1 AA)
- Interaction patterns and micro-animations
- Error prevention strategies
- User flow diagrams

**Use When:**
- Starting implementation
- Making design decisions
- Resolving UI/UX questions
- Onboarding new designers/developers

**Page Count:** ~100 sections

---

### 🛠️ [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
**Code Examples and Practical Patterns**

**What's Inside:**
- Quick start setup instructions
- Complete component implementations (copy-paste ready)
- State management with Zustand (full store example)
- Utility functions (validation, auto-save, keyboard navigation)
- Testing strategies (unit tests, accessibility tests)
- Common pitfalls and solutions

**Use When:**
- Building components
- Implementing state management
- Writing tests
- Debugging issues

**Key Components Included:**
- `SchemaTreeNode.tsx` (fully implemented)
- `PropertyEditor.tsx` (dialog with validation)
- `JSONPreviewPanel.tsx` (real-time preview)
- `StringConstraints.tsx` (constraint editor)
- `schemaStore.ts` (Zustand store)

---

### ✅ [ACCESSIBILITY_CHECKLIST.md](./ACCESSIBILITY_CHECKLIST.md)
**WCAG 2.1 Level AA Compliance Checklist**

**What's Inside:**
- Keyboard navigation requirements (10 sections)
- Screen reader support (ARIA patterns)
- Color and contrast guidelines
- Focus management rules
- Responsive design checklist
- Form and validation accessibility
- Testing tools and workflows
- Priority levels (Critical, High, Medium)

**Use When:**
- Before code review
- During QA testing
- Before release
- Auditing accessibility

**Testing Tools:**
- Axe DevTools
- WAVE
- Lighthouse
- Screen readers (NVDA, VoiceOver)

---

### 🎯 [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
**Print-and-Keep Developer Cheat Sheet**

**What's Inside:**
- Component mapping (UI element → shadcn/ui component)
- Color palette reference
- Spacing scale
- Icon mapping (Lucide React)
- Common Tailwind patterns
- State management snippets
- ARIA patterns (copy-paste)
- Keyboard shortcuts
- Testing commands
- Common mistakes to avoid

**Use When:**
- During daily development
- Looking up quick patterns
- Referencing colors/spacing
- Copying ARIA patterns

**Pro Tip:** Print this page and keep it at your desk!

---

## Getting Started

### For Product Managers
1. Read: [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) sections 1-2 (JTBD and Task Flows)
2. Review: User flow diagrams (section 15)
3. Understand: Primary user goals and task efficiency principles

### For Designers
1. Read: [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) in full
2. Reference: Color system, typography, iconography sections
3. Use: Figma/Sketch to create mockups based on specifications

### For Frontend Developers
1. **Day 1:** Read [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
2. **Day 2:** Skim [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md), focus on component specs (section 5)
3. **Day 3+:** Implement using [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
4. **Before Commit:** Check [ACCESSIBILITY_CHECKLIST.md](./ACCESSIBILITY_CHECKLIST.md)

### For QA Engineers
1. Read: [ACCESSIBILITY_CHECKLIST.md](./ACCESSIBILITY_CHECKLIST.md)
2. Reference: Testing tools and workflows
3. Use: Checklist for pre-release validation

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
**Goal:** Core tree editor with basic CRUD operations

**Tasks:**
1. Set up Zustand store (`schemaStore.ts`)
2. Implement `SchemaTreeNode` component
3. Implement `PropertyEditor` dialog (basic version)
4. Add/edit/delete property functionality
5. Basic validation (property name)

**Deliverables:**
- Can add/edit/delete root-level properties
- Properties display in tree with type icons
- Basic validation prevents invalid names

**Reference:**
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - Component examples
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - State management patterns

---

### Phase 2: Nesting & Constraints (Week 2)
**Goal:** Support nested objects/arrays with constraints

**Tasks:**
1. Implement nesting logic (max 3 levels)
2. Add depth validation and visual indicators
3. Implement constraint editors:
   - `StringConstraints.tsx`
   - `NumberConstraints.tsx`
   - `BooleanConstraints.tsx`
4. Add expand/collapse functionality

**Deliverables:**
- Can add nested properties (max 3 levels)
- Visual depth indicators (background, border)
- Type-specific constraint fields appear/disappear
- Prevent adding children beyond level 3

**Reference:**
- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) - Visual hierarchy (section 4)
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - Depth styling

---

### Phase 3: Preview & Validation (Week 3)
**Goal:** Real-time JSON Schema preview with validation

**Tasks:**
1. Implement `JSONPreviewPanel` component
2. Integrate AJV validation
3. Add syntax highlighting (react-json-view)
4. Display validation errors inline
5. Copy-to-clipboard functionality

**Deliverables:**
- Live JSON Schema updates on every change
- Validation status (valid/invalid) with error messages
- Copy schema to clipboard
- Syntax-highlighted JSON view

**Reference:**
- [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md) - JSONPreviewPanel example
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - Validation pattern

---

### Phase 4: Templates & Persistence (Week 4)
**Goal:** Load templates, save/export schemas

**Tasks:**
1. Implement `TemplateSelector` component
2. Create invoice and resume templates
3. Add save functionality (backend API)
4. Add export (JSON, TypeScript)
5. Add import (upload JSON)

**Deliverables:**
- Can load Invoice/Resume templates
- Can save schema to backend
- Can export as JSON or TypeScript types
- Can import existing JSON schemas

**Reference:**
- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) - Template selector (section 5.6)
- Backend API endpoints (from main project docs)

---

### Phase 5: Polish & Accessibility (Week 5)
**Goal:** Accessibility, keyboard navigation, animations

**Tasks:**
1. Implement keyboard navigation (arrow keys, Enter, Delete)
2. Add ARIA attributes (tree, treeitem, dialog)
3. Add focus indicators and management
4. Implement animations (expand/collapse, fade-in)
5. Add toast notifications
6. Auto-save to localStorage

**Deliverables:**
- Full keyboard navigation (no mouse required)
- WCAG 2.1 AA compliant
- Screen reader tested
- Smooth animations and transitions
- Unsaved work protected (auto-save)

**Reference:**
- [ACCESSIBILITY_CHECKLIST.md](./ACCESSIBILITY_CHECKLIST.md) - Full checklist
- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) - Micro-interactions (section 12)

---

## Design Principles Summary

### 1. Function Over Form
Every design decision is justified by its impact on task efficiency or error reduction. Visual polish enhances function, never replaces it.

### 2. Progressive Disclosure
Advanced features (constraints, nested properties) are hidden until needed. Smart defaults reduce initial cognitive load.

### 3. Error Prevention > Error Correction
Inline validation, visual depth warnings, and disabled buttons prevent errors before they occur.

### 4. Immediate Feedback
Real-time JSON preview, validation status, and hover states provide constant feedback.

### 5. Accessibility First
Keyboard navigation, screen reader support, and WCAG compliance are non-negotiable requirements, not optional enhancements.

---

## Tech Stack Reference

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Framework** | React 19.1.1 | UI library |
| **Language** | TypeScript 5.9.3 | Type safety |
| **Build Tool** | Vite 7.1.7 | Fast dev server |
| **Styling** | Tailwind CSS 4.1.16 | Utility-first CSS |
| **Components** | shadcn/ui | Pre-built accessible components |
| **Icons** | Lucide React 0.552.0 | Icon library |
| **State** | Zustand 5.0.8 | Global state management |
| **Validation** | AJV 8.17.1 | JSON Schema validation |
| **JSON View** | @microlink/react-json-view 1.27.0 | Syntax-highlighted JSON |

---

## Key Files & Locations

| File | Purpose | Location |
|------|---------|----------|
| **Zustand Store** | Global state (schema tree, selections) | `src/store/schemaStore.ts` |
| **Tree Component** | Recursive tree node display | `src/components/schema-editor/SchemaTreeNode.tsx` |
| **Property Editor** | Add/edit dialog | `src/components/schema-editor/PropertyEditor.tsx` |
| **JSON Preview** | Live schema preview | `src/components/preview/JSONPreviewPanel.tsx` |
| **Validation** | AJV schema validation | `src/lib/validation.ts` |
| **Utils** | cn() helper, depth styles | `src/lib/utils.ts` |
| **Types** | Property and schema types | `src/types/schema.ts` |

---

## Testing Strategy

### Unit Tests
- State management (Zustand store actions)
- Validation logic (AJV integration)
- Utility functions (depth calculation, tree traversal)

### Component Tests
- Tree node rendering
- Property editor form validation
- Keyboard navigation handlers

### Integration Tests
- Add/edit/delete property flows
- Template loading
- Export/import functionality

### Accessibility Tests
- Axe DevTools (automated)
- Screen reader testing (manual)
- Keyboard-only navigation (manual)

### E2E Tests (Optional)
- Complete user flows (create schema from scratch)
- Template customization
- Save and export

---

## Common Questions

### Q: Why Zustand instead of Redux?
**A:** Simpler API, less boilerplate, better TypeScript support. Perfect for this project's scale.

### Q: Why shadcn/ui instead of Material-UI?
**A:** Copy-paste components (not npm package), full customization, Tailwind integration, better accessibility defaults.

### Q: Why max 3 levels of nesting?
**A:** Prevents overly complex schemas, aligns with typical document structure (invoice → lineItems → product), reduces cognitive load.

### Q: Why real-time JSON preview?
**A:** Immediate feedback reduces errors. Users can verify schema as they build, reducing debugging time.

### Q: Do we support drag-and-drop reordering?
**A:** Not in Phase 1. Can add as enhancement if user testing shows need.

---

## Contributing

### Code Style
- Use TypeScript strict mode
- Follow shadcn/ui component patterns
- All interactive elements must be keyboard accessible
- Add ARIA attributes per [ACCESSIBILITY_CHECKLIST.md](./ACCESSIBILITY_CHECKLIST.md)

### Pull Request Checklist
- [ ] Passes TypeScript compilation (`npm run build`)
- [ ] Passes linting (`npm run lint`)
- [ ] Axe DevTools shows 0 violations
- [ ] Tested with keyboard navigation
- [ ] Tested in light and dark modes
- [ ] Matches design system specifications

### Documentation Updates
When adding features, update:
- Component specifications in [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)
- Code examples in [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
- Accessibility checklist if new interaction patterns added

---

## Support & Resources

### Internal Documentation
- [AI Document Processing - Main Project Docs](../../docs/)
- [Backend API Documentation](../../docs/guides/)

### External Resources
- [shadcn/ui Components](https://ui.shadcn.com/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Lucide Icons](https://lucide.dev/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)

### Questions?
- Design Questions: Reference [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)
- Implementation Questions: Reference [IMPLEMENTATION_GUIDE.md](./IMPLEMENTATION_GUIDE.md)
- Accessibility Questions: Reference [ACCESSIBILITY_CHECKLIST.md](./ACCESSIBILITY_CHECKLIST.md)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 2025-11-02 | Initial comprehensive design system release |

---

**Next Steps:**
1. Review all four documents
2. Set up development environment
3. Start with Phase 1 implementation
4. Use [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) as daily companion

**Happy Building! 🚀**

---

**Design System Version:** 1.0
**Last Updated:** 2025-11-02
**Designed by:** Aura, UI/UX Designer Agent
