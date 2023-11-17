import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer


class RequestHandler(BaseHTTPRequestHandler):

    def __init__(self,
                 ics_file: str = None,
                 ics_path: str = None,
                 *args, **kwargs) -> None:
        self.ics_file = "iopac.ics" if ics_file is None else ics_file
        self.ics_path = "/iopac.ics" if ics_path is None else ics_path
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == self.ics_path:
            self.send_response(200)
            self.send_header('Content-type', 'text/calendar')
            self.send_header('charset', 'utf-8')
            self.end_headers()
            with open(self.ics_file, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'404 Not Found')


class Server:
    def __init__(self,
                 port: int,
                 ics_file: str = None,
                 ics_path: str = None) -> None:
        self.port = port
        self.handler = partial(RequestHandler, ics_file, ics_path)
        self.httpd = HTTPServer(("", self.port), self.handler)
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
