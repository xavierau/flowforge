# Qwen Document-to-Markdown Implementation

## Overview
Implemented Qwen3-VL-8B-Instruct markdown converter via Dashscope API, following the existing converter architecture pattern.

## Files Created/Modified

### New Files
1. **`app/services/converters/qwen_markdown_converter.py`** (~390 lines)
   - Implements `IImageToMarkdownConverter` interface
   - Supports 3 format styles: `qwenvl_markdown`, `qwenvl_html`, `standard`
   - Automatic MIME type detection from base64 images
   - Parallel batch processing with retry logic
   - Extended timeouts for large images (5 min read/write)

2. **`test_qwen_markdown.py`** (~250 lines)
   - Comprehensive test suite for all formats
   - Single and batch conversion tests
   - Token usage tracking
   - Saves outputs to files for inspection

### Modified Files
1. **`app/config.py`**
   - Added `dashscope_api_key: str = ""`

2. **`app/services/converters/converter_factory.py`**
   - Imported `QwenMarkdownConverter`
   - Registered `qwen_vision` converter in `_register_converters()`
   - Updated docstring to include `qwen_vision`

3. **`.env.example`**
   - Added `DASHSCOPE_API_KEY` with documentation

## Features

### Format Styles

#### 1. QwenVL Markdown (`qwenvl_markdown`)
```markdown
<!-- Table (x1, y1, x2, y2) -->
\begin{tabular}{...}
...
\end{tabular}

<!-- Image (x1, y1, x2, y2) -->
```
- Tables as LaTeX with coordinates
- Image placeholders with positioning
- Precise layout reconstruction

#### 2. QwenVL HTML (`qwenvl_html`)
```html
<div class="text" data-bbox="x1 y1 x2 y2">...</div>
<div class="table" data-bbox="x1 y1 x2 y2">...</div>
```
- HTML with bounding box attributes
- Element-level positioning
- Supports visualization (like notebook)

#### 3. Standard Markdown (`standard`)
```markdown
# Header

Regular markdown content with tables, lists, etc.
```
- Clean markdown output
- No coordinates or positioning
- Standard formatting

### Key Features

**MIME Type Detection:**
- Automatic detection from base64 data using PIL
- Supports: JPEG, PNG, WEBP, GIF, BMP, TIFF
- Fallback to `image/jpeg` if detection fails

**Batch Processing:**
- Parallel conversion with `asyncio.gather()`
- Per-page retry with exponential backoff (5s, 10s, 20s)
- Aggregated token counts and metrics
- Per-page breakdown in results

**Error Handling:**
- 3 retry attempts with exponential backoff
- Comprehensive error logging
- Graceful degradation

## Usage

### Setup
```bash
# 1. Add API key to .env
echo "DASHSCOPE_API_KEY=your_key_here" >> .env

# 2. The converter is automatically registered if key exists
```

### Using the Converter
```python
from app.services.converters.converter_factory import get_converter_factory

# Get factory instance
factory = get_converter_factory()

# Get Qwen converter
converter = factory.get_markdown_converter("qwen_vision")

# Convert single image
result = await converter.convert_single(
    image_base64="base64_string_here",
    format_style="qwenvl_markdown",  # or "qwenvl_html" or "standard"
    page_number=1
)

print(f"Markdown: {result.markdown_content}")
print(f"Tokens: {result.input_tokens + result.output_tokens}")

# Convert batch
result = await converter.convert_batch(
    images_base64=["base64_1", "base64_2", "base64_3"],
    format_style="standard"
)
```

### Running Tests
```bash
# Test with single image
python test_qwen_markdown.py /path/to/image.jpg

# Test with multiple images (batch mode)
python test_qwen_markdown.py image1.jpg image2.png image3.jpg

# Uses default images if found in current directory
python test_qwen_markdown.py
```

### Test Output
The test script generates:
- `test_output_single_qwenvl_markdown.md`
- `test_output_single_qwenvl_html.md`
- `test_output_single_standard.md`
- `test_output_batch_qwenvl_markdown.md` (if multiple images)
- `test_output_batch_qwenvl_html.md` (if multiple images)
- `test_output_batch_standard.md` (if multiple images)

## API Configuration

### Endpoint
```
Base URL: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
Model: qwen3-vl-8b-instruct
```

### Parameters
```python
{
    "min_pixels": 512 * 32 * 32,   # 524,288 pixels
    "max_pixels": 2048 * 32 * 32,  # 2,097,152 pixels
}
```

### Timeouts
- Connect: 30 seconds
- Read: 300 seconds (5 minutes)
- Write: 300 seconds (5 minutes)
- Pool: 30 seconds

## Token Usage & Pricing

**Dashscope Pricing (Singapore Region):**
- Input: $0.72 per million tokens
- Output: $0.72 per million tokens
- Free quota: 1 million tokens (90-day validity)

**Typical Usage:**
- Single invoice page: ~1,500-2,500 tokens
- Multi-page document (5 pages): ~8,000-12,000 tokens

## Architecture Integration

### Factory Pattern
```
ConverterFactory
├── markdown_converters
│   ├── gemini_vision (Google Gemini 2.5 Flash)
│   ├── gpt4v (OpenAI GPT-4 Vision)
│   └── qwen_vision (Qwen3-VL-8B-Instruct) ← NEW
└── json_extractors
    ├── gemini (Gemini 2.5 Flash text)
    └── openai (GPT-4o-mini)
```

### Interface Compliance
Implements `IImageToMarkdownConverter`:
- ✅ `convert_single()` - Single image conversion
- ✅ `convert_batch()` - Parallel batch conversion
- ✅ Returns `MarkdownConversionResult` with metrics
- ✅ Async/await support
- ✅ Retry logic with exponential backoff

## Comparison with Other Converters

| Feature | Gemini Vision | GPT-4V | Qwen Vision |
|---------|--------------|---------|-------------|
| Provider | Google | OpenAI | Dashscope |
| Model | gemini-2.5-flash | gpt-4-vision-preview | qwen3-vl-8b-instruct |
| Parallel Batch | ✅ | ✅ | ✅ |
| Retry Logic | ✅ | ✅ | ✅ |
| MIME Detection | ❌ (PIL only) | ❌ (Hardcoded) | ✅ Automatic |
| Special Formats | ❌ | ❌ | ✅ (qwenvl_markdown, qwenvl_html) |
| Pricing | Medium | High | Low |

## Notes

### Prompt Construction
- **QwenVL formats** use simple prompts: `"qwenvl markdown"` or `"qwenvl html"`
- **Standard format** uses detailed instructions for clean markdown
- QwenVL formats don't need page markers (model adds them automatically)

### MIME Type Detection Strategy
1. Decode base64 to bytes
2. Use `PIL.Image.open()` to detect format
3. Map PIL format to MIME type (JPEG → image/jpeg, PNG → image/png)
4. Construct data URI: `data:{mime_type};base64,{base64_string}`

### Dependencies
- `openai>=1.0.0` ✅ (for OpenAI-compatible API client)
- `Pillow` ✅ (for image format detection)
- `httpx` ✅ (for timeout configuration)

## Future Enhancements

1. **Format Validation**
   - Validate QwenVL HTML structure
   - Extract and validate coordinates from markdown

2. **Visualization Tools**
   - Port `draw_bbox_html()` and `draw_bbox_markdown()` from notebook
   - Add visual debugging support

3. **Cost Optimization**
   - Cache results for identical images
   - Adaptive pixel threshold based on image complexity

4. **Additional Formats**
   - Support JSON output mode
   - Add LaTeX-only extraction

## References

- [Qwen VL OCR Documentation](https://www.alibabacloud.com/help/en/model-studio/qwen-vl-ocr)
- [Qwen API Reference](https://www.alibabacloud.com/help/en/model-studio/qwen-api-reference)
- Reference Notebook: `qwen_document_parsing.ipynb`

---

**Implementation Date:** 2025-11-25
**Status:** ✅ Complete and tested
