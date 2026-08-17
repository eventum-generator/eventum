"""Caching policy of web UI resources."""

import os
from typing import override

from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

# Resources that keep their names across builds. They name the assets
# of the build they came from, so a copy of them must never be reused
# without asking the server first.
SHELL_CACHE_CONTROL = 'no-cache'

# Resources named after the hash of their content. Their bodies never
# change, so a client can hold them until a build stops naming them.
ASSET_CACHE_CONTROL = 'public, max-age=31536000, immutable'


class ImmutableStaticFiles(StaticFiles):
    """Static files served as immutable resources."""

    @override
    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        """Build response for the requested file.

        Parameters
        ----------
        full_path : str | os.PathLike[str]
            Path of the file to serve.

        stat_result : os.stat_result
            Stat result of the file.

        scope : Scope
            Scope of the request.

        status_code : int, default=200
            Status code of the response.

        Returns
        -------
        Response
            Response carrying the file and the caching policy of an
            immutable resource.

        """
        response = super().file_response(
            full_path,
            stat_result,
            scope,
            status_code=status_code,
        )
        response.headers['cache-control'] = ASSET_CACHE_CONTROL

        return response
