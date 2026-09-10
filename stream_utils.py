"""Small, dependency-free helpers used by the streaming endpoint."""

from __future__ import annotations

import re
from email.utils import quote


class RangeNotSatisfiable(ValueError):
    """Raised when an HTTP byte range cannot be served."""


def parse_range(range_header: str, file_size: int) -> tuple[int, int]:
    """Parse a single HTTP bytes range and return inclusive (start, end)."""
    if file_size <= 0:
        raise RangeNotSatisfiable("empty file")
    if not range_header or not range_header.lower().startswith("bytes="):
        raise RangeNotSatisfiable("unsupported range unit")
    value = range_header[6:].strip()
    if "," in value:
        raise RangeNotSatisfiable("multiple ranges are not supported")
    if "-" not in value:
        raise RangeNotSatisfiable("invalid range")
    start_text, end_text = (part.strip() for part in value.split("-", 1))
    try:
        if not start_text:
            suffix_length = int(end_text)
            if suffix_length <= 0:
                raise RangeNotSatisfiable("invalid suffix")
            return max(0, file_size - suffix_length), file_size - 1
        start = int(start_text)
        if start < 0 or start >= file_size:
            raise RangeNotSatisfiable("start outside file")
        end = int(end_text) if end_text else file_size - 1
        if end < start:
            raise RangeNotSatisfiable("end before start")
        return start, min(end, file_size - 1)
    except (TypeError, ValueError) as exc:
        raise RangeNotSatisfiable("invalid range") from exc


def content_disposition_filename(name: str) -> str:
    """Create a safe inline Content-Disposition value for arbitrary filenames."""
    cleaned = re.sub(r"[\r\n\\/]", "_", (name or "file")).strip() or "file"
    cleaned = cleaned.replace('"', "'")
    ascii_name = cleaned.encode("ascii", "replace").decode("ascii")
    return f'inline; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(cleaned)}'
