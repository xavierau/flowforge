# Documentation Overview

This directory contains detailed documentation for the AI Document Processing system.

## 📂 Directory Structure

```
docs/
├── architecture/      # System design and architectural decisions
├── guides/            # How-to guides and reference documentation
└── troubleshooting/   # Common issues and solutions
```

## 📚 Documentation Index

### Architecture Documents

- **[Stateless Job Processing](architecture/2025-11-02-stateless-job-processing.md)**
  - Core design principle of the system
  - State machine design and transitions
  - Database session management patterns
  - Retry strategies and failure recovery
  - Testing stateless tasks

- **[VLLM Integration](architecture/2025-11-02-vllm-integration.md)**
  - Multi-provider abstraction layer
  - Google Gemini, OpenAI, DeepSeek implementations
  - Invoice extraction workflows
  - Adding new VLLM providers
  - Error handling and fallback strategies

- **[Product Requirements Document](architecture/2025-11-02-product-requirements-document.md)**
  - Original product vision and requirements
  - Feature specifications
  - Technical constraints

- **[Phase 1 Implementation Plan](architecture/2025-11-02-phase-1-implementation-plan.md)**
  - Initial implementation roadmap
  - Technical decisions and rationale

- **[Implementation Progress](architecture/2025-11-02-implementation-progress.md)**
  - Development progress tracking
  - Completed features and fixes

### Guides

- **[Development Commands](guides/2025-11-02-development-commands.md)**
  - Package management with uv
  - Database migrations
  - Running services (local and Docker)
  - Testing commands
  - Code quality tools
  - Docker operations
  - Celery monitoring

### Troubleshooting

- **[Common Issues & Solutions](troubleshooting/2025-11-02-common-issues.md)**
  - SQLAlchemy reserved word conflicts
  - Pydantic field name conflicts
  - Python 3.12 protobuf compatibility
  - Jobs stuck in processing
  - VLLM API failures
  - PDF conversion issues
  - Database connection pool exhaustion
  - Celery worker not processing tasks
  - File upload size limits

## 🚀 Quick Start Paths

### For Developers

1. Start with [Development Commands](guides/2025-11-02-development-commands.md) to set up your environment
2. Read [Stateless Job Processing](architecture/2025-11-02-stateless-job-processing.md) to understand core patterns
3. Refer to [Common Issues](troubleshooting/2025-11-02-common-issues.md) when you encounter problems

### For Architects

1. Review [Product Requirements](architecture/2025-11-02-product-requirements-document.md) for context
2. Study [Stateless Job Processing](architecture/2025-11-02-stateless-job-processing.md) for design principles
3. Examine [VLLM Integration](architecture/2025-11-02-vllm-integration.md) for provider architecture

### For Troubleshooting

1. Check [Common Issues](troubleshooting/2025-11-02-common-issues.md) first
2. Review service logs as documented in [Development Commands](guides/2025-11-02-development-commands.md)
3. Consult architecture docs for design context

## 📝 Documentation Conventions

### File Naming

All documentation files follow the pattern:
```
YYYY-MM-DD-descriptive-title.md
```

This ensures:
- Chronological sorting
- Clear versioning
- Easy identification of documentation age

### Cross-References

Documentation uses relative links to reference other files:
- Within docs/: `[Link Text](../category/filename.md)`
- To root files: `[Link Text](../../filename.md)`

### Code Examples

Code examples in documentation are:
- Syntax-highlighted with language tags
- Executable (when possible)
- Include necessary imports and context
- Show both correct and incorrect patterns (when teaching)

## 🔄 Keeping Documentation Updated

When making changes to the codebase:

1. **Architecture Changes:** Update relevant architecture documents
2. **New Features:** Add to guides if user-facing
3. **Bug Fixes:** Update troubleshooting guide if it resolves common issues
4. **Breaking Changes:** Document in both architecture and troubleshooting

## 📖 Additional Resources

- **Main Reference:** [.claude/CLAUDE.md](../.claude/CLAUDE.md) - Quick reference guide
- **API Documentation:** http://localhost:8000/docs (when running)
- **Test Documentation:** [TEST_RESULTS.md](../TEST_RESULTS.md)
- **Setup Guide:** [SETUP_NOTES.md](../SETUP_NOTES.md)
- **Invoice Schema:** [invoice_schema.json](../invoice_schema.json)

## 🤝 Contributing to Documentation

When adding new documentation:

1. Use the date prefix: `YYYY-MM-DD-title.md`
2. Place in the appropriate directory:
   - `architecture/` - Design decisions, patterns, system design
   - `guides/` - How-to guides, reference material
   - `troubleshooting/` - Problem-solving guides
3. Add entry to this README index
4. Update [.claude/CLAUDE.md](../.claude/CLAUDE.md) if it's essential information

---

**Last Updated:** 2025-11-02
