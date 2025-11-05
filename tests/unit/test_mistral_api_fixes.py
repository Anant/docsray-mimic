"""Unit tests for Mistral API fixes (Issue #23)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docsray.config import MistralOCRConfig
from docsray.providers.mistral import MistralProvider


@pytest.fixture
def mistral_provider():
    """Create initialized Mistral provider."""
    provider = MistralProvider()
    provider._initialized = True
    provider.config = MistralOCRConfig(
        enabled=True,
        api_key="test-key",
        model="mistral-large-latest"
    )
    return provider


@pytest.fixture
def mock_mistral_client():
    """Create mock Mistral client."""
    return MagicMock()


class TestClassifyPagesAPIFixes:
    """Test fixes for classify_pages empty response handling."""

    @pytest.mark.asyncio
    async def test_empty_response_choices(self, mistral_provider, mock_mistral_client):
        """Test handling of empty response.choices."""
        mistral_provider._client = mock_mistral_client
        
        # Mock API response with empty choices
        mock_response = MagicMock()
        mock_response.choices = []
        mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)
        
        pages = [{"page": 1, "textSample": "Test"}]
        labels = ["test"]
        
        result = await mistral_provider.classify_pages(pages, labels)
        
        # Should return empty list, not crash
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_content_in_response(self, mistral_provider, mock_mistral_client):
        """Test handling of empty content in response."""
        mistral_provider._client = mock_mistral_client
        
        # Mock API response with empty content
        mock_message = MagicMock()
        mock_message.content = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)
        
        pages = [{"page": 1, "textSample": "Test"}]
        labels = ["test"]
        
        result = await mistral_provider.classify_pages(pages, labels)
        
        # Should return empty list, not crash
        assert result == []

    @pytest.mark.asyncio
    async def test_whitespace_only_content(self, mistral_provider, mock_mistral_client):
        """Test handling of whitespace-only content."""
        mistral_provider._client = mock_mistral_client
        
        # Mock API response with whitespace content
        mock_message = MagicMock()
        mock_message.content = "   \n\t  "
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)
        
        pages = [{"page": 1, "textSample": "Test"}]
        labels = ["test"]
        
        result = await mistral_provider.classify_pages(pages, labels)
        
        # Should return empty list, not crash
        assert result == []

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, mistral_provider, mock_mistral_client):
        """Test handling of invalid JSON in response."""
        mistral_provider._client = mock_mistral_client
        
        # Mock API response with invalid JSON
        mock_message = MagicMock()
        mock_message.content = "This is not valid JSON"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)
        
        pages = [{"page": 1, "textSample": "Test"}]
        labels = ["test"]
        
        result = await mistral_provider.classify_pages(pages, labels)
        
        # Should return empty list, not crash with JSONDecodeError
        assert result == []

    @pytest.mark.asyncio
    async def test_valid_json_object_with_labels(self, mistral_provider, mock_mistral_client):
        """Test handling of valid JSON object with labels array."""
        mistral_provider._client = mock_mistral_client
        
        # Mock valid API response with JSON object format
        valid_response = {
            "labels": [
                {"page": 1, "label": "test", "confidence": 0.9}
            ]
        }
        mock_message = MagicMock()
        mock_message.content = json.dumps(valid_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)
        
        pages = [{"page": 1, "textSample": "Test"}]
        labels = ["test", "other"]
        
        result = await mistral_provider.classify_pages(pages, labels)
        
        # Should successfully parse and validate
        assert len(result) == 1
        assert result[0]["page"] == 1
        assert result[0]["label"] == "test"
        assert result[0]["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_api_call_includes_json_mode(self, mistral_provider, mock_mistral_client):
        """Test that API call includes response_format for JSON mode."""
        mistral_provider._client = mock_mistral_client
        
        # Mock valid response
        valid_response = {"labels": [{"page": 1, "label": "test", "confidence": 0.9}]}
        mock_message = MagicMock()
        mock_message.content = json.dumps(valid_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)
        
        pages = [{"page": 1, "textSample": "Test"}]
        labels = ["test"]
        
        await mistral_provider.classify_pages(pages, labels)
        
        # Verify response_format was included in call
        call_kwargs = mock_mistral_client.chat.complete_async.call_args[1]
        assert "response_format" in call_kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}


class TestExtractFieldsAPIFixes:
    """Test fixes for extract_fields JSON parsing errors."""

    @pytest.mark.asyncio
    async def test_empty_response_choices(self, mistral_provider, mock_mistral_client):
        """Test handling of empty response.choices."""
        mistral_provider._client = mock_mistral_client
        
        # Mock API response with empty choices
        mock_response = MagicMock()
        mock_response.choices = []
        mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)
        
        schema = {"fields": [{"name": "test", "type": "text"}]}
        inputs = [{"page": 1, "text": "Test"}]
        
        result = await mistral_provider.extract_fields(schema, inputs)
        
        # Should return empty fields with error, not crash
        assert result["fields"] == []
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, mistral_provider, mock_mistral_client):
        """Test handling of invalid JSON in response."""
        mistral_provider._client = mock_mistral_client
        
        # Mock API response with invalid JSON
        mock_message = MagicMock()
        mock_message.content = "Not valid JSON"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)
        
        schema = {"fields": [{"name": "test", "type": "text"}]}
        inputs = [{"page": 1, "text": "Test"}]
        
        result = await mistral_provider.extract_fields(schema, inputs)
        
        # Should return empty fields with error, not crash with JSONDecodeError
        assert result["fields"] == []
        assert len(result["errors"]) > 0
        assert "JSON" in str(result["errors"][0])

    @pytest.mark.asyncio
    async def test_valid_json_object_with_fields(self, mistral_provider, mock_mistral_client):
        """Test handling of valid JSON object with fields array."""
        mistral_provider._client = mock_mistral_client
        
        # Mock valid API response
        valid_response = {
            "fields": [
                {
                    "name": "revenue",
                    "value": 100000,
                    "confidence": 0.95,
                    "source": {"page": 1}
                }
            ],
            "errors": []
        }
        mock_message = MagicMock()
        mock_message.content = json.dumps(valid_response)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_mistral_client.chat.complete_async = AsyncMock(return_value=mock_response)
        
        schema = {"fields": [{"name": "revenue", "type": "currency"}]}
        inputs = [{"page": 1, "text": "Revenue: $100,000"}]
        
        result = await mistral_provider.extract_fields(schema, inputs)
        
        # Should successfully parse and validate
        assert len(result["fields"]) == 1
        assert result["fields"][0]["name"] == "revenue"
        assert result["fields"][0]["value"] == 100000
        assert result["fields"][0]["confidence"] == 0.95


class TestValidationImprovements:
    """Test improved validation logic."""

    def test_classification_validation_handles_invalid_labels(self, mistral_provider):
        """Test validation rejects invalid labels."""
        result = [
            {"page": 1, "label": "valid_label", "confidence": 0.9},
            {"page": 2, "label": "invalid_label", "confidence": 0.8},
        ]
        labels = ["valid_label", "other"]
        
        validated = mistral_provider._validate_classification_result(result, [], labels)
        
        # Should only keep valid label
        assert len(validated) == 1
        assert validated[0]["label"] == "valid_label"

    def test_classification_validation_handles_invalid_confidence(self, mistral_provider):
        """Test validation rejects invalid confidence scores."""
        result = [
            {"page": 1, "label": "test", "confidence": 0.9},
            {"page": 2, "label": "test", "confidence": 1.5},  # Invalid
            {"page": 3, "label": "test", "confidence": -0.1},  # Invalid
        ]
        labels = ["test"]
        
        validated = mistral_provider._validate_classification_result(result, [], labels)
        
        # Should only keep valid confidence
        assert len(validated) == 1
        assert validated[0]["page"] == 1

    def test_classification_validation_handles_missing_keys(self, mistral_provider):
        """Test validation rejects items with missing keys."""
        result = [
            {"page": 1, "label": "test", "confidence": 0.9},
            {"page": 2, "label": "test"},  # Missing confidence
            {"page": 3, "confidence": 0.8},  # Missing label
        ]
        labels = ["test"]
        
        validated = mistral_provider._validate_classification_result(result, [], labels)
        
        # Should only keep complete item
        assert len(validated) == 1
        assert validated[0]["page"] == 1

    def test_extraction_validation_handles_missing_keys(self, mistral_provider):
        """Test validation rejects fields with missing keys."""
        result = {
            "fields": [
                {"name": "field1", "value": "test", "confidence": 0.9},
                {"name": "field2", "value": "test"},  # Missing confidence
                {"value": "test", "confidence": 0.8},  # Missing name
            ],
            "errors": []
        }
        schema = {"fields": []}
        
        validated = mistral_provider._validate_extraction_result(result, schema)
        
        # Should only keep complete field
        assert len(validated["fields"]) == 1
        assert validated["fields"][0]["name"] == "field1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
