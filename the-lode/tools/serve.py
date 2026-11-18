#!/usr/bin/env python3
"""Local static server for the mine. Run from any working directory."""
import argparse
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / 'web'


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.glb': 'model/gltf-binary',
                      '.bin': 'application/octet-stream', '.js': 'text/javascript',
                      '.json': 'application/json'}

    def send_head(self):
        self.byte_count = None
        header = self.headers.get('Range', '')
        path = Path(self.translate_path(self.path))
        if path.suffix.lower() != '.mp4' or not path.is_file() or not header:
            return super().send_head()
        match = re.fullmatch(r'bytes=([0-9]{0,20})-([0-9]{0,20})', header.strip())
        if not match or not any(match.groups()):
            return super().send_head()
        try:
            media = path.open('rb')
        except OSError:
            return super().send_head()
        stat = os.fstat(media.fileno())
        size = stat.st_size
        modified = self.date_time_string(stat.st_mtime)
        if self.headers.get('If-Range', modified) != modified:
            media.close()
            return super().send_head()
        a,b = match.groups()
        start = int(a) if a else max(0, size-int(b))
        end = min(size-1, int(b)) if b and a else size-1
        if start > end or start >= size:
            media.close()
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.send_header('Content-Length','0')
            self.end_headers()
            return None
        self.byte_count = end-start+1
        self.send_response(206)
        self.send_header('Content-Type','video/mp4')
        self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length',str(self.byte_count))
        self.send_header('Last-Modified',modified)
        self.end_headers()
        media.seek(start)
        return media

    def copyfile(self, source, output):
        if self.byte_count is None:
            return super().copyfile(source,output)
        left = self.byte_count
        while left:
            block = source.read(min(left,64*1024))
            if not block:
                break
            output.write(block)
            left -= len(block)

    def end_headers(self):
        if Path(self.translate_path(self.path)).suffix.lower() == '.mp4':
            self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()


def server(port=8137):
    return ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(WEB)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8137)
    with server(parser.parse_args().port) as http:
        print(f'The Lode · http://127.0.0.1:{http.server_port}/', flush=True)
        try:
            http.serve_forever()
        except KeyboardInterrupt:
            pass
