# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from concurrent.futures import ThreadPoolExecutor
from waitress.parser import HTTPRequestParser
from waitress import utilities
from .compat import asyncio
from aiowsgi import task
import waitress
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
            self.request = None
            task_class = task.ErrorTask if request.error else task.WSGITask
            channel = Channel(self.server, self.transport)
            t = task_class(channel, request)
            asyncio.ensure_future(asyncio.coroutine(t.service)(),
                                  loop=self.server.loop)
            if task_class is task.ErrorTask:
                channel.done.set_result(True)
            return channel
        else:
            self.request = request

    @classmethod
    def run(cls):
        cls.loop.run_forever()


class Channel(object):

    def __init__(self, server, transport):
        self.loop = server.loop
        self.server = server
        self.transport = transport
        self.write = transport.write
        self.addr = transport.get_extra_info('peername')[0]
        self.done = asyncio.Future(loop=self.loop)

    def write_soon(self, data):
        if data:
            if 'Buffer' in data.__class__.__name__:
                for v in data:
                    self.write(v)
            else:
                if not isinstance(data, bytes):
                    data = data.encode('utf8')
                self.write(data)
            return len(data)
        return 0

    def check_client_disconnected(self):
        return self.transport.is_closing()


def create_server(application, ssl=None, **adj):
    """Create a wsgi server:

    .. code-block::

        >>> async def application(environ, start_response):
        ...     pass
        >>> loop = asyncio.get_event_loop()
        >>> srv = create_server(application, loop=loop, port=2345)
        >>> srv.close()

    Then use ``srv.run()`` or ``loop.run_forever()``
    """
    if 'loop' in adj:
        loop = adj.pop('loop')
    else:
        loop = asyncio.get_event_loop()
    if 'ident' not in adj:
        adj['ident'] = 'aiowsgi'

    server = waitress.create_server(application, _start=False, **adj)

    adj = server.adj

    server.executor = None
    if not asyncio.iscoroutine(application) and \
       not asyncio.iscoroutinefunction(application):
        server.executor = ThreadPoolExecutor(max_workers=adj.threads)

    server.run = loop.run_forever
    server.loop = loop

    args = dict(app=[application],
                aioserver=None,
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

    def done(future):
        result = future.result()
        server.aioserver = result

    task = asyncio.ensure_future(
        f(proto, sock=server.socket, backlog=adj.backlog, ssl=ssl), loop=loop)
    task.add_done_callback(done)
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
