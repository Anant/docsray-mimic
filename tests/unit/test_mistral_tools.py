"""Unit tests for Mistral AI tools parameter handling."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docsray.tools.mistral_tools import (
    coerce_parameter,
    handle_classify_pages,
    handle_extract_fields,
    handle_summarize,
)


class TestParameterCoercion:
    """Test suite for parameter type coercion."""

    def test_coerce_dict_from_string(self):
        """Test coercing a stringified dict."""
        input_str = '{"start": 1, "end": 5}'
        result = coerce_parameter(input_str, dict)
        assert isinstance(result, dict)
        assert result == {"start": 1, "end": 5}

    def test_coerce_list_from_string(self):
        """Test coercing a stringified list."""
        input_str = '["income_statement", "balance_sheet"]'
        result = coerce_parameter(input_str, list)
        assert isinstance(result, list)
        assert result == ["income_statement", "balance_sheet"]

    def test_coerce_already_dict(self):
        """Test that already-dict parameters pass through unchanged."""
        input_dict = {"start": 1, "end": 5}
        result = coerce_parameter(input_dict, dict)
        assert result is input_dict
        assert result == {"start": 1, "end": 5}

    def test_coerce_already_list(self):
        """Test that already-list parameters pass through unchanged."""
        input_list = ["income_statement", "balance_sheet"]
        result = coerce_parameter(input_list, list)
        assert result is input_list
        assert result == ["income_statement", "balance_sheet"]

    def test_coerce_invalid_json(self):
        """Test handling of invalid JSON string."""
        input_str = "{invalid json}"
        result = coerce_parameter(input_str, dict)
        # Should return the original string if parsing fails
        assert result == input_str

    def test_coerce_none(self):
        """Test handling of None value."""
        result = coerce_parameter(None, dict)
        assert result is None

    def test_coerce_empty_string(self):
        """Test handling of empty string."""
        result = coerce_parameter("", dict)
        # Empty string should fail to parse and return as-is
        assert result == ""

    def test_coerce_complex_nested_dict(self):
        """Test coercing complex nested structures."""
        input_str = '{"fields": [{"name": "revenue", "type": "currency"}]}'
        result = coerce_parameter(input_str, dict)
        assert isinstance(result, dict)
        assert "fields" in result
        assert isinstance(result["fields"], list)
        assert result["fields"][0]["name"] == "revenue"

    def test_coerce_list_of_numbers(self):
        """Test coercing a list of numbers."""
        input_str = "[1, 30, 31, 32]"
        result = coerce_parameter(input_str, list)
        assert isinstance(result, list)
        assert result == [1, 30, 31, 32]


@pytest.mark.asyncio
class TestClassifyPagesParameterHandling:
    """Test parameter handling in handle_classify_pages."""

    async def test_classify_pages_with_string_labels(self):
        """Test that stringified labels are properly coerced."""
        with patch("docsray.tools.mistral_tools.download_document") as mock_download:
            with patch("docsray.tools.mistral_tools.get_local_document"):
                with patch("docsray.tools.mistral_tools.fitz") as mock_fitz:
                    # Mock registry and provider
                    mock_provider = MagicMock()
                    mock_provider._initialized = True
                    mock_provider.config.model = "pixtral-12b-2409"
                    mock_provider.classify_pages = AsyncMock(
                        return_value=[
                            {"page": 1, "label": "income_statement", "confidence": 0.95}
                        ]
                    )

                    mock_registry = MagicMock()
                    mock_registry.get_provider.return_value = mock_provider

                    # Mock PDF
                    mock_pdf = MagicMock()
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = "Sample income statement text"
                    mock_pdf.__getitem__.return_value = mock_page
                    mock_pdf.__len__.return_value = 1
                    mock_fitz.open.return_value = mock_pdf

                    # Call with stringified labels
                    result = await handle_classify_pages(
                        document_url="test.pdf",
                        labels='["income_statement", "balance_sheet"]',  # Stringified JSON to test parameter coercion
                        registry=mock_registry,
                    )

                    # Should succeed and coerce the labels
                    assert "labels" in result
                    assert result["labels"][0]["label"] == "income_statement"

    async def test_classify_pages_with_string_page_range(self):
        """Test that stringified page_range is properly coerced."""
        with patch("docsray.tools.mistral_tools.download_document"):
            with patch("docsray.tools.mistral_tools.get_local_document"):
                with patch("docsray.tools.mistral_tools.fitz") as mock_fitz:
                    # Mock registry and provider
                    mock_provider = MagicMock()
                    mock_provider._initialized = True
                    mock_provider.config.model = "pixtral-12b-2409"
                    mock_provider.classify_pages = AsyncMock(
                        return_value=[
                            {"page": 1, "label": "income_statement", "confidence": 0.95}
                        ]
                    )

                    mock_registry = MagicMock()
                    mock_registry.get_provider.return_value = mock_provider

                    # Mock PDF
                    mock_pdf = MagicMock()
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = "Sample text"
                    mock_pdf.__getitem__.return_value = mock_page
                    mock_pdf.__len__.return_value = 5
                    mock_fitz.open.return_value = mock_pdf

                    # Call with stringified page_range
                    result = await handle_classify_pages(
                        document_url="test.pdf",
                        labels=["income_statement"],
                        page_range='{"start": 1, "end": 5}',  # Stringified JSON to test parameter coercion
                        registry=mock_registry,
                    )

                    # Should succeed and coerce the page_range
                    assert "labels" in result


@pytest.mark.asyncio
class TestExtractFieldsParameterHandling:
    """Test parameter handling in handle_extract_fields."""

    async def test_extract_fields_with_string_schema(self):
        """Test that stringified schema is properly coerced."""
        with patch("docsray.tools.mistral_tools.download_document"):
            with patch("docsray.tools.mistral_tools.get_local_document"):
                with patch("docsray.tools.mistral_tools.fitz") as mock_fitz:
                    # Mock registry and provider
                    mock_provider = MagicMock()
                    mock_provider._initialized = True
                    mock_provider.config.model = "pixtral-12b-2409"
                    mock_provider.extract_fields = AsyncMock(
                        return_value={
                            "fields": [
                                {
                                    "name": "revenue",
                                    "value": 1000000,
                                    "confidence": 0.98,
                                }
                            ],
                            "errors": [],
                        }
                    )

                    mock_registry = MagicMock()
                    mock_registry.get_provider.return_value = mock_provider

                    # Mock PDF
                    mock_pdf = MagicMock()
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = "Revenue: $1,000,000"
                    mock_pdf.__getitem__.return_value = mock_page
                    mock_pdf.__len__.return_value = 1
                    mock_fitz.open.return_value = mock_pdf

                    # Call with stringified schema
                    schema_str = '{"fields": [{"name": "revenue", "type": "currency"}]}'
                    result = await handle_extract_fields(
                        document_url="test.pdf",
                        schema=schema_str,  # Stringified JSON to test parameter coercion
                        registry=mock_registry,
                    )

                    # Should succeed and coerce the schema
                    assert "fields" in result
                    assert len(result["fields"]) > 0

    async def test_extract_fields_with_string_page_filter(self):
        """Test that stringified page_filter is properly coerced."""
        with patch("docsray.tools.mistral_tools.download_document"):
            with patch("docsray.tools.mistral_tools.get_local_document"):
                with patch("docsray.tools.mistral_tools.fitz") as mock_fitz:
                    # Mock registry and provider
                    mock_provider = MagicMock()
                    mock_provider._initialized = True
                    mock_provider.config.model = "pixtral-12b-2409"
                    mock_provider.extract_fields = AsyncMock(
                        return_value={"fields": [], "errors": []}
                    )

                    mock_registry = MagicMock()
                    mock_registry.get_provider.return_value = mock_provider

                    # Mock PDF
                    mock_pdf = MagicMock()
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = "Sample text"
                    mock_pdf.__getitem__.return_value = mock_page
                    mock_pdf.__len__.return_value = 10
                    mock_fitz.open.return_value = mock_pdf

                    # Call with stringified page_filter
                    result = await handle_extract_fields(
                        document_url="test.pdf",
                        schema={"fields": [{"name": "test", "type": "text"}]},
                        page_filter='{"pages": [1, 5, 10]}',  # Stringified JSON to test parameter coercion
                        registry=mock_registry,
                    )

                    # Should succeed and coerce the page_filter
                    assert "fields" in result


@pytest.mark.asyncio
class TestSummarizeParameterHandling:
    """Test parameter handling in handle_summarize."""

    async def test_summarize_with_string_page_range(self):
        """Test that stringified page_range is properly coerced."""
        with patch("docsray.tools.mistral_tools.download_document"):
            with patch("docsray.tools.mistral_tools.get_local_document"):
                with patch("docsray.tools.mistral_tools.fitz") as mock_fitz:
                    # Mock registry and provider
                    mock_provider = MagicMock()
                    mock_provider._initialized = True
                    mock_provider.config.model = "pixtral-12b-2409"
                    mock_provider.summarize_pages = AsyncMock(
                        return_value=[
                            {"page": 1, "summary": "This is a summary of page 1"}
                        ]
                    )

                    mock_registry = MagicMock()
                    mock_registry.get_provider.return_value = mock_provider

                    # Mock PDF
                    mock_pdf = MagicMock()
                    mock_page = MagicMock()
                    mock_page.get_text.return_value = "Sample page content"
                    mock_pdf.__getitem__.return_value = mock_page
                    mock_pdf.__len__.return_value = 10
                    mock_fitz.open.return_value = mock_pdf

                    # Call with stringified page_range
                    result = await handle_summarize(
                        document_url="test.pdf",
                        page_range='{"start": 1, "end": 10}',  # Stringified JSON to test parameter coercion
                        registry=mock_registry,
                    )

                    # Should succeed and coerce the page_range
                    assert "summaries" in result


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in tools."""

    async def test_classify_pages_no_provider(self):
        """Test error when provider is not available."""
        mock_registry = MagicMock()
        mock_registry.get_provider.return_value = None

        result = await handle_classify_pages(
            document_url="test.pdf", labels=["test"], registry=mock_registry
        )

        assert "error" in result
        assert "Mistral provider not available" in result["error"]

    async def test_extract_fields_provider_not_initialized(self):
        """Test error when provider is not initialized."""
        mock_provider = MagicMock()
        mock_provider._initialized = False

        mock_registry = MagicMock()
        mock_registry.get_provider.return_value = mock_provider

        result = await handle_extract_fields(
            document_url="test.pdf",
            schema={"fields": []},
            registry=mock_registry,
        )

        assert "error" in result
        assert "failed to initialize" in result["error"]
