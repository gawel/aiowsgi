# -*- coding: utf-8 -*-
import webob
import asyncio
import aiowsgi


def application(environ, start_response):  # pragma: no cover
    return webob.Response('It works!')(environ, start_response)


def main():  # pragma: no cover
    loop = asyncio.get_event_loop()
    args = aiowsgi.WSGIProtocol.factory(application, host='127.0.0.1')
    asyncio.async(loop.create_server(*args))
    print('Listening on http://127.0.0.1:8080/ ...')
    loop.run_forever()
