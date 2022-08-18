# -*- coding: utf-8 -*-
import webob
resp = webob.Response('It works!')


async def aioapp(environ, start_response):
    return resp(environ, start_response)


def app(environ, start_response):
    return resp(environ, start_response)
