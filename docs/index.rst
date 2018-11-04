.. aiowsgi documentation master file, created by
   sphinx-quickstart on Thu May  8 23:21:43 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. include:: ../README.rst

Usage
=====

Install the software:

.. code-block:: sh

    $ pip install aiowsgi

Launch the server:

.. code-block:: sh

    $ aiowsgi-serve yourmodule:application
    $ aiowsgi-serve -h

You can also use a paste factory

.. code-block:: ini

    [server:main]
    use = egg:aiowsgi

Notice that all options will not work. aiowsgi just use ``waitress`` with a
custom server factory but not all adjustments are implemented.


API
===

.. autofunction:: aiowsgi.serve

.. autofunction:: aiowsgi.create_server

.. autoclass:: aiowsgi.thread.WSGIServer



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

