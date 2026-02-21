import socket
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests as rq  # type: ignore[import-untyped]
from zoneinfo import ZoneInfo

from eventum.plugins.input.plugins.http.config import HttpInputPluginConfig
from eventum.plugins.input.plugins.http.plugin import HttpInputPlugin


@pytest.mark.filterwarnings('ignore:websockets')
def test_plugin():
    with ThreadPoolExecutor(max_workers=1) as executor:
        plugin = HttpInputPlugin(
            config=HttpInputPluginConfig(port=8080),
            params={
                'id': 1,
                'timezone': ZoneInfo('UTC'),
            },
        )

        timestamps = []

        def generate():
            for batch in plugin.generate(size=100):
                timestamps.extend(batch)

        future = executor.submit(generate)

        # wait for http server to start
        while True:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 8080))
            sock.close()
            if result == 0:
                break
            time.sleep(0.1)

        for _ in range(5):
            res = rq.post('http://localhost:8080/generate', json={'count': 2})
            assert res.status_code == 201

        res = rq.post('http://localhost:8080/stop')

        assert res.status_code == 200

        future.result()

        assert len(timestamps) == 10
