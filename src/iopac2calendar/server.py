import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        if self.path == "/iopac.ics":
            with open("iopac.ics", "rb") as f:
                self.wfile.write(f.read())
        else:
            self.wfile.write(b"Hello, world!")


class Server:
    def __init__(self, port: int) -> None:
        self.port = port
        self.httpd = HTTPServer(("", self.port), RequestHandler)
        self.thread = threading.Thread(target=self._serve)

    def _serve(self) -> None:
        self.httpd.serve_forever()

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.thread.join()

    def __del__(self) -> None:
        self.stop()
