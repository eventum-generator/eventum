"""File response utils."""

from urllib.parse import quote

# Every downloadable file is served as an opaque byte stream. Deriving
# the media type from the extension would hand a browser a type it
# knows how to execute - an `.html` or `.svg` file placed in a
# generator directory would become same-origin script the moment the
# disposition header stopped applying. The extension is preserved in
# the saved file name, so the type is still recognized on disk.
DOWNLOAD_MEDIA_TYPE = 'application/octet-stream'

# A file shown in place is text whatever it holds, for the same reason:
# any type a browser knows how to execute would be served from the
# origin the application itself runs on.
INLINE_MEDIA_TYPE = 'text/plain'

_QUOTED_STRING_FORBIDDEN = '"\\'


def build_file_headers(filename: str | None) -> dict[str, str]:
    """Build the headers a served project file carries.

    Parameters
    ----------
    filename : str | None
        Name to save the file under, or `None` to serve it in place.
        Path separators and control characters are stripped and the
        name is encoded per RFC 6266, so a name cannot alter the header
        it travels in.

    Returns
    -------
    dict[str, str]
        Headers to attach to the response.

    """
    # The media type is fixed either way, but a browser may still sniff
    # the body and act on what it finds; this forbids it.
    headers = {'X-Content-Type-Options': 'nosniff'}

    if filename is not None:
        headers['Content-Disposition'] = _attachment_disposition(filename)

    return headers


def _attachment_disposition(filename: str) -> str:
    """Build the `Content-Disposition` value for a saved file."""
    name = _sanitize_filename(filename)

    # A name that fits a quoted string as it is needs no encoding, and
    # the plain parameter is the one every client reads. Anything else
    # ships in both forms: the extended parameter carries the name in
    # full, the plain one keeps clients that ignore it from falling
    # back to the URL.
    if _fits_quoted_string(name):
        return f'attachment; filename="{name}"'

    return (
        f'attachment; filename="{_ascii_fallback(name)}"; '
        f"filename*=utf-8''{quote(name, safe='')}"
    )


def _fits_quoted_string(name: str) -> bool:
    """Check that a name can be sent as a plain quoted parameter."""
    return name.isascii() and not any(
        char in _QUOTED_STRING_FORBIDDEN for char in name
    )


def _sanitize_filename(filename: str) -> str:
    """Strip path separators and unprintable characters from a name."""
    stripped = ''.join(
        char for char in filename if char.isprintable() and char not in '/\\'
    ).strip()

    return stripped or 'download'


def _ascii_fallback(name: str) -> str:
    """Build the ASCII name for clients ignoring the extended form."""
    fallback = ''.join(
        char
        for char in name
        if char.isascii() and char not in _QUOTED_STRING_FORBIDDEN
    ).strip()

    return fallback or 'download'
