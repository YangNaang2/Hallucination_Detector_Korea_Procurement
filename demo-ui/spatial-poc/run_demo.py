"""Serve only public demo assets. No token or account configuration required."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import webbrowser

if __name__ == '__main__':
    directory = Path(__file__).resolve().parent / 'dist'
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    with ThreadingHTTPServer(('127.0.0.1', 8765), handler) as server:
        url = 'http://127.0.0.1:8765/'
        print(f'ASTRA / FREE MAP: {url}', flush=True)
        print('No Mapbox token needed. Internet + WebGL required. Ctrl+C to stop.', flush=True)
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
