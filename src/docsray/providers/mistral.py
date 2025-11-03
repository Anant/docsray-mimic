"""Mistral AI provider for document intelligence tasks."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import MistralOCRConfig
from ..utils.documents import download_document, get_document_format, get_local_document, is_url
from .base import (
    Document,
    DocumentProvider,
    ExtractResult,
    MapResult,
    PeekResult,
    ProviderCapabilities,
    SeekResult,
    XrayResult,
)

logger = logging.getLogger(__name__)


class MistralProvider(DocumentProvider):
    """Mistral AI provider for document intelligence and analysis.
    
    This provider offers AI-powered capabilities like:
    - Page classification (document types)
    - Structured field extraction
    - Document summarization
    - Semantic understanding
    """

    def __init__(self):
        self.config: Optional[MistralOCRConfig] = None
        self._initialized = False
        self._client = None

    def get_name(self) -> str:
        return "mistral-ocr"

    def get_supported_formats(self) -> List[str]:
        return ["pdf", "txt", "md", "docx", "html"]

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            formats=self.get_supported_formats(),
            features={
                "ocr": True,
                "tables": True,
                "images": True,
                "forms": True,
                "multiLanguage": True,
                "streaming": False,
                "customInstructions": True,
                "semanticSearch": True,
                "classification": True,
                "structuredExtraction": True,
                "summarization": True,
            },
            performance={
                "maxFileSize": 100 * 1024 * 1024,  # 100MB
                "averageSpeed": 5,  # pages per second (AI processing is slower)
            }
        )

    async def can_process(self, document: Document) -> bool:
        """Check if provider can process the document."""
        if not self._initialized or not self._client:
            return False

        # Check format
        doc_format = document.format or get_document_format(document.url)
        if doc_format and doc_format.lower() not in self.get_supported_formats():
            return False

        # Check size limit
        if document.size:
            max_size = self.get_capabilities().performance["maxFileSize"]
            if document.size > max_size:
                return False

        return True

    async def initialize(self, config: MistralOCRConfig) -> None:
        """Initialize Mistral provider with configuration."""
        self.config = config
        
        if not config.enabled:
            logger.info("Mistral provider is disabled")
            self._initialized = False
            return

        if not config.api_key:
            logger.warning("Mistral API key not provided")
            self._initialized = False
            return

        try:
            from mistralai import Mistral
            self._client = Mistral(api_key=config.api_key, server_url=config.base_url)
            self._initialized = True
            logger.info(f"Mistral provider initialized with model: {config.model}")
        except ImportError:
            logger.error("mistralai package not installed. Install with: pip install mistralai")
            self._initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize Mistral client: {e}")
            self._initialized = False

    async def dispose(self) -> None:
        """Cleanup provider resources."""
        self._client = None
        self._initialized = False

    async def peek(self, document: Document, options: Dict[str, Any]) -> PeekResult:
        """Get document overview using Mistral AI."""
        if not self._initialized:
            raise RuntimeError("Mistral provider not initialized")

        doc_path = await self._ensure_local_document(document)
        
        # Extract basic metadata
        metadata = {
            "provider": self.get_name(),
            "format": document.format or get_document_format(document.url),
            "size": doc_path.stat().st_size if doc_path.exists() else document.size,
        }

        # For peek, we'll provide basic document info
        # Deep analysis happens in xray
        structure = {
            "type": "document",
            "path": str(doc_path),
        }

        return PeekResult(
            metadata=metadata,
            structure=structure,
        )

    async def map(self, document: Document, options: Dict[str, Any]) -> MapResult:
        """Generate document structure map."""
        if not self._initialized:
            raise RuntimeError("Mistral provider not initialized")

        # For Mistral, mapping would involve analyzing document structure
        # This is a simplified implementation
        doc_map = {
            "provider": self.get_name(),
            "sections": [],
            "ai_powered": True,
        }

        return MapResult(document_map=doc_map)

    async def seek(self, document: Document, target: Dict[str, Any]) -> SeekResult:
        """Navigate to specific location in document using AI understanding."""
        if not self._initialized:
            raise RuntimeError("Mistral provider not initialized")

        # Mistral can use semantic understanding for seek operations
        location = {
            "found": False,
            "message": "Semantic seek not yet implemented",
        }

        return SeekResult(location=location)

    async def xray(self, document: Document, options: Dict[str, Any]) -> XrayResult:
        """Perform deep document analysis using Mistral AI.
        
        This is where Mistral's AI capabilities shine:
        - Document classification
        - Key entity extraction
        - Relationship mapping
        - Semantic understanding
        """
        if not self._initialized:
            raise RuntimeError("Mistral provider not initialized")

        doc_path = await self._ensure_local_document(document)
        
        # Extract text content for analysis
        content = await self._extract_text(doc_path)
        
        # Use Mistral for deep analysis
        analysis = await self._analyze_content(content, options)
        
        return XrayResult(
            analysis=analysis,
            confidence=analysis.get("confidence", 0.0),
            provider_info={
                "provider": self.get_name(),
                "model": self.config.model if self.config else "unknown",
            }
        )

    async def extract(self, document: Document, options: Dict[str, Any]) -> ExtractResult:
        """Extract content from document."""
        if not self._initialized:
            raise RuntimeError("Mistral provider not initialized")

        doc_path = await self._ensure_local_document(document)
        content = await self._extract_text(doc_path)
        
        # Mistral can enhance extraction with structure understanding
        extract_format = options.get("format", "text")
        
        if extract_format == "structured":
            # Use Mistral for structured extraction
            content = await self._structured_extract(content, options)
        
        return ExtractResult(
            content=content,
            format=extract_format,
        )

    # Helper methods

    async def _ensure_local_document(self, document: Document) -> Path:
        """Ensure document is available locally."""
        if document.path and document.path.exists():
            return document.path
        
        if is_url(document.url):
            return await download_document(document.url)
        
        return await get_local_document(document.url)

    async def _extract_text(self, doc_path: Path) -> str:
        """Extract text from document.
        
        For PDFs, we'll use PyMuPDF as a fallback.
        Mistral OCR would be used for images/scanned content.
        """
        if doc_path.suffix.lower() == '.pdf':
            try:
                import fitz
                pdf = fitz.open(str(doc_path))
                text = "\n\n".join(page.get_text() for page in pdf)
                pdf.close()
                return text
            except Exception as e:
                logger.error(f"Failed to extract text from PDF: {e}")
                return ""
        elif doc_path.suffix.lower() in ['.txt', '.md']:
            return doc_path.read_text(encoding='utf-8')
        else:
            logger.warning(f"Unsupported format for text extraction: {doc_path.suffix}")
            return ""

    async def _analyze_content(self, content: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content using Mistral AI."""
        if not self._client:
            return {"error": "Mistral client not initialized"}

        try:
            # Truncate content if too long (Mistral has token limits)
            max_chars = options.get("max_chars", 8000)
            if len(content) > max_chars:
                content = content[:max_chars] + "\n\n[Content truncated...]"

            # Create analysis prompt
            system_prompt = options.get(
                "system_prompt",
                "You are a document analysis assistant. Analyze the following document and provide key insights."
            )

            # Call Mistral API
            from mistralai.models import UserMessage, SystemMessage
            
            response = await self._client.chat.complete_async(
                model=self.config.model if self.config else "mistral-ocr-latest",
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=content),
                ]
            )

            analysis_text = response.choices[0].message.content if response.choices else "No analysis generated"
            
            return {
                "analysis": analysis_text,
                "confidence": 0.85,  # Placeholder confidence score
                "model": self.config.model if self.config else "mistral-ocr-latest",
            }

        except Exception as e:
            logger.error(f"Mistral analysis failed: {e}")
            return {
                "error": str(e),
                "confidence": 0.0,
            }

    async def _structured_extract(self, content: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data using Mistral AI."""
        if not self._client:
            return {"error": "Mistral client not initialized"}

        try:
            schema = options.get("schema", {})
            
            # Create extraction prompt
            system_prompt = f"""Extract structured data from the following document.
Return a JSON object with the requested fields: {json.dumps(schema)}"""

            from mistralai.models import UserMessage, SystemMessage
            
            response = await self._client.chat.complete_async(
                model=self.config.model if self.config else "mistral-ocr-latest",
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=content),
                ]
            )

            result_text = response.choices[0].message.content if response.choices else "{}"
            
            # Try to parse as JSON
            try:
                return json.loads(result_text)
            except json.JSONDecodeError:
                return {"raw_result": result_text}

        except Exception as e:
            logger.error(f"Structured extraction failed: {e}")
            return {"error": str(e)}

    # New methods for specialized AI capabilities

    async def classify_pages(
        self,
        pages: List[Dict[str, Any]],
        labels: List[str],
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Classify document pages into predefined categories.
        
        Args:
            pages: List of page dicts with 'page' and 'textSample' keys
            labels: Valid classification labels
            model: Mistral model to use (default: from config)
            system_prompt: Custom system prompt (optional)
            temperature: Sampling temperature (0-1)
        
        Returns:
            List of dicts with 'page', 'label', 'confidence' keys
        """
        if not self._client:
            raise RuntimeError("Mistral client not initialized")

        model = model or (self.config.model if self.config else "mistral-large-latest")
        
        if system_prompt is None:
            system_prompt = self._build_classification_prompt(labels)

        try:
            from mistralai.models import UserMessage, SystemMessage
            
            response = await self._client.chat.complete_async(
                model=model,
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=json.dumps(pages)),
                ],
                temperature=temperature,
            )

            result_text = response.choices[0].message.content if response.choices else "[]"
            result = json.loads(result_text)
            
            return self._validate_classification_result(result, pages, labels)

        except Exception as e:
            logger.error(f"Page classification failed: {e}")
            return []

    async def extract_fields(
        self,
        schema: Dict[str, Any],
        inputs: List[Dict[str, Any]],
        model: Optional[str] = None,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """Extract structured fields from document text.
        
        Args:
            schema: Field definitions with name, type, pattern
            inputs: List of page dicts with 'page' and 'text' keys
            model: Mistral model to use
            temperature: Sampling temperature
        
        Returns:
            Dict with 'fields' array and optional 'errors' array
        """
        if not self._client:
            raise RuntimeError("Mistral client not initialized")

        model = model or (self.config.model if self.config else "mistral-large-latest")
        system_prompt = self._build_extraction_prompt(schema)

        try:
            from mistralai.models import UserMessage, SystemMessage
            
            response = await self._client.chat.complete_async(
                model=model,
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=json.dumps(inputs)),
                ],
                temperature=temperature,
            )

            result_text = response.choices[0].message.content if response.choices else "{}"
            result = json.loads(result_text)
            
            return self._validate_extraction_result(result, schema)

        except Exception as e:
            logger.error(f"Field extraction failed: {e}")
            return {"fields": [], "errors": [str(e)]}

    async def summarize_pages(
        self,
        pages: List[Dict[str, Any]],
        style: str = "bullet",
        model: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Generate summaries for document pages.
        
        Args:
            pages: List of page dicts with 'page' and 'text' keys
            style: Summary style (bullet, paragraph, executive)
            model: Mistral model to use (default: mistral-small-latest)
            max_tokens: Maximum tokens per summary
            temperature: Sampling temperature
        
        Returns:
            List of dicts with 'page' and 'summary' keys
        """
        if not self._client:
            raise RuntimeError("Mistral client not initialized")

        model = model or "mistral-small-latest"
        summaries = []

        for page in pages:
            try:
                system_prompt = self._build_summary_prompt(style)
                
                from mistralai.models import UserMessage, SystemMessage
                
                response = await self._client.chat.complete_async(
                    model=model,
                    messages=[
                        SystemMessage(content=system_prompt),
                        UserMessage(content=page["text"]),
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                summary_text = response.choices[0].message.content if response.choices else ""
                
                summaries.append({
                    "page": page["page"],
                    "summary": summary_text
                })

            except Exception as e:
                logger.error(f"Summarization failed for page {page.get('page')}: {e}")
                summaries.append({
                    "page": page.get("page"),
                    "summary": f"Error: {str(e)}"
                })

        return summaries

    def _build_classification_prompt(self, labels: List[str]) -> str:
        """Build system prompt for page classification."""
        return f"""You are analyzing a company's annual report. Below is a list of pages with page numbers 
and text samples. Classify each page into one of these categories: {', '.join(labels)}.

Return JSON array with format: [{{"page": int, "label": string, "confidence": float}}].

Rules:
- Do not include EBITDA reconciliation pages under income_statement
- Multi-page sections should have same label across consecutive pages
- Use 'other' for unclassifiable pages
- Confidence must be between 0.0 and 1.0"""

    def _build_extraction_prompt(self, schema: Dict[str, Any]) -> str:
        """Build system prompt for field extraction."""
        fields_desc = "\n".join([
            f"- {f['name']} (type: {f['type']}, pattern: {f.get('pattern', 'any')})"
            for f in schema.get("fields", [])
        ])
        
        return f"""Extract the following fields from financial statement text:
{fields_desc}

Return JSON with format: [{{"name": string, "value": typed_value, "confidence": float, 
"source": {{"page": int, "lineIdx": int?}}}}].

Rules:
- Return null for missing fields
- Include confidence score (0.0-1.0)
- Preserve data types (numbers as numbers, dates as ISO strings)
- Extract source page and line index when possible"""

    def _build_summary_prompt(self, style: str) -> str:
        """Build system prompt for summarization."""
        style_instructions = {
            "bullet": "Create a concise bullet-point summary (3-5 points).",
            "paragraph": "Write a single paragraph summary (3-4 sentences).",
            "executive": "Provide an executive summary highlighting key insights."
        }
        
        return f"""Summarize the following page content. 
{style_instructions.get(style, style_instructions['bullet'])}

Focus on factual information and key data points. Avoid speculation."""

    def _validate_classification_result(
        self,
        result: Any,
        pages: List[Dict],
        labels: List[str]
    ) -> List[Dict[str, Any]]:
        """Validate and clean classification results."""
        if not isinstance(result, list):
            result = result.get("labels", []) if isinstance(result, dict) else []
        
        validated = []
        for item in result:
            if isinstance(item, dict) and all(k in item for k in ["page", "label", "confidence"]):
                if item["label"] in labels or item["label"] == "other":
                    if 0.0 <= item["confidence"] <= 1.0:
                        validated.append(item)
        
        return validated

    def _validate_extraction_result(
        self,
        result: Any,
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and clean extraction results."""
        if not isinstance(result, dict):
            return {"fields": [], "errors": ["Invalid result format"]}
        
        fields = result.get("fields", [])
        errors = result.get("errors", [])
        
        validated_fields = []
        for field in fields:
            if isinstance(field, dict) and all(k in field for k in ["name", "value", "confidence"]):
                validated_fields.append(field)
        
        return {
            "fields": validated_fields,
            "errors": errors
        }
