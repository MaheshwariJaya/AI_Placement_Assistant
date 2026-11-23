import hashlib
import os
import uuid
from pathlib import Path
from typing import Tuple

import fitz  # PyMuPDF
import docx

from app.config import get_settings
from app.core.errors import AppError

settings = get_settings()

# Allowed file signatures (magic bytes)
MAGIC_PDF = b"%PDF"
MAGIC_DOCX = b"PK\x03\x04"


class DocumentParsingError(AppError):
    """Raised when document parsing fails."""
    def __init__(self, message: str, code: str = "DOCUMENT_PARSING_FAILED", status_code: int = 400):
        super().__init__(message=message, code=code, status_code=status_code)


class ScannedPdfError(AppError):
    """Raised when a PDF is image-based / scanned and has insufficient selectable text."""
    def __init__(self, message: str = "Scanned PDF detected. Text extraction requires OCR which is not enabled in this phase."):
        super().__init__(message=message, code="SCANNED_PDF_NEEDS_OCR", status_code=422)


def get_storage_directory() -> Path:
    """Return the absolute path to the private resume uploads directory, ensuring it exists."""
    storage_path = Path(settings.RESUME_STORAGE_DIR).resolve()
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


def validate_file_content(content: bytes, original_filename: str) -> Tuple[str, str]:
    """
    Validate file size, extension, and magic byte signatures.
    Returns (sanitized_extension, file_hash).
    """
    # 1. Size Validation (Hard 5MB limit)
    size = len(content)
    if size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise DocumentParsingError(
            f"File size ({size} bytes) exceeds maximum allowable limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes (5 MB).",
            code="FILE_TOO_LARGE",
            status_code=413,
        )
    if size == 0:
        raise DocumentParsingError("Uploaded file is empty (0 bytes).", code="EMPTY_FILE", status_code=400)

    # 2. Extension Validation
    ext = Path(original_filename).suffix.lower()
    if ext not in [".pdf", ".docx"]:
        raise DocumentParsingError(
            f"Unsupported file extension '{ext}'. Only .pdf and .docx resumes are accepted.",
            code="INVALID_FILE_TYPE",
            status_code=400,
        )

    # 3. Magic Bytes (Signature) Validation
    if ext == ".pdf":
        if not content.startswith(MAGIC_PDF):
            raise DocumentParsingError(
                "Invalid PDF document: File header does not match PDF signature.",
                code="INVALID_FILE_SIGNATURE",
                status_code=400,
            )
        file_type = "pdf"
    elif ext == ".docx":
        if not content.startswith(MAGIC_DOCX):
            raise DocumentParsingError(
                "Invalid DOCX document: File header does not match standard DOCX/ZIP signature.",
                code="INVALID_FILE_SIGNATURE",
                status_code=400,
            )
        file_type = "docx"
    else:
        raise DocumentParsingError("Unsupported file type.", code="INVALID_FILE_TYPE", status_code=400)

    # 4. Compute SHA-256 for integrity and deduplication
    file_hash = hashlib.sha256(content).hexdigest()

    return file_type, file_hash


def save_resume_file(content: bytes, student_id: int, file_type: str) -> Tuple[str, Path]:
    """
    Safely write uploaded resume bytes to the private filesystem directory.
    Returns (secure_filename, absolute_file_path).
    """
    storage_dir = get_storage_directory()
    secure_filename = f"{student_id}_{uuid.uuid4().hex}.{file_type}"
    target_path = storage_dir / secure_filename

    # Ensure target_path stays strictly within storage_dir (Path Traversal Protection)
    if not str(target_path.resolve()).startswith(str(storage_dir.resolve())):
        raise DocumentParsingError("Path traversal attempt detected.", code="SECURITY_VIOLATION", status_code=400)

    with open(target_path, "wb") as f:
        f.write(content)

    return secure_filename, target_path


def extract_text_from_pdf(file_path: Path) -> str:
    """
    Extract raw text from PDF document using PyMuPDF (fitz).
    Enriches visible text with underlying hyperlink URIs (e.g., LinkedIn, GitHub, project links).
    Detects scanned / empty documents requiring OCR.
    """
    extracted_text_chunks = []
    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            links = [l for l in page.get_links() if l.get("uri")]

            if not links:
                # Fast path when no hyperlinks are embedded on this page
                text = page.get_text("text")
                if text:
                    extracted_text_chunks.append(text.strip())
                continue

            words = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
            word_link_map = {}
            handled_links = set()

            for l_idx, l in enumerate(links):
                uri = l["uri"].strip()
                rect = fitz.Rect(l["from"])
                matched_indices = []
                for w_idx, w in enumerate(words):
                    w_rect = fitz.Rect(w[:4])
                    center = fitz.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)
                    if rect.contains(center) or (w_rect.intersects(rect) and abs(w[1] - rect.y0) < 10):
                        matched_indices.append(w_idx)

                if matched_indices:
                    last_w = max(matched_indices)
                    if not uri.startswith("mailto:"):
                        word_link_map[last_w] = uri
                    handled_links.add(l_idx)

            lines_dict = {}
            for w_idx, w in enumerate(words):
                b_no, l_no = w[5], w[6]
                key = (b_no, l_no)
                if key not in lines_dict:
                    lines_dict[key] = []
                word_str = w[4]
                if w_idx in word_link_map:
                    word_str = f"{word_str} ({word_link_map[w_idx]})"
                lines_dict[key].append(word_str)

            page_lines = []
            for key in sorted(lines_dict.keys()):
                page_lines.append(" ".join(lines_dict[key]))

            # Collect unhandled links (e.g. image/icon links with no textual characters underneath)
            unhandled = [
                links[i]["uri"].strip()
                for i in range(len(links))
                if i not in handled_links and not links[i]["uri"].startswith("mailto:")
            ]
            if unhandled:
                page_lines.append("\n[Additional Document Links]:")
                for u in unhandled:
                    page_lines.append(f"- {u}")

            full_page = "\n".join(page_lines).strip()
            if full_page:
                extracted_text_chunks.append(full_page)

        doc.close()
    except Exception as e:
        raise DocumentParsingError(f"Failed to read PDF file: {str(e)}", code="PDF_READ_ERROR")

    full_text = "\n\n".join(extracted_text_chunks).strip()

    # OCR detection guardrail:
    # If the document has pages but total selectable text is under 50 characters,
    # it is almost certainly a raster/scanned image PDF without an embedded text layer.
    if len(full_text) < 50:
        raise ScannedPdfError(
            "Scanned or image-only PDF detected (extracted text < 50 characters). "
            "Text extraction requires OCR which is not enabled in this phase."
        )

    return full_text


def _extract_docx_paragraph_text(p) -> str:
    """Extract paragraph text while appending hyperlink URIs from internal relationships."""
    parts = []
    try:
        for child in p._element:
            if child.tag.endswith("r"):
                for node in child.iter():
                    if node.tag.endswith("t") and node.text:
                        parts.append(node.text)
            elif child.tag.endswith("hyperlink"):
                r_id = child.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                link_text = "".join(node.text for node in child.iter() if node.tag.endswith("t") and node.text)
                if r_id and r_id in p.part.rels:
                    rel = p.part.rels[r_id]
                    url = getattr(rel, "target_ref", None) or getattr(rel, "_target", None)
                    if url and not url.startswith("mailto:"):
                        parts.append(f"{link_text} ({url})" if link_text else f"({url})")
                    else:
                        parts.append(link_text)
                else:
                    parts.append(link_text)
        full = "".join(parts).strip()
        return full if full else p.text.strip()
    except Exception:
        return p.text.strip()


def extract_text_from_docx(file_path: Path) -> str:
    """Extract raw text, hyperlinks, and table contents from DOCX document using python-docx."""
    extracted_text_chunks = []
    try:
        doc = docx.Document(file_path)
        # Extract paragraph text with hyperlinks
        for p in doc.paragraphs:
            text = _extract_docx_paragraph_text(p)
            if text:
                extracted_text_chunks.append(text)

        # Extract table text
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    cell_text = " ".join(_extract_docx_paragraph_text(p) for p in cell.paragraphs if p.text.strip())
                    if not cell_text:
                        cell_text = cell.text.strip()
                    if cell_text:
                        row_text.append(cell_text)
                if row_text:
                    extracted_text_chunks.append(" | ".join(row_text))
    except Exception as e:
        raise DocumentParsingError(f"Failed to read DOCX file: {str(e)}", code="DOCX_READ_ERROR")

    full_text = "\n".join(extracted_text_chunks).strip()

    if len(full_text) < 20:
        raise DocumentParsingError(
            "Document contains insufficient extractable text (< 20 characters).",
            code="EMPTY_DOCUMENT_TEXT",
        )

    return full_text


def extract_document_text(file_path: Path, file_type: str) -> str:
    """Extract textual content according to file type."""
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type == "docx":
        return extract_text_from_docx(file_path)
    else:
        raise DocumentParsingError(f"Unsupported file type: {file_type}")

