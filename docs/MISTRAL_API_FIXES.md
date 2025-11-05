# Mistral API Fixes - Issue #23

## Summary

This document describes the fixes implemented to address Mistral API integration issues identified in Issue #23.

## Issues Fixed

### 1. Empty API Response Handling

**Problem:** `classify_pages` was returning empty labels array due to improper handling of empty or null API responses.

**Solution:**
- Added explicit checks for `response.choices` being empty
- Added checks for `response.choices[0].message.content` being None or empty
- Strip whitespace and validate content exists before JSON parsing
- Return appropriate empty results instead of crashing

**Code Location:** `src/docsray/providers/mistral.py` lines 397-412 (classify_pages)

### 2. JSON Parsing Errors

**Problem:** `extract_fields` was failing with "Expecting value: line 1 column 1 (char 0)" error when API returned invalid or empty JSON.

**Solution:**
- Wrapped JSON parsing in try/except with JSONDecodeError handling
- Added detailed error logging showing the exact response text
- Return structured error response with error messages
- Added exc_info=True to exception logging for stack traces

**Code Location:** `src/docsray/providers/mistral.py` lines 475-490 (extract_fields)

### 3. JSON Mode Support

**Problem:** API was not enforcing JSON format, leading to inconsistent response formats.

**Solution:**
- Added `response_format={"type": "json_object"}` to all Mistral API calls
- Updated prompts to request JSON objects (not arrays) with proper structure
- Classification: `{"labels": [...]}`
- Extraction: `{"fields": [...], "errors": []}`

**Code Location:** `src/docsray/providers/mistral.py` lines 394, 467

### 4. Enhanced Logging

**Problem:** Silent failures with no debugging information.

**Solution:**
- Added debug logging for input parameters (model, labels, fields, pages)
- Log raw API responses (first 200 chars) for debugging
- Log validation results (items validated, skipped)
- Added detailed warning logs for each validation failure type

**Code Location:** Throughout `src/docsray/providers/mistral.py`

### 5. Improved Validation

**Problem:** Validation was not providing detailed feedback on why items were rejected.

**Solution:**
- Enhanced `_validate_classification_result` with detailed per-item validation
- Enhanced `_validate_extraction_result` with detailed per-field validation
- Log specific reasons for rejection (invalid label, bad confidence, missing keys)
- Count and report skipped items

**Code Location:** `src/docsray/providers/mistral.py` lines 619-658

## Testing

### Manual Testing

Created standalone test scripts to verify:
1. Empty response handling
2. Whitespace-only response handling
3. Invalid JSON handling
4. Valid JSON object parsing
5. Validation filtering logic

See `/tmp/test_validation_fixes.py` for test implementation.

### Unit Tests

Created comprehensive unit tests in `tests/unit/test_mistral_api_fixes.py` covering:
- Empty response.choices handling
- Empty/null content handling
- Whitespace-only content handling
- Invalid JSON response handling
- Valid JSON object with labels/fields
- JSON mode parameter inclusion
- Validation edge cases

## Configuration

No configuration changes required. Default model in config is already correct:
- `MistralOCRConfig.model = "pixtral-12b-2409"` (valid Mistral vision model)

## Prompt Improvements

### Classification Prompt
```
IMPORTANT: You MUST return a JSON object with a "labels" array containing the classification results.

Return JSON object with this exact format: {"labels": [{"page": int, "label": string, "confidence": float}]}.
```

### Extraction Prompt
```
IMPORTANT: You MUST return ONLY a valid JSON object, with no additional text or explanation.

Return JSON object with this exact format: {"fields": [{"name": string, "value": typed_value, "confidence": float, "source": {"page": int, "lineIdx": int?}}], "errors": []}.
```

## Migration Impact

**Breaking Changes:** None

**Behavioral Changes:**
- More detailed error messages in logs
- Better handling of edge cases (empty responses, invalid JSON)
- Consistent JSON object format expected from API

## Future Improvements

Potential future enhancements:
1. Add retry logic with exponential backoff for transient failures
2. Add API rate limiting detection and handling
3. Add telemetry/metrics for success/failure rates
4. Add caching for repeated classification requests
5. Add batch processing optimizations

## Related Files

- `src/docsray/providers/mistral.py` - Main implementation
- `src/docsray/tools/mistral_tools.py` - Tool handlers (parameter coercion already implemented)
- `src/docsray/config.py` - Configuration (model defaults correct)
- `tests/unit/test_mistral_api_fixes.py` - Unit tests
- `/tmp/test_validation_fixes.py` - Standalone validation tests

## References

- Issue: https://github.com/xingh/docsray-mcp/issues/23
- Mistral API Documentation: https://docs.mistral.ai/api/
- Pixtral Model: https://docs.mistral.ai/capabilities/vision/
