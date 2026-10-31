"""Turn a PDF, an .eml file, or pasted text into one source string for the graph."""

from __future__ import annotations

import html
import io
import re
from dataclasses import dataclass
from email import policy
from email.parser import BytesParser

from pypdf import PdfReader

from app.errors import AppError

MAX_BYTES = 15 * 1024 * 1024


@dataclass
class IngestResult:
    source_text: str
    source_kind: str
    filename: str = ""
    subject: str = ""
    sender: str = ""

    @property
    def characters(self) -> int:
        return len(self.source_text)


def ingest_source(data: bytes, filename: str, text: str, kind_hint: str) -> IngestResult:
    if len(data) > MAX_BYTES:
        raise AppError("Files must be 15 MB or smaller.", "file_too_large", 413)

    name = (filename or "").strip()
    lower = name.lower()
    parts: list[str] = []
    kind = ""
    subject = ""
    sender = ""

    if data:
        if lower.endswith(".pdf"):
            parts.append(_pdf_text(data))
            kind = "pdf"
        elif lower.endswith(".eml"):
            email = _email_text(data)
            parts.append(email["text"])
            subject = email["subject"]
            sender = email["sender"]
            kind = "email"
        elif lower.endswith(".msg"):
            raise AppError(
                "Outlook .msg files are not parsed. Save the message as .eml, or paste the email text.",
                "unsupported_type",
                415,
            )
        elif lower.endswith((".txt", ".md", ".text")):
            parts.append(_decode_text(data))
            kind = "text"
        elif data.startswith(b"%PDF"):
            parts.append(_pdf_text(data))
            kind = "pdf"
        else:
            parts.append(_decode_text(data))
            kind = "text"

    pasted = (text or "").strip()
    if pasted:
        parts.append(pasted)
        if not kind:
            kind = "email" if _looks_like_email(pasted) else "text"
        elif kind == "pdf":
            kind = "pdf+text"

    hint = (kind_hint or "").strip().lower()
    if hint in {"pdf", "text", "email"} and not data:
        kind = hint

    combined = "\n\n".join(part.strip() for part in parts if part and part.strip())
    if len(combined.strip()) < 1:
        raise AppError(
            "Nothing to read. Upload a PDF or .eml, or paste the incident text.",
            "empty_source",
            422,
        )
    return IngestResult(
        source_text=combined.strip(),
        source_kind=kind or "text",
        filename=name,
        subject=subject,
        sender=sender,
    )


def _decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").strip()


def _pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise AppError(f"The PDF could not be opened. {exc}", "pdf_unreadable", 422) from exc
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            raise AppError(
                "This PDF is encrypted. Export an unprotected copy or paste the text.",
                "pdf_encrypted",
                422,
            ) from exc
    pages: list[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    text = "\n\n".join(pages).strip()
    if len(text) < 20:
        raise AppError(
            "No text could be extracted from this PDF. If it is a scan, paste the text or run OCR first.",
            "pdf_no_text",
            422,
        )
    return text


def _email_text(data: bytes) -> dict[str, str]:
    try:
        message = BytesParser(policy=policy.default).parsebytes(data)
    except Exception as exc:
        raise AppError(f"The email file could not be parsed. {exc}", "email_unreadable", 422) from exc
    subject = str(message.get("subject") or "")
    sender = str(message.get("from") or "")
    recipient = str(message.get("to") or "")
    sent = str(message.get("date") or "")
    body = _message_body(message)
    text = f"From: {sender}\nTo: {recipient}\nDate: {sent}\nSubject: {subject}\n\n{body}".strip()
    return {"text": text, "subject": subject, "sender": sender}


def _message_body(message) -> str:
    if message.is_multipart():
        plain: list[str] = []
        html_parts: list[str] = []
        for part in message.walk():
            if part.get_content_disposition() == "attachment":
                continue
            content_type = part.get_content_type()
            if content_type == "text/plain":
                plain.append(_part_text(part))
            elif content_type == "text/html":
                html_parts.append(_part_text(part))
        if any(piece.strip() for piece in plain):
            return "\n".join(plain).strip()
        if html_parts:
            return strip_html("\n".join(html_parts))
        return ""
    content = _part_text(message)
    if message.get_content_type() == "text/html":
        return strip_html(content)
    return content.strip()


def _part_text(part) -> str:
    try:
        return str(part.get_content())
    except Exception:
        payload = part.get_payload(decode=True) or b""
        if isinstance(payload, str):
            return payload
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")


def strip_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?i)<br\s*/?>", "\n", value)
    value = re.sub(r"(?i)</p>", "\n", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return re.sub(r"[ \t]{2,}", " ", value).strip()


def _looks_like_email(text: str) -> bool:
    """A pasted shift note often starts with 'From:'. Require a subject and an address too."""
    head = text[:1200].lower()
    has_from = head.startswith("from:") or "\nfrom:" in head
    has_subject = "\nsubject:" in head or head.startswith("subject:")
    return has_from and has_subject and "@" in head
