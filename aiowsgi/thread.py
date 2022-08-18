# -*- coding: utf-8 -*-
import time
import socket
import threading
from . import asyncio
from . import create_server
from six.moves import http_client


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    ip, port = s.getsockname()
    s.close()
    return ip, port


def check_server(host, port, path_info='/', timeout=3, retries=30):
    """Perform a request until the server reply"""
    if retries < 0:
        return 0
    time.sleep(.3)
    for i in range(retries):
        try:
            conn = http_client.HTTPConnection(host, int(port), timeout=timeout)
            conn.request('GET', path_info)
            res = conn.getresponse()
            return res.status
        except (socket.error, http_client.HTTPException):
            print('wait')
            time.sleep(.3)
    return 0


class WSGIServer(threading.Thread):
    """Stopable WSGI server running in a thread (not main thread).
    Usefull for functionnal testing.

    Usage:

    .. code-block::

        >>> async def application(environ, start_response):
        ...     start_response('200 OK', [])
        ...     return ['Hello world']
        >>> loop = asyncio.get_event_loop()
        >>> server = WSGIServer(application)
        >>> server.start()
        >>> server.stop()

    ``server.url`` will contain the url to request
    """

    def __init__(self, app, host='127.0.0.1', port=None):
        super(WSGIServer, self).__init__()
        self.server = None
        self.app = app
        _, self.port = port or get_free_port()
        self.host = host
        self.url = 'http://%s:%s' % (self.host, self.port)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.server = create_server(
            self.app, loop=self.loop, host=self.host, port=self.port)
        self.server.run()

    def wait(self):
        info = (self.host, self.port)
        status = check_server(*info)
        if status not in (200, 399):
            self.loop.call_soon_threadsafe(self._stop)
            info += (status,)
            raise RuntimeError(
                'Not able to connect to server at %s:%s (%s)' % info)

    def _stop(self):
        if self.server is not None:
            if getattr(self.server, 'aioserver', None) is not None:
                try:
                    self.server.aioserver.close()
                except TypeError:
                    pass
            self.server.close()
        self.loop.stop()

    def start(self):
        super(WSGIServer, self).start()
        self.wait()

    def stop(self):
        self.loop.call_soon_threadsafe(self._stop)
