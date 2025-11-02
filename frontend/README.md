# JSON Schema Builder - Frontend

React + TypeScript + Vite web application for visual JSON Schema creation with 3-level nesting support.

## ✅ Phase 1 Complete - Project Foundation

### Completed Setup

1. **Project Initialized**
   - ✅ Vite + React + TypeScript project created
   - ✅ Dependencies installed (Tailwind, Zustand, Lucide, Ajv, JSON viewer)
   - ✅ TypeScript configured with path aliases (`@/*` → `./src/*`)
   - ✅ Vite configured with Tailwind plugin and API proxy to port 8000

2. **Styling Configured**
   - ✅ Tailwind CSS with shadcn/ui theme system
   - ✅ CSS variables for light/dark mode
   - ✅ `src/index.css` with Tailwind directives
   - ✅ Utility function `src/lib/utils.ts` for className merging (`cn()`)

3. **Directory Structure**
   ```
   src/
   ├── components/ui/      # shadcn/ui components (add as needed)
   ├── lib/
   │   └── utils.ts        # ✅ Created
   ├── store/              # Zustand store (Phase 2)
   ├── types/              # TypeScript types (Phase 2)
   └── templates/          # Schema templates (Phase 2)
   ```

### Configuration Files Ready

- `vite.config.ts` - Vite + Tailwind + paths + proxy `/api` → `http://localhost:8000`
- `tsconfig.app.json` - TypeScript with `@/*` path mapping
- `tailwind.config.js` - Tailwind with shadcn/ui theme
- `package.json` - All dependencies installed

---

## 🚀 Quick Start

```bash
# Development server on http://localhost:3000
npm run dev

# Build for production
npm run build
npm run preview
```

### Environment Variables

Create `.env`:
```bash
VITE_API_URL=http://localhost:8000
```

---

## 📋 Phase 2 - Next Steps (Implementation Guide)

This guide provides step-by-step instructions to complete the JSON Schema Builder.

### Step 1: Create .env File

```bash
echo "VITE_API_URL=http://localhost:8000" > .env
```

### Step 2: Install Additional Dependencies

```bash
npm install uuid
npm install -D @types/uuid
```

### Step 3: Create Type Definitions

Full type definition files are in the comprehensive plan document. See `.claude/CLAUDE.md` for the detailed plan with all code snippets.

### Step 4: Install shadcn/ui Components

```bash
npx shadcn@latest add button card dialog input label select textarea switch separator tabs
```

### Step 5: Continue Implementation

Refer to the comprehensive implementation plan in the project planning session for:
- Full Zustand store implementation
- Template files (invoice, resume)
- UI component structure
- Tree view recursive component
- Property editor dialogs
- JSON preview with tabs

---

## 📁 Project Structure (Planned)

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                      # shadcn/ui components
│   │   ├── schema-builder/          # Tree view & editors
│   │   ├── preview/                 # JSON preview
│   │   ├── templates/               # Template selector
│   │   └── toolbar/                 # Top toolbar
│   ├── lib/
│   │   ├── utils.ts                 # ✅ Done
│   │   ├── api.ts                   # API client
│   │   └── schema-validator.ts      # Schema validation
│   ├── store/
│   │   └── schemaStore.ts           # Zustand state management
│   ├── types/
│   │   ├── schema.ts                # Schema type definitions
│   │   ├── api.ts                   # API types
│   │   └── template.ts              # Template types
│   ├── templates/
│   │   ├── invoice.ts               # Invoice schema template
│   │   ├── resume.ts                # Resume schema template
│   │   └── index.ts                 # Template exports
│   ├── App.tsx                      # Main app component
│   ├── main.tsx                     # Entry point
│   └── index.css                    # ✅ Done
├── package.json                     # ✅ Done
├── vite.config.ts                   # ✅ Done
├── tsconfig.app.json                # ✅ Done
├── tailwind.config.js               # ✅ Done
└── README.md                        # This file
```

---

## 🎯 Features (Planned)

- ✅ Visual tree-based schema editor
- ✅ Maximum 3-level nesting enforcement
- ✅ Property type selector (string, number, boolean, object, array)
- ✅ Constraint editors (format, pattern, min/max, enum, default)
- ✅ Required field marking
- ✅ Live JSON Schema preview
- ✅ Sample data generation
- ✅ Pre-built templates (Invoice, Resume)
- ✅ Save/load schemas via backend API
- ✅ Export as downloadable JSON file
- ✅ Import existing JSON schemas

---

## 📚 Key Technologies

| Technology | Purpose |
|------------|---------|
| React 19 | UI framework |
| TypeScript 5.6 | Type safety |
| Vite 6 | Build tool & dev server |
| Tailwind CSS 4 | Styling |
| shadcn/ui | Component library |
| Zustand 5 | State management |
| Lucide React | Icons |
| @microlink/react-json-view | JSON viewer |
| Ajv | JSON Schema validator |

---

##  Implementation Status

**Phase 1**: ✅ Complete - Project foundation, configuration, styling
**Phase 2**: 🔄 In Progress - Type definitions, store, templates
**Phase 3**: ⏳ Pending - UI components
**Phase 4**: ⏳ Pending - Backend integration
**Phase 5**: ⏳ Pending - Testing & polish

---

## 📖 Documentation

- Full implementation plan: See `.claude/CLAUDE.md`
- API documentation: Backend at `http://localhost:8000/docs` (when running)
- Component examples: [shadcn/ui docs](https://ui.shadcn.com/)

---

**Last Updated**: 2025-11-02
**Version**: 0.1.0 (Foundation Complete)
