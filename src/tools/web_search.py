import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO

import requests

from .base import Tool, ToolResult

logger = logging.getLogger(__name__)

DEFAULT_FETCH_TIMEOUT = 8
DEFAULT_MAX_CHARS_PER_PAGE = 3000

# For PDF chunks
DEFAULT_PDF_CHUNK_SIZE = 2500
DEFAULT_PDF_CHUNK_OVERLAP = 300

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


class WebSearchTool(Tool):
    """
    Web search tool with support for:

    - HTML pages
    - Text-based PDFs
    - Scanned PDFs using OCR
    - PDF page numbers
    - PDF chunking

    PDF content is extracted from all pages and divided into
    smaller chunks so the LLM can work with relevant information
    without receiving the entire PDF at once.
    """

    name = "web_search"

    description = (
        "Search the web for current or recent information not covered by "
        "the internal climate finance knowledge base. Useful for recent "
        "news, statistics, reports, events, and PDF documents. Supports "
        "HTML pages, text-based PDFs, and scanned PDFs using OCR. PDF "
        "content is extracted with page numbers and divided into chunks."
    )

    def __init__(
        self,
        max_results: int = 5,
        fetch_full_content: bool = True,
        max_chars_per_page: int = DEFAULT_MAX_CHARS_PER_PAGE,
        fetch_timeout: int = DEFAULT_FETCH_TIMEOUT,
        max_workers: int = 5,
        enable_ocr: bool = True,
        ocr_language: str = "eng",
        pdf_chunk_size: int = DEFAULT_PDF_CHUNK_SIZE,
        pdf_chunk_overlap: int = DEFAULT_PDF_CHUNK_OVERLAP,
    ):
        self.max_results = max_results
        self.fetch_full_content = fetch_full_content
        self.max_chars_per_page = max_chars_per_page
        self.fetch_timeout = fetch_timeout
        self.max_workers = max_workers

        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language

        self.pdf_chunk_size = pdf_chunk_size
        self.pdf_chunk_overlap = pdf_chunk_overlap

    # ============================================================
    # SEARCH
    # ============================================================

    def run(self, query: str = "", **kwargs) -> ToolResult:

        if not query:
            return ToolResult(
                success=False,
                error="No query provided."
            )

        try:
            from ddgs import DDGS

        except ImportError:

            try:
                from duckduckgo_search import DDGS

            except ImportError:

                return ToolResult(
                    success=False,
                    error=(
                        "Web search library not installed. "
                        "Run: pip install ddgs"
                    ),
                )

        actual_max_results = kwargs.get(
            "max_results",
            self.max_results
        )

        fetch_full_content = kwargs.get(
            "fetch_full_content",
            self.fetch_full_content
        )

        try:

            with DDGS() as ddgs:

                raw_results = list(
                    ddgs.text(
                        query,
                        max_results=actual_max_results
                    )
                )

        except Exception as e:

            logger.error(
                "Web search failed: %s",
                e
            )

            return ToolResult(
                success=False,
                error=str(e)
            )

        results = [
            {
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
                "content": "",
                "content_type": "",
                "chunks": [],
            }
            for r in raw_results
        ]

        if not results:

            return ToolResult(
                success=False,
                error=f"No web results found for query: {query}",
            )

        if fetch_full_content:

            self._attach_full_content(results)

        else:

            for r in results:
                r["content"] = r["snippet"]

        logger.info(
            "Web search returned %d results for: %s",
            len(results),
            query[:50]
        )

        return ToolResult(
            success=True,
            data=results
        )

    # ============================================================
    # FETCH RESULTS IN PARALLEL
    # ============================================================

    def _attach_full_content(self, results: list) -> None:

        workers = max(
            1,
            min(
                self.max_workers,
                len(results)
            )
        )

        with ThreadPoolExecutor(
            max_workers=workers
        ) as executor:

            future_to_result = {
                executor.submit(
                    self._fetch_page_text,
                    r["url"]
                ): r
                for r in results
            }

            for future in as_completed(
                future_to_result
            ):

                result = future_to_result[future]

                try:

                    text, content_type = future.result()

                except Exception as e:

                    logger.warning(
                        "Failed to fetch %s: %s",
                        result["url"],
                        e
                    )

                    text = ""
                    content_type = ""

                result["content_type"] = content_type

                snippet = result["snippet"]

                if text and len(
                    text
                ) >= max(
                    len(snippet),
                    200
                ):

                    result["content"] = text

                else:

                    result["content"] = (
                        snippet or text
                    )

                # =================================================
                # CREATE PDF CHUNKS
                # =================================================

                if content_type == "application/pdf" and text:

                    result["chunks"] = (
                        self._chunk_pdf_content(text)
                    )

    # ============================================================
    # FETCH HTML OR PDF
    # ============================================================

    def _fetch_page_text(
        self,
        url: str
    ) -> tuple[str, str]:

        if not url:
            return "", ""

        try:

            response = requests.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=self.fetch_timeout
            )

            response.raise_for_status()

        except Exception as e:

            logger.warning(
                "Request failed for %s: %s",
                url,
                e
            )

            return "", ""

        content_type = response.headers.get(
            "Content-Type",
            ""
        ).lower()

        # ========================================================
        # PDF
        # ========================================================

        is_pdf = (
            "application/pdf" in content_type
            or self._looks_like_pdf_url(url)
        )

        if is_pdf:

            text = self._extract_pdf_text(
                response.content
            )

            # IMPORTANT:
            # Do NOT truncate PDF content here.
            # We want all pages before chunking.

            return (
                text,
                "application/pdf"
            )

        # ========================================================
        # NON HTML
        # ========================================================

        if (
            "html" not in content_type
            and content_type
        ):

            return "", content_type

        # ========================================================
        # HTML
        # ========================================================

        text = self._extract_with_trafilatura(
            response.text
        )

        if not text:

            text = self._extract_with_bs4(
                response.text
            )

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        # HTML stays limited
        text = text[
            :self.max_chars_per_page
        ]

        return (
            text,
            "text/html"
        )

    # ============================================================
    # PDF URL DETECTION
    # ============================================================

    @staticmethod
    def _looks_like_pdf_url(
        url: str
    ) -> bool:

        clean_url = (
            url
            .lower()
            .split("?")[0]
            .split("#")[0]
        )

        return clean_url.endswith(".pdf")

    # ============================================================
    # PDF EXTRACTION
    # ============================================================

    def _extract_pdf_text(
        self,
        pdf_bytes: bytes
    ) -> str:

        text = self._extract_pdf_with_pypdf(
            pdf_bytes
        )

        # Normal PDF
        if text and len(
            text.strip()
        ) >= 100:

            logger.info(
                "PDF text extraction successful."
            )

            return text

        # Scanned PDF
        if self.enable_ocr:

            logger.info(
                "PDF appears to be scanned. "
                "Trying OCR..."
            )

            ocr_text = (
                self._extract_pdf_with_ocr(
                    pdf_bytes
                )
            )

            if ocr_text:
                return ocr_text

        return text or ""

    # ============================================================
    # PYPDF
    # ============================================================

    @staticmethod
    def _extract_pdf_with_pypdf(
        pdf_bytes: bytes
    ) -> str:

        try:

            from pypdf import PdfReader

        except ImportError:

            logger.warning(
                "pypdf is not installed. "
                "Run: pip install pypdf"
            )

            return ""

        try:

            reader = PdfReader(
                BytesIO(pdf_bytes)
            )

            pages = []

            for page_number, page in enumerate(
                reader.pages,
                start=1
            ):

                try:

                    page_text = (
                        page.extract_text()
                        or ""
                    ).strip()

                    page_text = re.sub(
                        r"\s+",
                        " ",
                        page_text
                    )

                    if page_text:

                        pages.append(
                            f"[Page {page_number}]\n"
                            f"{page_text}"
                        )

                except Exception as e:

                    logger.warning(
                        "Failed to extract "
                        "PDF page %d: %s",
                        page_number,
                        e
                    )

            return "\n\n".join(
                pages
            )

        except Exception as e:

            logger.warning(
                "pypdf extraction failed: %s",
                e
            )

            return ""

    # ============================================================
    # OCR
    # ============================================================

    def _extract_pdf_with_ocr(
        self,
        pdf_bytes: bytes
    ) -> str:

        try:

            import fitz

        except ImportError:

            logger.warning(
                "PyMuPDF is not installed. "
                "Run: pip install pymupdf"
            )

            return ""

        try:

            import pytesseract

        except ImportError:

            logger.warning(
                "pytesseract is not installed. "
                "Run: pip install pytesseract"
            )

            return ""

        try:

            from PIL import Image

        except ImportError:

            logger.warning(
                "Pillow is not installed."
            )

            return ""

        try:

            document = fitz.open(
                stream=pdf_bytes,
                filetype="pdf"
            )

            pages = []

            for page_number in range(
                len(document)
            ):

                page = document[
                    page_number
                ]

                matrix = fitz.Matrix(
                    2.0,
                    2.0
                )

                pixmap = page.get_pixmap(
                    matrix=matrix,
                    alpha=False
                )

                image_bytes = pixmap.tobytes(
                    "png"
                )

                try:

                    image = Image.open(
                        BytesIO(image_bytes)
                    )

                    text = (
                        pytesseract.image_to_string(
                            image,
                            lang=self.ocr_language
                        )
                    )

                except Exception as e:

                    logger.warning(
                        "OCR failed on page %d: %s",
                        page_number + 1,
                        e
                    )

                    text = ""

                text = re.sub(
                    r"\s+",
                    " ",
                    text
                ).strip()

                if text:

                    pages.append(
                        f"[Page {page_number + 1} - OCR]\n"
                        f"{text}"
                    )

            document.close()

            return "\n\n".join(
                pages
            )

        except Exception as e:

            logger.warning(
                "PDF OCR failed: %s",
                e
            )

            return ""

    # ============================================================
    # PDF CHUNKING
    # ============================================================

    def _chunk_pdf_content(
        self,
        text: str
    ) -> list:

        """
        Split the complete PDF into overlapping chunks.

        Page markers are preserved.

        Example:

        [Page 12]
        Climate finance...

        [Page 13]
        Developing countries...
        """

        if not text:
            return []

        chunk_size = max(
            500,
            self.pdf_chunk_size
        )

        overlap = max(
            0,
            min(
                self.pdf_chunk_overlap,
                chunk_size // 2
            )
        )

        # Split while preserving page markers.
        page_pattern = r"(\[Page \d+(?: - OCR)?\])"

        parts = re.split(
            page_pattern,
            text
        )

        pages = []

        current_page = None

        for part in parts:

            part = part.strip()

            if not part:
                continue

            if re.match(
                r"\[Page \d+(?: - OCR)?\]",
                part
            ):

                current_page = part

            else:

                if current_page:

                    pages.append(
                        (
                            current_page,
                            part
                        )
                    )

        chunks = []

        for page_marker, page_text in pages:

            start = 0
            text_length = len(page_text)

            while start < text_length:

                end = min(
                    start + chunk_size,
                    text_length
                )

                chunk_text = page_text[
                    start:end
                ].strip()

                if chunk_text:

                    chunks.append(
                        {
                            "page": page_marker,
                            "text": (
                                f"{page_marker}\n"
                                f"{chunk_text}"
                            )
                        }
                    )

                if end >= text_length:
                    break

                start = max(
                    end - overlap,
                    start + 1
                )

        logger.info(
            "Created %d PDF chunks.",
            len(chunks)
        )

        return chunks

    # ============================================================
    # HTML - TRAFILATURA
    # ============================================================

    @staticmethod
    def _extract_with_trafilatura(
        html: str
    ) -> str:

        try:

            import trafilatura

        except ImportError:

            return ""

        try:

            return (
                trafilatura.extract(
                    html
                )
                or ""
            )

        except Exception:

            return ""

    # ============================================================
    # HTML - BEAUTIFULSOUP
    # ============================================================

    @staticmethod
    def _extract_with_bs4(
        html: str
    ) -> str:

        try:

            from bs4 import BeautifulSoup

        except ImportError:

            return ""

        try:

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

        except Exception:

            return ""

        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "aside",
                "form"
            ]
        ):

            tag.decompose()

        paragraphs = soup.find_all(
            "p"
        )

        text = " ".join(
            p.get_text(
                " ",
                strip=True
            )
            for p in paragraphs
        )

        return (
            text
            or soup.get_text(
                " ",
                strip=True
            )
        )
