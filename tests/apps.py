# -*- coding: utf-8 -*-
import webob
from aiowsgi.compat import asyncio

resp = webob.Response('It works!')


@asyncio.coroutine
def aioapp(environ, start_response):
    return resp(environ, start_response)


def app(environ, start_response):
    return resp(environ, start_response)
