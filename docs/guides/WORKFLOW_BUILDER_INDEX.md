# Workflow Builder - Documentation Index

**Date**: 2025-11-15
**Version**: 1.0
**Status**: Production Ready

## 🎯 Quick Navigation

| I want to... | Go to... |
|-------------|----------|
| Get started in 5 minutes | [Quick Reference](#quick-reference) |
| Learn all features | [User Guide](#user-guide) |
| See real examples | [Examples](#examples) |
| Understand how it works | [Architecture](#architecture) |
| Reference expression syntax | [Expression Syntax](#expression-syntax) |

---

## 📚 Documentation

### Quick Reference
**File**: `2025-11-15-workflow-builder-quick-reference.md`

**What**: Cheat sheet with common patterns and syntax

**Contents**:
- 5-minute quick start
- Node types table
- Expression syntax examples
- Configuration cheat sheet
- Keyboard shortcuts
- Common errors & fixes
- Copy-paste example workflow

**Best for**: Quick lookups, refreshers, cheat sheet

⏱️ **Read time**: 5 minutes

---

### User Guide
**File**: `2025-11-15-workflow-builder-user-guide.md`

**What**: Complete guide to all workflow builder features

**Contents**:
- Getting started
- All 5 node types (detailed)
- Expression syntax (complete)
- Building your first workflow
- Common patterns
- Tips & best practices
- Troubleshooting

**Best for**: First-time users, complete feature reference

⏱️ **Read time**: 30 minutes

---

### Examples
**File**: `2025-11-15-workflow-examples.md`

**What**: 7 real-world workflow examples with step-by-step configs

**Contents**:
1. Basic Invoice Processing (5 min)
2. Invoice Approval Workflow (10 min)
3. Receipt Validation & Classification (15 min)
4. Multi-Stage Data Enrichment (20 min)
5. Error Handling & Retry (15 min)
6. Conditional Routing by Document Type (20 min)
7. Complex Multi-Condition Workflow (25 min)

**Best for**: Learning by example, copy-paste configs

⏱️ **Read time**: 45 minutes (or pick specific examples)

---

### Architecture
**File**: `../architecture/2025-11-15-workflow-builder-architecture.md`

**What**: Technical implementation details

**Contents**:
- Architecture overview
- Technology stack
- File structure
- Core components (detailed)
- State management with Zustand
- Data flow patterns
- Expression system internals
- Validation system
- Persistence (localStorage)
- Performance optimizations
- Security considerations
- Testing strategy

**Best for**: Developers, technical understanding, debugging

⏱️ **Read time**: 1 hour

---

### Expression Syntax
**File**: `../../frontend/EXPRESSION_SYNTAX.md`

**What**: Complete reference for expression syntax

**Contents**:
- Basic syntax
- Advanced patterns
- All supported fields
- Nested data access
- Condition operators
- Troubleshooting
- API reference

**Best for**: Expression syntax lookup, advanced usage

⏱️ **Read time**: 15 minutes

---

## 🚀 Getting Started Path

### For First-Time Users

1. **Quick Start** (5 min)
   - Read: [Quick Reference - Quick Start section](./2025-11-15-workflow-builder-quick-reference.md#-quick-start-5-minutes)
   - Do: Add nodes, connect them, configure

2. **First Workflow** (10 min)
   - Read: [User Guide - Building Your First Workflow](./2025-11-15-workflow-builder-user-guide.md#building-your-first-workflow)
   - Do: Follow invoice processing example

3. **Learn Node Types** (15 min)
   - Read: [User Guide - Node Types](./2025-11-15-workflow-builder-user-guide.md#node-types)
   - Do: Experiment with each node type

4. **Master Expressions** (15 min)
   - Read: [User Guide - Expression Syntax](./2025-11-15-workflow-builder-user-guide.md#expression-syntax)
   - Do: Use Expression Builder to insert fields

5. **Build Real Workflow** (30 min)
   - Read: [Examples - Pick one that matches your use case](./2025-11-15-workflow-examples.md)
   - Do: Implement the example

**Total time**: ~75 minutes to full proficiency

---

### For Developers

1. **Architecture Overview** (20 min)
   - Read: [Architecture - Overview & Tech Stack](../architecture/2025-11-15-workflow-builder-architecture.md#architecture-overview)

2. **Core Components** (30 min)
   - Read: [Architecture - Core Components](../architecture/2025-11-15-workflow-builder-architecture.md#core-components)

3. **State Management** (20 min)
   - Read: [Architecture - State Management](../architecture/2025-11-15-workflow-builder-architecture.md#state-management)

4. **Expression System** (20 min)
   - Read: [Architecture - Expression System](../architecture/2025-11-15-workflow-builder-architecture.md#expression-system)

5. **Build Feature** (varies)
   - Read: Architecture sections relevant to your feature
   - Implement following existing patterns

**Total time**: ~90 minutes for technical understanding

---

## 📖 Documentation Structure

```
docs/
├── guides/
│   ├── 2025-11-15-workflow-builder-user-guide.md      ← Complete guide
│   ├── 2025-11-15-workflow-builder-quick-reference.md ← Cheat sheet
│   ├── 2025-11-15-workflow-examples.md                ← Real examples
│   └── WORKFLOW_BUILDER_INDEX.md                      ← This file
└── architecture/
    └── 2025-11-15-workflow-builder-architecture.md    ← Technical docs

frontend/
├── EXPRESSION_SYNTAX.md                                ← Expression reference
├── EXPRESSION_QUICK_START.md                           ← Expression examples
├── EXPRESSION_TESTING_GUIDE.md                         ← Test cases
└── IMPLEMENTATION_SUMMARY.md                           ← Implementation details
```

---

## 🎓 Learning by Use Case

### I want to extract and process invoices
1. Read: [Examples - Basic Invoice Processing](./2025-11-15-workflow-examples.md#example-1-basic-invoice-processing)
2. Read: [Examples - Invoice Approval Workflow](./2025-11-15-workflow-examples.md#example-2-invoice-approval-workflow)
3. Build: Your invoice workflow

### I want to route documents conditionally
1. Read: [User Guide - If Node](./2025-11-15-workflow-builder-user-guide.md#4-if-conditional)
2. Read: [Examples - Conditional Routing](./2025-11-15-workflow-examples.md#example-6-conditional-routing-by-document-type)
3. Build: Your routing logic

### I want to transform data with Python
1. Read: [User Guide - Python Runner](./2025-11-15-workflow-builder-user-guide.md#3-python-runner)
2. Read: [Quick Reference - Python Quick Reference](./2025-11-15-workflow-builder-quick-reference.md#-python-quick-reference)
3. Read: [Examples - Multi-Stage Data Enrichment](./2025-11-15-workflow-examples.md#example-4-multi-stage-data-enrichment)
4. Build: Your transformation logic

### I want to call external APIs
1. Read: [User Guide - HTTP Request Node](./2025-11-15-workflow-builder-user-guide.md#5-http-request)
2. Read: [Expression Syntax - Using in URLs](../../frontend/EXPRESSION_SYNTAX.md)
3. Build: Your API integration

### I want to validate and handle errors
1. Read: [Examples - Error Handling & Retry](./2025-11-15-workflow-examples.md#example-5-error-handling--retry)
2. Build: Your validation workflow

---

## 🔍 Search Guide

### By Keyword

| Looking for... | Find it in... |
|---------------|---------------|
| "How do I add a node?" | User Guide - Getting Started |
| "Expression syntax" | Expression Syntax OR Quick Reference |
| "Python examples" | Examples OR Quick Reference |
| "If node condition" | User Guide - If Node OR Examples |
| "Save workflow" | User Guide - Workflow Controls |
| "Error: Schema required" | User Guide - Troubleshooting |
| "Node border colors" | Quick Reference - Visual Indicators |
| "Connection validation" | Architecture - Validation System |
| "How it works internally" | Architecture - All sections |
| "Copy-paste example" | Examples OR Quick Reference |

---

## 📊 Feature Coverage

### User Guide Coverage
- ✅ All 5 node types documented
- ✅ Expression syntax complete
- ✅ Configuration examples
- ✅ Troubleshooting guide
- ✅ Best practices
- ✅ Tips for success

### Examples Coverage
- ✅ Simple linear workflow
- ✅ Conditional branching
- ✅ Multi-condition routing
- ✅ Data transformation
- ✅ Error handling
- ✅ Document classification
- ✅ Complex enterprise workflow

### Architecture Coverage
- ✅ Component architecture
- ✅ State management
- ✅ Expression system
- ✅ Validation system
- ✅ Persistence layer
- ✅ Performance optimizations
- ✅ Security considerations
- ✅ Testing strategy

---

## 🆘 Need Help?

### Documentation Not Answering Your Question?

1. **Check all docs**: Use the search guide above
2. **Try examples**: Often shows patterns not explicitly documented
3. **Check architecture**: Technical details might be there
4. **Look at code**: Implementation is well-commented

### Found a Bug or Issue?

1. **Check**: [User Guide - Troubleshooting](./2025-11-15-workflow-builder-user-guide.md#troubleshooting)
2. **Check**: [Quick Reference - Common Errors](./2025-11-15-workflow-builder-quick-reference.md#-common-errors--fixes)
3. **Report**: Create GitHub issue with:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots if applicable

### Want to Contribute?

1. **Read**: [Architecture Guide](../architecture/2025-11-15-workflow-builder-architecture.md)
2. **Follow**: Existing patterns in codebase
3. **Test**: Thoroughly before submitting PR
4. **Document**: Update relevant docs with your changes

---

## 🗺️ Roadmap

### Phase 1: Visual Builder ✅ COMPLETE
- [x] 5 node types
- [x] Visual canvas with React Flow
- [x] Expression syntax
- [x] Real-time validation
- [x] localStorage persistence
- [x] Import/export JSON

### Phase 2: Backend Integration (Next)
- [ ] REST API for workflow CRUD
- [ ] PostgreSQL storage
- [ ] Workflow execution engine
- [ ] Real-time execution status
- [ ] Execution logs
- [ ] Integration with existing document processing

### Phase 3: Advanced Features (Future)
- [ ] Workflow templates
- [ ] Undo/redo
- [ ] Versioning
- [ ] Sub-workflows
- [ ] Loop nodes
- [ ] Error handling nodes
- [ ] Testing/debugging mode

### Phase 4: Collaboration (Future)
- [ ] Multi-user editing
- [ ] Comments on nodes
- [ ] Workflow sharing
- [ ] Team workspaces
- [ ] Audit logs

---

## 📈 Version History

### Version 1.0 (2025-11-15) - Initial Release
- ✅ Complete workflow builder implementation
- ✅ 5 node types (HTTP Trigger, Extraction, Python Runner, HTTP Request, If)
- ✅ Expression system with builder UI
- ✅ Real-time validation
- ✅ localStorage persistence
- ✅ Complete documentation (4 guides + architecture)

---

## 📞 Contact & Feedback

- **Questions**: Check documentation first
- **Bugs**: GitHub Issues
- **Feature Requests**: GitHub Issues with [Feature Request] tag
- **Documentation Issues**: GitHub Issues with [Documentation] tag

---

**Last Updated**: 2025-11-15
**Version**: 1.0
**Status**: Production Ready
**Maintainers**: Development Team
