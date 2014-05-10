# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from concurrent.futures import ThreadPoolExecutor
from waitress.parser import HTTPRequestParser
from waitress import utilities
from aiowsgi import task
import waitress
import asyncio
import sys


class WSGIProtocol(asyncio.Protocol):

    request_class = HTTPRequestParser

    def connection_made(self, transport):
        self.transport = transport
        self.request = None

    def data_received(self, data):
        if self.request is None:
            request = self.request_class(self.adj)
        else:
            request = self.request

        pos = request.received(data)
        if self.request is None and len(data) > pos:
            request.received(data[pos:])

        if request.completed or request.error:
            args = [self.server, self.transport, request]
            self.request = None
            asyncio.async(process(*args))
        else:
            self.request = request

    @classmethod
    def run(cls):
        cls.loop.run_forever()


@asyncio.coroutine
def process(server, transport, request):
    task_class = task.ErrorTask if request.error else task.WSGITask
    t = task_class(Channel(server, transport), request)
    asyncio.Task(asyncio.coroutine(t.service)())


class Channel(object):

    def __init__(self, server, transport):
        self.server = server
        self.transport = transport
        self.write = transport.write
        self.addr = transport.get_extra_info('peername')[0]

    def write_soon(self, data):
        if data:
            if 'Buffer' in data.__class__.__name__:
                for v in data:
                    self.write(v)
            else:
                self.write(data)
            return len(data)
        return 0


def create_server(application, ssl=None, **adj):
    """Create a wsgi server:

    .. code-block::

        >>> def application(environ, start_response):
        ...     pass
        >>> loop = asyncio.get_event_loop()
        >>> srv = create_server(application, loop=loop, port=8000)

    Then use ``srv.run()`` or ``loop.run_forever()``
    """
    if 'loop' in adj:
        loop = adj.pop('loop')
    else:
        loop = asyncio.get_event_loop()
    if 'ident' not in adj:
        adj['ident'] = 'aiowsgi'
    if not asyncio.iscoroutine(application) and \
       not asyncio.iscoroutinefunction(application):
        if hasattr(application, '__call__'):
            application = application.__call__
        application = asyncio.coroutine(application)
    server = waitress.create_server(application, _start=False, **adj)

    adj = server.adj

    server.run = loop.run_forever
    server.loop = loop
    server.executor = ThreadPoolExecutor(max_workers=adj.threads)

    args = dict(app=[application],
                adj=adj,
                loop=loop,
                server=server,
                server_name=server.server_name,
                effective_host=server.effective_host,
                effective_port=server.effective_port)
    proto = type(str('BoundedWSGIProtocol'), (WSGIProtocol,), args)
    server.proto = proto

    if adj.unix_socket:
        utilities.cleanup_unix_socket(adj.unix_socket)
        f = loop.create_unix_server
    else:
        f = loop.create_server
    asyncio.async(f(proto, sock=server.socket, backlog=adj.backlog, ssl=ssl))
    return server


def serve(application, **kw):  # pragma: no cover
    """Serve a wsgi application"""
    no_async = kw.pop('no_async', False)
    if not no_async:
        kw['_server'] = create_server
    return waitress.serve(application, **kw)


def serve_paste(app, global_conf, **kw):
    serve(app, **kw)
    return 0


def run(argv=sys.argv):
    from waitress import runner
    runner.run(argv=argv, _serve=serve)
