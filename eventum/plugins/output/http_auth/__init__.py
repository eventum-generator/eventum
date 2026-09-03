"""Authentication for http based output plugins."""

from eventum.plugins.output.http_auth.authenticators import (
    AuthenticationError,
    BasicHttpAuthenticator,
    BearerHttpAuthenticator,
    HttpAuthenticator,
    HttpAuthenticatorParams,
    OAuth2ClientCredentialsHttpAuthenticator,
    create_authenticator,
)
from eventum.plugins.output.http_auth.config import (
    AuthType,
    BasicHttpAuthConfig,
    BearerHttpAuthConfig,
    ClientAuthMethod,
    HttpAuthConfigT,
    OAuth2ClientCredentialsHttpAuthConfig,
)

__all__ = [
    'AuthType',
    'AuthenticationError',
    'BasicHttpAuthConfig',
    'BasicHttpAuthenticator',
    'BearerHttpAuthConfig',
    'BearerHttpAuthenticator',
    'ClientAuthMethod',
    'HttpAuthConfigT',
    'HttpAuthenticator',
    'HttpAuthenticatorParams',
    'OAuth2ClientCredentialsHttpAuthConfig',
    'OAuth2ClientCredentialsHttpAuthenticator',
    'create_authenticator',
]
