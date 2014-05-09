# -*- coding: utf-8 -*-
from waitress.adjustments import Adjustments
from waitress.parser import HTTPRequestParser
import asyncio
import webob


class WSGIProtocol(asyncio.Protocol):

    parser_class = HTTPRequestParser

    @classmethod
    def factory(cls, application, **adj):
        """Create a TCP server:

        .. code-block:: python

            >>> loop = asyncio.get_event_loop()
            >>> args = WSGIProtocol.factory(application,
            ...                             host='127.0.0.1',
            ...                             port=8000)
            >>> task = asyncio.async(loop.create_server(*args))
        """
        adj = Adjustments(**adj)
        args = dict(app=[application], adj=adj)
        return type('BoundedWSGIProtocol', (cls,), args), adj.host, adj.port

    @classmethod
    def unix_factory(cls, application, **adj):
        """Create a UNIX server:

        .. code-block:: python

            >>> loop = asyncio.get_event_loop()
            >>> args = WSGIProtocol.unix_factory(application,
            ...                                  unix_socket='/tmp/wsgi')
            >>> task = asyncio.async(loop.create_unix_server(*args))
        """
        server, host, port = cls.factory(application, **adj)
        return server, server.adj.unix_socket

    def connection_made(self, transport):  # pragma: no cover
        self.transport = transport
        self.parser = None
        self.request = None
        self.keep_alive = False

    def data_received(self, data):
        if self.parser is None:
            self.parser = parser = self.parser_class(self.adj)
        else:
            parser = self.parser

        pos = parser.received(data)
        if self.request is None and len(data) > pos:
            parser.received(data[pos:])

        if parser.headers_finished:
            environ = {
                'PATH_INFO': parser.path,
                'REQUEST_METHOD': parser.command,
                'SERVER_PROTOCOL': parser.version,
                'wsgi.url_scheme': parser.url_scheme,
                'wsgi.input': parser.get_body_stream(),
            }
            self.request = webob.Request(environ=environ,
                                         headers=parser.headers)
            self.keep_alive = parser.headers.get('Connection') == 'Keep-Alive'

        if parser.completed or parser.error:
            if parser.error:
                resp = webob.Response(parser.error.body)
                resp.status = '%s %s' % (parser.error.code,
                                         parser.error.reason)
                self.keep_alive = False
            else:
                resp = self.request.get_response(self.app[0])
            w = self.transport.write
            w(('HTTP/1.1 ' + resp.status + '\r\n').encode('latin1'))
            if self.keep_alive:
                w('Connection: Keep-Alive\r\n'.encode('latin1'))
            else:
                w('Connection: Closed\r\n'.encode('latin1'))
            for h in resp.headers.items():
                w(('%s: %s\r\n' % h).encode('latin1'))
            body = resp.body
            if body:
                w(b'\r\n' + body)
            if not self.keep_alive:
                self.transport.close()
            self.parser = self.request = None
            return resp


def application():
    """testing purpose"""
