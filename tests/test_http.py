# -*- coding: utf-8 -*-
from unittest import TestCase
import aiowsgi
from webtest.debugapp import debug_app


class Transport(object):

    def __init__(self):
        self.data = b''
        self.closed = False

    def write(self, data):
        self.data += data

    def close(self):
        self.closed = True


class TestHttp(TestCase):

    def callFTU(self, **kw):
        s = aiowsgi.WSGIProtocol.factory(debug_app, **kw)[0]()
        s.connection_made(Transport())
        return s

    def test_get(self):
        p = self.callFTU()
        p.data_received(b'GET / HTTP/1.1\r\n\r\n')
        t = p.transport
        self.assertFalse(p.parser)
        self.assertIn(b'REQUEST_METHOD: GET', t.data)

    def test_post(self):
        p = self.callFTU()
        t = p.transport
        p.data_received(
            b'POST / HTTP/1.1\r\nContent-Length: 1\r\n\r\nX')
        self.assertFalse(p.parser)
        self.assertIn(b'REQUEST_METHOD: POST', t.data)
        self.assertIn(b'HTTP_CONTENT_LENGTH: 1', t.data)

    def test_post_error(self):
        p = self.callFTU(max_request_body_size=1)
        t = p.transport
        resp = p.data_received(
            b'POST / HTTP/1.1\r\nContent-Length: 1025\r\n\r\nB')
        self.assertEqual(resp.status_int, 413)
        self.assertFalse(p.parser)
        self.assertFalse(p.keep_alive)
        self.assertTrue(t.closed)
        p.data_received(b'B' * 1024)
        self.assertTrue(p.parser)
        resp = p.data_received(b'GET / HTTP/1.1\r\n\r\n')
        self.assertEqual(resp.status_int, 200)
        self.assertFalse(p.parser)
