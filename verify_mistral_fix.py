#!/usr/bin/env python3
"""Manual verification script for Mistral parameter handling fix.

This script demonstrates that the fix correctly handles both:
1. Invalid default model issue (now uses valid pixtral-12b-2409)
2. Stringified parameter coercion (handles JSON strings properly)

Run this script to verify the fixes are working correctly.
"""

import sys

sys.path.insert(0, "src")

from docsray.config import MistralOCRConfig
from docsray.tools.mistral_tools import coerce_parameter


# Valid Mistral AI model identifiers
VALID_MISTRAL_MODELS = [
    "pixtral-12b-2409",  # Vision model for OCR/documents
    "mistral-large-latest",  # Text model for complex reasoning
    "mistral-small-latest",  # Lightweight text model
]


def test_model_fix():
    """Verify the default model is now valid."""
    print("=" * 70)
    print("TEST 1: Invalid Default Model Fix")
    print("=" * 70)

    # Create config with defaults
    config = MistralOCRConfig()

    print(f"Default model: {config.model}")
    print(f"Valid? {config.model in VALID_MISTRAL_MODELS}")

    # Verify it's not the old invalid model
    assert config.model != "mistral-ocr-latest", "Old invalid model still in use!"
    assert config.model == "pixtral-12b-2409", f"Unexpected model: {config.model}"

    print("\n✅ Default model is now valid: pixtral-12b-2409")
    print("   (Previously was invalid: mistral-ocr-latest)")
    return True


def test_parameter_coercion():
    """Verify parameter coercion handles stringified JSON."""
    print("\n" + "=" * 70)
    print("TEST 2: Parameter Type Coercion Fix")
    print("=" * 70)

    tests = [
        # (description, input, expected_type, expected_output)
        (
            "Dict from JSON string",
            '{"start": 1, "end": 5}',
            dict,
            {"start": 1, "end": 5},
        ),
        (
            "List from JSON string",
            '["income_statement", "balance_sheet"]',
            list,
            ["income_statement", "balance_sheet"],
        ),
        ("Already a dict", {"start": 1, "end": 5}, dict, {"start": 1, "end": 5}),
        (
            "Already a list",
            ["income_statement", "balance_sheet"],
            list,
            ["income_statement", "balance_sheet"],
        ),
        ("None value", None, dict, None),
        (
            "Complex nested structure",
            '{"fields": [{"name": "revenue", "type": "currency"}]}',
            dict,
            {"fields": [{"name": "revenue", "type": "currency"}]},
        ),
        ("List of numbers", "[1, 30, 31, 32]", list, [1, 30, 31, 32]),
    ]

    all_passed = True
    for desc, input_val, expected_type, expected_output in tests:
        try:
            result = coerce_parameter(input_val, expected_type)
            if result == expected_output:
                print(f"✅ {desc}")
                print(f"   Input:  {repr(input_val)[:60]}")
                print(f"   Output: {repr(result)[:60]}")
            else:
                print(f"❌ {desc}")
                print(f"   Expected: {expected_output}")
                print(f"   Got:      {result}")
                all_passed = False
        except Exception as e:
            print(f"❌ {desc}")
            print(f"   Error: {e}")
            all_passed = False

    return all_passed


def test_invalid_json_handling():
    """Verify graceful handling of invalid JSON."""
    print("\n" + "=" * 70)
    print("TEST 3: Invalid JSON Handling")
    print("=" * 70)

    invalid_inputs = [
        "{invalid json}",
        "{'single': 'quotes'}",
        "[unclosed list",
        "",
    ]

    all_passed = True
    for invalid_input in invalid_inputs:
        try:
            result = coerce_parameter(invalid_input, dict)
            # Should return the original value when parsing fails
            if result == invalid_input:
                print(f"✅ Gracefully handled: {repr(invalid_input)[:40]}")
            else:
                print(f"⚠️  Unexpected result for {repr(invalid_input)[:40]}: {result}")
        except Exception as e:
            print(f"❌ Exception for {repr(invalid_input)[:40]}: {e}")
            all_passed = False

    return all_passed


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("MISTRAL PARAMETER HANDLING FIX VERIFICATION")
    print("=" * 70)
    print("\nThis script verifies the fixes for Issue #23:")
    print("1. Invalid default model (mistral-ocr-latest → pixtral-12b-2409)")
    print("2. Parameter type coercion (stringified JSON → native types)")
    print()

    results = []

    try:
        results.append(("Model Fix", test_model_fix()))
    except Exception as e:
        print(f"\n❌ Model fix test failed: {e}")
        results.append(("Model Fix", False))

    try:
        results.append(("Parameter Coercion", test_parameter_coercion()))
    except Exception as e:
        print(f"\n❌ Parameter coercion test failed: {e}")
        results.append(("Parameter Coercion", False))

    try:
        results.append(("Invalid JSON Handling", test_invalid_json_handling()))
    except Exception as e:
        print(f"\n❌ Invalid JSON handling test failed: {e}")
        results.append(("Invalid JSON Handling", False))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_passed = all(result for _, result in results)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    if all_passed:
        print("\n🎉 All tests passed! The fix is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
