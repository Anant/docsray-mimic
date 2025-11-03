"""MCP tools for Mistral AI-powered document intelligence."""

import logging
from pathlib import Path
from typing import Any, Optional

from ..providers.base import Document
from ..providers.registry import ProviderRegistry
from ..utils.cache import DocumentCache
from ..utils.documents import download_document, get_local_document, is_url

logger = logging.getLogger(__name__)


async def handle_classify_pages(
    document_url: str,
    labels: list[str],
    model: Optional[str] = None,
    page_range: Optional[dict[str, int]] = None,
    registry: Optional[ProviderRegistry] = None,
    cache: Optional[DocumentCache] = None,
) -> dict[str, Any]:
    """Classify pages in a PDF document using Mistral AI.

    Args:
        document_url: URL or local path to document
        labels: Valid classification labels
        model: Mistral model to use (default: mistral-large-latest)
        page_range: Optional page range to classify (start, end)
        registry: Provider registry
        cache: Document cache

    Returns:
        Classification results with page labels and confidence scores
    """
    try:
        # Get Mistral provider
        provider = registry.get_provider("mistral-ocr") if registry else None
        if not provider:
            return {
                "error": "Mistral provider not available",
                "suggestion": "Enable Mistral provider with DOCSRAY_MISTRAL_ENABLED=true and provide API key",
            }

        # Initialize provider if not already initialized
        if not provider._initialized and hasattr(provider, "initialize"):
            await provider.initialize(provider.config)

        if not provider._initialized:
            return {
                "error": "Mistral provider failed to initialize",
                "suggestion": "Check DOCSRAY_MISTRAL_API_KEY is set correctly",
            }

        # Create document object
        doc = Document(url=document_url)

        # Ensure we can process this document
        if not await provider.can_process(doc):
            return {
                "error": "Document cannot be processed by Mistral provider",
                "format": doc.format,
            }

        # Extract text from pages for classification
        # For now, we'll use a simplified approach with text extraction
        from ..providers.mistral import MistralProvider

        if not isinstance(provider, MistralProvider):
            return {"error": "Provider is not a Mistral provider"}

        # Get document path
        if is_url(document_url):
            doc_path = await download_document(document_url)
        else:
            doc_path = await get_local_document(document_url)

        doc.path = doc_path

        # Extract text and create page samples
        pages = await _extract_page_samples(doc_path, page_range)

        # Classify pages using Mistral
        results = await provider.classify_pages(
            pages=pages, labels=labels, model=model, temperature=0.0
        )

        return {
            "labels": results,
            "total_pages": len(pages),
            "model": model or provider.config.model,
            "provider": "mistral-ocr",
        }

    except Exception as e:
        logger.error(f"Page classification failed: {e}")
        return {"error": str(e), "type": type(e).__name__}


async def handle_extract_fields(
    document_url: str,
    schema: dict[str, Any],
    page_filter: Optional[dict[str, Any]] = None,
    model: Optional[str] = None,
    registry: Optional[ProviderRegistry] = None,
    cache: Optional[DocumentCache] = None,
) -> dict[str, Any]:
    """Extract structured fields from document pages using Mistral AI.

    Args:
        document_url: URL or local path to document
        schema: Field definitions to extract
        page_filter: Optional filter for which pages to extract from
        model: Mistral model to use
        registry: Provider registry
        cache: Document cache

    Returns:
        Extracted fields with values, confidence scores, and source tracking
    """
    try:
        # Get Mistral provider
        provider = registry.get_provider("mistral-ocr") if registry else None
        if not provider:
            return {
                "error": "Mistral provider not available",
                "suggestion": "Enable Mistral provider with DOCSRAY_MISTRAL_ENABLED=true",
            }

        # Initialize provider if needed
        if not provider._initialized and hasattr(provider, "initialize"):
            await provider.initialize(provider.config)

        if not provider._initialized:
            return {
                "error": "Mistral provider failed to initialize",
                "suggestion": "Check DOCSRAY_MISTRAL_API_KEY is set correctly",
            }

        # Create document object
        doc = Document(url=document_url)

        # Get document path
        if is_url(document_url):
            doc_path = await download_document(document_url)
        else:
            doc_path = await get_local_document(document_url)

        doc.path = doc_path

        # Extract text from pages
        pages = await _extract_page_text(doc_path, page_filter)

        # Extract fields using Mistral
        from ..providers.mistral import MistralProvider

        if not isinstance(provider, MistralProvider):
            return {"error": "Provider is not a Mistral provider"}

        results = await provider.extract_fields(
            schema=schema, inputs=pages, model=model, temperature=0.0
        )

        return {
            "fields": results.get("fields", []),
            "errors": results.get("errors", []),
            "total_pages_processed": len(pages),
            "model": model or provider.config.model,
            "provider": "mistral-ocr",
        }

    except Exception as e:
        logger.error(f"Field extraction failed: {e}")
        return {"error": str(e), "type": type(e).__name__}


async def handle_summarize(
    document_url: str,
    style: str = "bullet",
    page_range: Optional[dict[str, int]] = None,
    model: Optional[str] = None,
    max_tokens: int = 512,
    registry: Optional[ProviderRegistry] = None,
    cache: Optional[DocumentCache] = None,
) -> dict[str, Any]:
    """Generate summaries of PDF pages using Mistral AI.

    Args:
        document_url: URL or local path to document
        style: Summary style (bullet, paragraph, executive)
        page_range: Optional page range to summarize
        model: Mistral model to use
        max_tokens: Maximum tokens per summary
        registry: Provider registry
        cache: Document cache

    Returns:
        Page summaries
    """
    try:
        # Get Mistral provider
        provider = registry.get_provider("mistral-ocr") if registry else None
        if not provider:
            return {
                "error": "Mistral provider not available",
                "suggestion": "Enable Mistral provider with DOCSRAY_MISTRAL_ENABLED=true",
            }

        # Initialize provider if needed
        if not provider._initialized and hasattr(provider, "initialize"):
            await provider.initialize(provider.config)

        if not provider._initialized:
            return {"error": "Mistral provider failed to initialize"}

        # Create document object
        doc = Document(url=document_url)

        # Get document path
        if is_url(document_url):
            doc_path = await download_document(document_url)
        else:
            doc_path = await get_local_document(document_url)

        doc.path = doc_path

        # Extract text from pages
        pages = await _extract_page_text(
            doc_path, {"range": page_range} if page_range else None
        )

        # Summarize pages using Mistral
        from ..providers.mistral import MistralProvider

        if not isinstance(provider, MistralProvider):
            return {"error": "Provider is not a Mistral provider"}

        summaries = await provider.summarize_pages(
            pages=pages,
            style=style,
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
        )

        return {
            "summaries": summaries,
            "total_pages": len(pages),
            "style": style,
            "model": model or "mistral-small-latest",
            "provider": "mistral-ocr",
        }

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return {"error": str(e), "type": type(e).__name__}


# Helper functions


async def _extract_page_samples(
    doc_path: Path, page_range: Optional[dict[str, int]] = None
) -> list[dict[str, Any]]:
    """Extract text samples from document pages for classification.

    Args:
        doc_path: Path to document
        page_range: Optional page range (start, end)

    Returns:
        List of page dicts with page number and text sample
    """
    pages = []

    try:
        import fitz  # PyMuPDF

        pdf = fitz.open(str(doc_path))
        start = page_range.get("start", 1) if page_range else 1
        end = page_range.get("end", len(pdf)) if page_range else len(pdf)

        for page_num in range(start - 1, end):  # PyMuPDF uses 0-based indexing
            if page_num >= len(pdf):
                break

            page = pdf[page_num]
            text = page.get_text()

            # Take first 70 characters as sample for classification
            text_sample = text[:70].strip() if text else ""

            pages.append(
                {
                    "page": page_num + 1,  # 1-based for user-facing output
                    "textSample": text_sample,
                }
            )

        pdf.close()

    except Exception as e:
        logger.error(f"Failed to extract page samples: {e}")

    return pages


async def _extract_page_text(
    doc_path: Path, page_filter: Optional[dict[str, Any]] = None
) -> list[dict[str, Any]]:
    """Extract full text from document pages.

    Args:
        doc_path: Path to document
        page_filter: Optional filter (pages list or range)

    Returns:
        List of page dicts with page number and full text
    """
    pages = []

    try:
        import fitz  # PyMuPDF

        pdf = fitz.open(str(doc_path))

        # Determine which pages to extract
        if page_filter:
            if "pages" in page_filter:
                page_nums = page_filter["pages"]
            elif "range" in page_filter:
                page_range = page_filter["range"]
                start = page_range.get("start", 1)
                end = page_range.get("end", len(pdf))
                page_nums = list(range(start, end + 1))
            else:
                page_nums = list(range(1, len(pdf) + 1))
        else:
            page_nums = list(range(1, len(pdf) + 1))

        for page_num in page_nums:
            if page_num < 1 or page_num > len(pdf):
                continue

            page = pdf[page_num - 1]  # PyMuPDF uses 0-based indexing
            text = page.get_text()

            pages.append({"page": page_num, "text": text})

        pdf.close()

    except Exception as e:
        logger.error(f"Failed to extract page text: {e}")

    return pages
