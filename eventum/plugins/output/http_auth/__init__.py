"""Authentication for http based output plugins."""

from eventum.plugins.output.http_auth.authenticators import (
    AcquiredToken,
    AuthenticationError,
    BasicHttpAuthenticator,
    BearerHttpAuthenticator,
    HttpAuthenticator,
    HttpAuthenticatorParams,
    OAuth2ClientCredentialsHttpAuthenticator,
    TokenHttpAuthenticator,
    basic_auth_header,
    create_authenticator,
    parse_token_response,
    request_token,
)
from eventum.plugins.output.http_auth.config import (
    AuthType,
    BasicHttpAuthConfig,
    BearerHttpAuthConfig,
    ClientAuthMethod,
    HttpAuthConfigT,
    OAuth2ClientCredentialsHttpAuthConfig,
    is_header_value,
)

__all__ = [
    'AcquiredToken',
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
    'TokenHttpAuthenticator',
    'basic_auth_header',
    'create_authenticator',
    'is_header_value',
    'parse_token_response',
    'request_token',
]
