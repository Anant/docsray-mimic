# Mistral Tools Parameter Handling Fix

## Summary

This document describes the fixes applied to resolve critical issues with Mistral AI tool integration in DocsRay MCP Server, as reported in [Issue #23](https://github.com/xingh/docsray-mcp/issues/23).

## Problems Fixed

### 1. Invalid Default Model

**Problem:** The default Mistral model was set to `mistral-ocr-latest`, which doesn't exist in Mistral's model catalog. This caused 400/500 errors when tools were invoked without an explicit model parameter.

**Solution:** Changed the default model to `pixtral-12b-2409`, which is a valid Mistral vision model appropriate for OCR and document processing tasks.

**Files Changed:**
- `src/docsray/config.py`: Updated `MistralOCRConfig.model` default
- `src/docsray/providers/mistral.py`: Updated fallback model references in `_analyze_content()` and `_structured_extract()`

### 2. Parameter Type Coercion

**Problem:** Complex parameters (dictionaries and lists) were being passed as JSON strings instead of native Python types. This caused Pydantic validation errors like:

```
Input should be a valid dictionary [type=dict_type, input_value='{"start": 1, "end": 5}', input_type=str]
```

**Root Cause:** The MCP protocol serializes parameters to JSON for transport. While simple types (strings, numbers) deserialize correctly, complex types (dicts, lists) remained as strings in some MCP client implementations.

**Solution:** Added parameter type coercion in all Mistral tool handlers:
- Created `coerce_parameter()` helper function to safely parse stringified JSON
- Applied coercion to all affected parameters:
  - `labels` (list) in `handle_classify_pages`
  - `page_range` (dict) in `handle_classify_pages` and `handle_summarize`
  - `schema` (dict) in `handle_extract_fields`
  - `page_filter` (dict) in `handle_extract_fields`

**Files Changed:**
- `src/docsray/tools/mistral_tools.py`: Added `coerce_parameter()` function and applied it in all handlers

## Technical Details

### Parameter Coercion Function

```python
def coerce_parameter(param: Any, expected_type: type) -> Any:
    """Convert stringified JSON parameters to their expected types.
    
    Args:
        param: The parameter value (possibly a JSON string)
        expected_type: The expected Python type (dict or list)
    
    Returns:
        The parameter converted to the expected type, or the original value if conversion fails
    """
    if isinstance(param, str) and expected_type in (dict, list):
        try:
            return json.loads(param)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Failed to parse parameter as {expected_type.__name__}: {e}")
            return param
    return param
```

**Features:**
- Safe JSON parsing with error handling
- Returns original value if parsing fails (graceful degradation)
- Only attempts parsing for string inputs to expected dict/list types
- Logs warnings for debugging when parsing fails
- Passes through already-typed parameters unchanged

### Valid Mistral Models

According to Mistral AI's documentation and API:

| Model | Use Case | Context Window |
|-------|----------|----------------|
| `pixtral-12b-2409` | Vision/OCR tasks, document analysis | 128K tokens |
| `mistral-large-latest` | Text understanding, complex reasoning | 128K tokens |
| `mistral-small-latest` | Lightweight text tasks, summarization | 32K tokens |

**Model Selection in DocsRay:**
- **Default:** `pixtral-12b-2409` (for OCR/vision capabilities)
- **Classification & Extraction:** Uses default or user-specified model
- **Summarization:** Defaults to `mistral-small-latest` (more cost-effective)

## Testing

### Unit Tests

Created comprehensive test suite in `tests/unit/test_mistral_tools.py`:

1. **Parameter Coercion Tests:**
   - String to dict conversion
   - String to list conversion
   - Pass-through for already-typed parameters
   - Invalid JSON handling
   - None value handling
   - Complex nested structures

2. **Tool Integration Tests:**
   - `handle_classify_pages` with stringified `labels` and `page_range`
   - `handle_extract_fields` with stringified `schema` and `page_filter`
   - `handle_summarize` with stringified `page_range`

3. **Error Handling Tests:**
   - Provider not available
   - Provider not initialized

### Manual Testing

```bash
# Test parameter coercion
python -c "
from docsray.tools.mistral_tools import coerce_parameter

# Test dict coercion
assert coerce_parameter('{\"start\": 1, \"end\": 5}', dict) == {'start': 1, 'end': 5}

# Test list coercion
assert coerce_parameter('[\"a\", \"b\"]', list) == ['a', 'b']

print('✅ Parameter coercion works!')
"

# Test model configuration
python -c "
from docsray.config import MistralOCRConfig

config = MistralOCRConfig()
assert config.model == 'pixtral-12b-2409'

print('✅ Default model is valid!')
"
```

## Backward Compatibility

✅ **Fully backward compatible:**
- Already-typed parameters pass through unchanged
- No changes to function signatures
- No changes to tool definitions in MCP
- Works with both old (properly typed) and new (stringified) parameter formats

## Usage Examples

### Before Fix (Would Fail)

```python
# MCP client sends stringified parameters
result = await docsray_classify_pages(
    document_url="report.pdf",
    labels='["income_statement", "balance_sheet"]',  # ❌ String causes validation error
    page_range='{"start": 20, "end": 40}'             # ❌ String causes validation error
)
```

### After Fix (Works)

```python
# Both formats now work

# Format 1: Properly typed (always worked)
result = await docsray_classify_pages(
    document_url="report.pdf",
    labels=["income_statement", "balance_sheet"],  # ✅ Native list
    page_range={"start": 20, "end": 40}            # ✅ Native dict
)

# Format 2: Stringified (now works too)
result = await docsray_classify_pages(
    document_url="report.pdf",
    labels='["income_statement", "balance_sheet"]',  # ✅ String gets coerced
    page_range='{"start": 20, "end": 40}'            # ✅ String gets coerced
)
```

## Performance Impact

**Minimal:** Parameter coercion only occurs once per tool invocation and uses fast JSON parsing from Python's built-in `json` module. Impact is negligible compared to network latency and AI model inference time.

## Security Considerations

**Safe JSON Parsing:**
- Uses Python's standard `json.loads()` (not `eval()`)
- Catches and handles `JSONDecodeError` gracefully
- Logs warnings for debugging without exposing sensitive data
- Returns original value on error (fail-safe)

## Future Improvements

Potential enhancements (out of scope for this fix):

1. **Schema Validation:** Add runtime schema validation for complex parameters
2. **Type Hints:** Strengthen type hints with `Literal` types for string enums
3. **Error Recovery:** Auto-correct common JSON formatting errors
4. **MCP Protocol Fix:** Address root cause in MCP transport layer (if applicable)

## Related Issues

- [Issue #23](https://github.com/xingh/docsray-mcp/issues/23): Mistral Tools Parameter Type Handling Issues

## Contributors

- Implementation based on detailed analysis in Issue #23 comment by @ColtonShawProctor
