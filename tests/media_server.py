from __future__ import annotations

import http.server
import threading
import time
from typing import Any, cast


class MediaHandler(http.server.BaseHTTPRequestHandler):
    @property
    def media(self) -> MediaServer:
        return cast("MediaServer", self.server)

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def do_HEAD(self) -> None:
        self._respond(send_body=False)

    def do_GET(self) -> None:
        self._respond(send_body=True)

    def _respond(self, send_body: bool) -> None:
        path, _, _query = self.path.partition("?")
        ranged = not path.startswith("/norange/")
        name = path.removeprefix("/norange")
        if name == "/page.html":
            self._send_page(send_body)
            return
        data = self.media.files.get(name)
        if data is None:
            self.send_error(404)
            return
        start = 0
        requested = self.headers.get("Range", "")
        if ranged and requested.startswith("bytes="):
            start = int(requested[6:].split("-")[0] or 0)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(data) - 1}/{len(data)}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", "image/jpeg" if name.endswith(".jpg") else "video/mp4")
        self.send_header("Content-Length", str(len(data) - start))
        if ranged:
            self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        if send_body:
            self._stream(data, start)

    def _stream(self, data: bytes, start: int) -> None:
        chunk = self.media.chunk_size
        try:
            for offset in range(start, len(data), chunk):
                self.wfile.write(data[offset : offset + chunk])
                if self.media.delay:
                    time.sleep(self.media.delay)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _send_page(self, send_body: bool) -> None:
        base = self.media.base_url
        body = (
            '<html><head><title>Sample clip</title><meta property="og:title" content="Sample clip">'
            f'<meta property="og:image" content="{base}/thumb.jpg">'
            f'<meta property="og:video" content="{base}/sample.mp4"></head><body></body></html>'
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if send_body:
            self.wfile.write(body)


class MediaServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, files: dict[str, bytes], delay: float = 0.0, chunk_size: int = 16384):
        super().__init__(("127.0.0.1", 0), MediaHandler)
        self.files = files
        self.delay = delay
        self.chunk_size = chunk_size
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"

    def __enter__(self) -> MediaServer:
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.shutdown()
        self.server_close()
