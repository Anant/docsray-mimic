"""Unit tests for Mistral AI provider."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docsray.config import MistralOCRConfig
from docsray.providers.base import Document
from docsray.providers.mistral import MistralProvider


@pytest.fixture
def mistral_config():
    """Create test Mistral configuration."""
    return MistralOCRConfig(
        enabled=True,
        api_key="test-api-key",
        base_url="https://api.mistral.ai",
        model="mistral-large-latest",
    )


@pytest.fixture
def mistral_provider():
    """Create Mistral provider instance."""
    return MistralProvider()


@pytest.mark.asyncio
class TestMistralProvider:
    """Test suite for MistralProvider."""

    def test_get_name(self, mistral_provider):
        """Test provider name."""
        assert mistral_provider.get_name() == "mistral-ocr"

    def test_get_supported_formats(self, mistral_provider):
        """Test supported formats."""
        formats = mistral_provider.get_supported_formats()
        assert "pdf" in formats
        assert "txt" in formats
        assert "md" in formats

    def test_get_capabilities(self, mistral_provider):
        """Test provider capabilities."""
        caps = mistral_provider.get_capabilities()
        assert "pdf" in caps.formats
        assert caps.features["classification"] is True
        assert caps.features["structuredExtraction"] is True
        assert caps.features["summarization"] is True
        assert caps.features["semanticSearch"] is True

    async def test_initialize_success(self, mistral_provider, mistral_config):
        """Test successful provider initialization."""
        with patch("docsray.providers.mistral.Mistral") as mock_mistral:
            mock_client = MagicMock()
            mock_mistral.return_value = mock_client

            await mistral_provider.initialize(mistral_config)

            assert mistral_provider._initialized is True
            assert mistral_provider._client is not None
            mock_mistral.assert_called_once_with(
                api_key="test-api-key", server_url="https://api.mistral.ai"
            )

    async def test_initialize_no_api_key(self, mistral_provider):
        """Test initialization with no API key."""
        config = MistralOCRConfig(enabled=True, api_key=None)
        await mistral_provider.initialize(config)

        assert mistral_provider._initialized is False

    async def test_initialize_disabled(self, mistral_provider):
        """Test initialization when provider is disabled."""
        config = MistralOCRConfig(enabled=False, api_key="test-key")
        await mistral_provider.initialize(config)

        assert mistral_provider._initialized is False

    async def test_can_process_valid_document(self, mistral_provider, mistral_config):
        """Test can_process with valid document."""
        with patch("docsray.providers.mistral.Mistral"):
            await mistral_provider.initialize(mistral_config)

            doc = Document(url="test.pdf", format="pdf", size=50 * 1024 * 1024)  # 50MB

            result = await mistral_provider.can_process(doc)
            assert result is True

    async def test_can_process_unsupported_format(
        self, mistral_provider, mistral_config
    ):
        """Test can_process with unsupported format."""
        with patch("docsray.providers.mistral.Mistral"):
            await mistral_provider.initialize(mistral_config)

            doc = Document(url="test.xlsx", format="xlsx", size=10 * 1024 * 1024)

            result = await mistral_provider.can_process(doc)
            assert result is False

    async def test_can_process_too_large(self, mistral_provider, mistral_config):
        """Test can_process with file too large."""
        with patch("docsray.providers.mistral.Mistral"):
            await mistral_provider.initialize(mistral_config)

            doc = Document(
                url="test.pdf",
                format="pdf",
                size=200 * 1024 * 1024,  # 200MB, over 100MB limit
            )

            result = await mistral_provider.can_process(doc)
            assert result is False

    async def test_classify_pages_success(self, mistral_provider, mistral_config):
        """Test successful page classification."""
        with patch("docsray.providers.mistral.Mistral") as mock_mistral:
            # Setup mock client
            mock_client = MagicMock()
            mock_mistral.return_value = mock_client

            # Setup mock response
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            mock_message.content = json.dumps(
                [
                    {"page": 1, "label": "income_statement", "confidence": 0.95},
                    {"page": 2, "label": "balance_sheet", "confidence": 0.92},
                ]
            )
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]

            mock_client.chat.complete_async = AsyncMock(return_value=mock_response)

            await mistral_provider.initialize(mistral_config)

            pages = [
                {"page": 1, "textSample": "Income Statement for Year..."},
                {"page": 2, "textSample": "Balance Sheet as of..."},
            ]
            labels = ["income_statement", "balance_sheet", "notes"]

            result = await mistral_provider.classify_pages(pages, labels)

            assert len(result) == 2
            assert result[0]["page"] == 1
            assert result[0]["label"] == "income_statement"
            assert result[0]["confidence"] == 0.95

    async def test_extract_fields_success(self, mistral_provider, mistral_config):
        """Test successful field extraction."""
        with patch("docsray.providers.mistral.Mistral") as mock_mistral:
            # Setup mock client
            mock_client = MagicMock()
            mock_mistral.return_value = mock_client

            # Setup mock response
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            mock_message.content = json.dumps(
                {
                    "fields": [
                        {
                            "name": "total_revenue",
                            "value": 1000000,
                            "confidence": 0.98,
                            "source": {"page": 1},
                        }
                    ],
                    "errors": [],
                }
            )
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]

            mock_client.chat.complete_async = AsyncMock(return_value=mock_response)

            await mistral_provider.initialize(mistral_config)

            schema = {"fields": [{"name": "total_revenue", "type": "currency"}]}
            inputs = [{"page": 1, "text": "Total Revenue: $1,000,000"}]

            result = await mistral_provider.extract_fields(schema, inputs)

            assert len(result["fields"]) == 1
            assert result["fields"][0]["name"] == "total_revenue"
            assert result["fields"][0]["value"] == 1000000
            assert result["fields"][0]["confidence"] == 0.98

    async def test_summarize_pages_success(self, mistral_provider, mistral_config):
        """Test successful page summarization."""
        with patch("docsray.providers.mistral.Mistral") as mock_mistral:
            # Setup mock client
            mock_client = MagicMock()
            mock_mistral.return_value = mock_client

            # Setup mock response
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            mock_message.content = "• Key finding 1\n• Key finding 2\n• Key finding 3"
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]

            mock_client.chat.complete_async = AsyncMock(return_value=mock_response)

            await mistral_provider.initialize(mistral_config)

            pages = [{"page": 1, "text": "Long document text here..."}]

            result = await mistral_provider.summarize_pages(pages, style="bullet")

            assert len(result) == 1
            assert result[0]["page"] == 1
            assert "Key finding" in result[0]["summary"]

    def test_build_classification_prompt(self, mistral_provider):
        """Test classification prompt building."""
        labels = ["income_statement", "balance_sheet", "notes"]
        prompt = mistral_provider._build_classification_prompt(labels)

        assert "income_statement" in prompt
        assert "balance_sheet" in prompt
        assert "confidence" in prompt
        assert "EBITDA" in prompt

    def test_build_extraction_prompt(self, mistral_provider):
        """Test extraction prompt building."""
        schema = {
            "fields": [
                {"name": "total_revenue", "type": "currency"},
                {"name": "fiscal_year_end", "type": "date", "pattern": "YYYY-MM-DD"},
            ]
        }
        prompt = mistral_provider._build_extraction_prompt(schema)

        assert "total_revenue" in prompt
        assert "currency" in prompt
        assert "fiscal_year_end" in prompt
        assert "date" in prompt

    def test_build_summary_prompt(self, mistral_provider):
        """Test summary prompt building."""
        prompt_bullet = mistral_provider._build_summary_prompt("bullet")
        assert "bullet-point" in prompt_bullet

        prompt_para = mistral_provider._build_summary_prompt("paragraph")
        assert "paragraph" in prompt_para

        prompt_exec = mistral_provider._build_summary_prompt("executive")
        assert "executive" in prompt_exec

    def test_validate_classification_result(self, mistral_provider):
        """Test classification result validation."""
        result = [
            {"page": 1, "label": "income_statement", "confidence": 0.95},
            {"page": 2, "label": "balance_sheet", "confidence": 0.92},
            {"page": 3, "label": "invalid_label", "confidence": 0.5},  # Invalid label
            {"page": 4, "label": "notes", "confidence": 1.5},  # Invalid confidence
        ]
        pages = [{"page": i} for i in range(1, 5)]
        labels = ["income_statement", "balance_sheet", "notes"]

        validated = mistral_provider._validate_classification_result(
            result, pages, labels
        )

        assert len(validated) == 2  # Only first 2 are valid
        assert validated[0]["label"] == "income_statement"
        assert validated[1]["label"] == "balance_sheet"

    def test_validate_extraction_result(self, mistral_provider):
        """Test extraction result validation."""
        result = {
            "fields": [
                {"name": "total_revenue", "value": 1000000, "confidence": 0.98},
                {"name": "invalid_field", "value": 500000},  # Missing confidence
            ],
            "errors": [],
        }
        schema = {"fields": [{"name": "total_revenue", "type": "currency"}]}

        validated = mistral_provider._validate_extraction_result(result, schema)

        assert len(validated["fields"]) == 1  # Only first field is valid
        assert validated["fields"][0]["name"] == "total_revenue"

    async def test_dispose(self, mistral_provider, mistral_config):
        """Test provider disposal."""
        with patch("docsray.providers.mistral.Mistral"):
            await mistral_provider.initialize(mistral_config)
            assert mistral_provider._initialized is True

            await mistral_provider.dispose()

            assert mistral_provider._initialized is False
            assert mistral_provider._client is None


@pytest.mark.integration
@pytest.mark.asyncio
class TestMistralProviderIntegration:
    """Integration tests for Mistral provider (requires API key)."""

    @pytest.mark.skip(reason="Requires valid Mistral API key")
    async def test_real_classification(self, mistral_provider):
        """Test real classification with Mistral API."""
        # This test requires MISTRAL_API_KEY environment variable
        import os

        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            pytest.skip("MISTRAL_API_KEY not set")

        config = MistralOCRConfig(
            enabled=True, api_key=api_key, model="mistral-large-latest"
        )

        await mistral_provider.initialize(config)

        pages = [
            {
                "page": 1,
                "textSample": "Income Statement for the Year Ended December 31, 2023",
            }
        ]
        labels = ["income_statement", "balance_sheet", "notes", "other"]

        result = await mistral_provider.classify_pages(pages, labels)

        assert len(result) > 0
        assert result[0]["label"] in labels
        assert 0.0 <= result[0]["confidence"] <= 1.0
