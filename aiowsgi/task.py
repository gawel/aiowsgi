import asyncio
from waitress.task import reraise
from waitress.task import hop_by_hop
from waitress.task import ErrorTask  # NOQA
from waitress.task import WSGITask as Task
from waitress.task import ReadOnlyFileBasedBuffer


class WSGITask(Task):
    """A WSGI task produces a response from a WSGI application.
    """
    environ = None

    def execute(self):
        env = self.get_environment()
        env['aiowsgi.loop'] = self.channel.server.loop

        def start_response(status, headers, exc_info=None):
            if self.complete and not exc_info:
                raise AssertionError("start_response called a second time "
                                     "without providing exc_info.")
            if exc_info:
                try:
                    if self.complete:
                        # higher levels will catch and handle raised exception:
                        # 1. "service" method in task.py
                        # 2. "service" method in channel.py
                        # 3. "handler_thread" method in task.py
                        reraise(exc_info[0], exc_info[1], exc_info[2])
                    else:
                        # As per WSGI spec existing headers must be cleared
                        self.response_headers = []
                finally:
                    exc_info = None

            self.complete = True

            if not status.__class__ is str:
                raise AssertionError('status %s is not a string' % status)

            self.status = status

            # Prepare the headers for output
            for k, v in headers:
                if not k.__class__ is str:
                    raise AssertionError(
                        'Header name %r is not a string in %r' % (k, (k, v))
                    )
                if not v.__class__ is str:
                    raise AssertionError(
                        'Header value %r is not a string in %r' % (v, (k, v))
                    )
                kl = k.lower()
                if kl == 'content-length':
                    self.content_length = int(v)
                elif kl in hop_by_hop:
                    raise AssertionError(
                        '%s is a "hop-by-hop" header; it cannot be used by '
                        'a WSGI application (see PEP 3333)' % k)

            self.response_headers.extend(headers)

            # Return a method used to write the response data.
            return self.write

        # Call the application to handle the request and write a response
        t = asyncio.Task(
            self.channel.server.application(env, start_response))
        t.add_done_callback(self.aiocallback)

    def finish(self):
        pass

    def aiocallback(self, f):
        self.channel.server.loop.run_in_executor(
            self.channel.server.executor, self.aiofinish, f)

    def aiofinish(self, f):
        self.aioexecute(f.result())
        Task.finish(self)
        if self.close_on_finish:
            self.channel.transport.close()

    def aioexecute(self, app_iter):
        try:
            if app_iter.__class__ is ReadOnlyFileBasedBuffer:
                cl = self.content_length
                size = app_iter.prepare(cl)
                if size:
                    if cl != size:
                        if cl is not None:
                            self.remove_content_length_header()
                        self.content_length = size
                    self.write(b'')  # generate headers
                    self.channel.write_soon(app_iter)
                    return

            first_chunk_len = None
            for chunk in app_iter:
                if first_chunk_len is None:
                    first_chunk_len = len(chunk)
                    # Set a Content-Length header if one is not supplied.
                    # start_response may not have been called until first
                    # iteration as per PEP, so we must reinterrogate
                    # self.content_length here
                    if self.content_length is None:
                        app_iter_len = None
                        if hasattr(app_iter, '__len__'):
                            app_iter_len = len(app_iter)
                        if app_iter_len == 1:
                            self.content_length = first_chunk_len
                # transmit headers only after first iteration of the iterable
                # that returns a non-empty bytestring (PEP 3333)
                if chunk:
                    self.write(chunk)

            cl = self.content_length
            if cl is not None:
                if self.content_bytes_written != cl:
                    # close the connection so the client isn't sitting around
                    # waiting for more data when there are too few bytes
                    # to service content-length
                    self.close_on_finish = True
                    if self.request.command != 'HEAD':
                        self.logger.warning(
                            'application returned too few bytes (%s) '
                            'for specified Content-Length (%s) via app_iter'
                            '' % (
                                self.content_bytes_written, cl),
                        )
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
