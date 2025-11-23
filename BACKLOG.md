# Project Backlog

Feature requests and enhancements for the AI Document Processing platform.

---

## Image Preprocessing Configuration

**Priority:** Medium
**Status:** Backlog
**Date Added:** 2025-11-16

### Description
Make image preprocessing configurable per document/job instead of always applying the same preprocessing workflow.

### Current Behavior
- All PDF uploads automatically get preprocessed with:
  - Bilateral noise removal (medium strength)
  - Simple contrast enhancement (factor 1.5)
  - Grid overlay (20px, light gray)
- No way to disable or customize preprocessing per job

### Proposed Enhancements

#### 1. Enable/Disable Preprocessing
- Add `enable_preprocessing` boolean to extraction job API request
- Default: `true` (maintains current behavior)
- When `false`, skip preprocessing step entirely

**API Example:**
```json
POST /api/v1/documents/{document_id}/parse
{
  "extraction_schema": {...},
  "enable_preprocessing": false
}
```

#### 2. Configurable Preprocessing Parameters
- Add `preprocessing_config` object to API request
- Allow users to customize:
  - Noise removal method and strength
  - Contrast enhancement method and factor
  - Grid overlay settings (size, color, opacity)

**API Example:**
```json
POST /api/v1/documents/{document_id}/parse
{
  "extraction_schema": {...},
  "preprocessing_config": {
    "noise_removal": {
      "enabled": true,
      "method": "bilateral",
      "strength": "medium"
    },
    "contrast_enhancement": {
      "enabled": true,
      "method": "simple",
      "factor": 1.5
    },
    "grid_overlay": {
      "enabled": true,
      "grid_size": 20,
      "line_color": [200, 200, 200, 80],
      "line_width": 1
    }
  }
}
```

#### 3. Preprocessing Presets
- Create named preprocessing presets for common document types:
  - `invoice` - Optimized for invoices
  - `bank_statement` - Optimized for bank statements
  - `receipt` - Optimized for receipts
  - `scan` - Heavy noise reduction for scanned documents
  - `photo` - Light processing for photos
  - `none` - No preprocessing

**API Example:**
```json
POST /api/v1/documents/{document_id}/parse
{
  "extraction_schema": {...},
  "preprocessing_preset": "bank_statement"
}
```

#### 4. Per-Job Preprocessing Storage
- Store preprocessing configuration in `ExtractionJob` model:
  - `preprocessing_enabled` (boolean)
  - `preprocessing_config` (JSONB)
  - `preprocessing_preset` (string, nullable)
- Allows tracking which preprocessing was used for each job
- Enables A/B testing of preprocessing approaches

### Implementation Tasks

- [ ] Update `ExtractionJob` schema to include preprocessing fields
- [ ] Create database migration for new fields
- [ ] Add preprocessing configuration to API request schema
- [ ] Create preprocessing presets configuration file
- [ ] Update `preprocess_document_images` task to accept config parameters
- [ ] Update `combined_extraction` task to pass config to preprocessing
- [ ] Add preprocessing config to job results/status API
- [ ] Document preprocessing API in OpenAPI/Swagger
- [ ] Add frontend UI for preprocessing configuration (optional)

### Benefits

1. **Flexibility**: Users can optimize preprocessing for their document types
2. **Performance**: Users can disable preprocessing if not needed
3. **Testing**: Easy to compare results with/without preprocessing
4. **Cost Control**: Skipping preprocessing saves processing time
5. **Quality**: Fine-tune preprocessing for specific use cases

### Technical Notes

- Default preset should match current behavior (bilateral + simple contrast + grid)
- Preprocessing config should be validated before job creation
- Invalid config should fail fast with clear error message
- Consider caching preprocessed images with config hash to avoid reprocessing

### Related Files

- `app/tasks/image_preprocessor.py` - Main preprocessing task
- `app/tasks/combined_extraction.py` - Orchestration
- `app/models/extraction.py` - Job model
- `app/schemas/extraction.py` - API schemas
- `app/utils/image_utils.py` - Image processing functions

---

## Other Backlog Items

<!-- Add other feature requests below -->
