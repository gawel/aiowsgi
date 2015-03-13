# -*- coding: utf-8 -*-
import socket
import threading
from . import asyncio
from . import create_server


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    ip, port = s.getsockname()
    s.close()
    return ip, port


class WSGIServer(threading.Thread):
    """Stopable WSGI server running in a thread (not main thread).
    Usefull for functionnal testing.

    Usage:

    .. code-block::

        >>> @asyncio.coroutine
        ... def application(environ, start_response):
        ...     pass
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

    def stop(self):
        if self.server is not None:
            if self.server.aioserver is not None:
                try:
                    self.server.aioserver.close()
                except TypeError:
                    pass
            self.server.close()
        self.loop.stop()
        self.join()
