# -*- coding: utf-8 -*-
from aiowsgi.thread import WSGIServer
from webtest.debugapp import debug_app
from webtest import TestApp
from unittest import TestCase


class TestHttp(TestCase):

    def setUp(self):
        server = WSGIServer(debug_app)
        server.start()
        self.addCleanup(server.stop)
        self.app = TestApp(server.url)

    def test_page(self):
        resp = self.app.get('/')
        resp.mustcontain('SERVER_SOFTWARE: aiowsgi')
