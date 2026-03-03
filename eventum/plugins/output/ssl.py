"""Helper for creating SSL contexts for output plugins."""

import ssl
from pathlib import Path


def create_ssl_context(
    *,
    verify: bool,
    ca_cert: Path | None = None,
    client_cert: Path | None = None,
    client_key: Path | None = None,
) -> ssl.SSLContext:
    """Create initialized SSL context.

    Parameters
    ----------
    verify : bool
        Wether to verify certificates.

    ca_cert : Path | None, default=None
        Path to CA certificate.

    client_cert : Path | None, default=None
        Path to client certificate.

    client_key : Path | None, default=None
        Path to client certificate key.

    Returns
    -------
    ssl.SSLContext
        Initialized SSL context.

    Raises
    ------
    OSError
        If error occurs during reading certificates.

    ValueError:
        If client cert is provided but client key is not or vise versa.

    """
    context = ssl.create_default_context()

    if not verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    if ca_cert is not None:
        try:
            context.load_verify_locations(cafile=ca_cert)
        except ssl.SSLError as e:
            msg = f'Invalid CA certificate: {e}'
            raise OSError(msg) from e
        except OSError as e:
            msg = f'Failed to load CA certificate: {e}'
            raise OSError(msg) from e

    if client_cert is not None or client_key is not None:
        if client_cert is None or client_key is None:
            msg = 'Client certificate and key must be provided together'
            raise ValueError(msg)

        try:
            context.load_cert_chain(
                certfile=client_cert,
                keyfile=client_key,
            )
        except ssl.SSLError as e:
            msg = f'Invalid client certificate or key: {e}'
            raise OSError(msg) from e
        except OSError as e:
            msg = f'Failed to load client certificate or key: {e}'
            raise OSError(msg) from e

    return context
