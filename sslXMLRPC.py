#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
from hashlib import sha256
import hmac
import uuid
import time
from datetime import datetime
import re
import ConfigParser

import ssl
import socket
import SocketServer
import BaseHTTPServer
import SimpleHTTPServer
import SimpleXMLRPCServer
from xmlrpclib import Fault
import threading
import Queue

KEYFILE  = 'key.pem'  # Replace with your PEM formatted key file
CERTFILE = 'cert.pem'  # Replace with your PEM formatted certificate file

# 2011/01/01 in UTC
EPOCH = 1293840000

def require_login(decorated_function):
    """
    Decorator that prevents access to action if not logged in.

    If the login check failed a xmlrpclib.Fault exception is raised
    """

    def wrapper(self, session_id, *args, **kwargs):
        """ Decorated methods must always have self and session_id """

        # check if a valid session is available
        if not self.sessions.has_key(session_id):
            self._clear_expired_sessions() # clean the session dict
            raise Fault("Session ID invalid", "Call login(user, pass) to aquire a valid session")

        last_visit = self.sessions[session_id]["last_visit"]

        # check if timestamp is valid
        if is_timestamp_expired(last_visit):
            self._clear_expired_sessions() # clean the session dict
            raise Fault("Session ID expired", "Call login(user, pass) to aquire a valid session")

        self.sessions[session_id]["last_visit"] = get_timestamp()
        return decorated_function(self, session_id, *args, **kwargs)

    return wrapper

def timestamp_to_datetime(timestamp):
    """
    Convert a timestamp from 'get_timestamp' into a datetime object

    Args:
        ts: An integer timestamp

    Returns:
        A datetime object
    """

    return datetime.utcfromtimestamp(timestamp + EPOCH)

def get_timestamp():
    """
    Returns the seconds since 1/1/2011.

    Returns:
        A integer timestamp
    """

    return int(time.time() - EPOCH)

def is_timestamp_expired(timestamp, max_age = 2700): # maxage in seconds (here: 2700 = 45 min)
    """
    Checks if the given timestamp is expired

    Args:
        timestamp: An integer timestamp
        max_age  : The maximal allowd age of the timestamp in seconds

    Returns:
        True if the timestamp is expired or False if the timestamp is valid
    """

    age = get_timestamp() - timestamp
    if age > max_age:
        return True
    return False


class SecureXMLRPCServer(BaseHTTPServer.HTTPServer,SimpleXMLRPCServer.SimpleXMLRPCDispatcher):
    def __init__(self, server_address, HandlerClass, logRequests=True, allow_none=False):
        """
        Secure XML-RPC server.
        It it very similar to SimpleXMLRPCServer but it uses HTTPS for transporting XML data.
        """
        self.logRequests = logRequests
        self.allow_none  = True

        SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self, self.allow_none, None)
        SocketServer.BaseServer.__init__(self, server_address, HandlerClass)

        self.socket = ssl.wrap_socket(socket.socket(), server_side=True, certfile=CERTFILE,
                            keyfile=KEYFILE, ssl_version=ssl.PROTOCOL_SSLv23)

        self.server_bind()
        self.server_activate()

class SecureXMLRpcRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    """
    Secure XML-RPC request handler class.
    It it very similar to SimpleXMLRPCRequestHandler but it uses HTTPS for transporting XML data.
    """

    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def do_POST(self):
        """Handles the HTTPS POST request.

        It was copied out from SimpleXMLRPCServer.py and modified to shutdown the socket cleanly.
        """

        try:
            # get arguments
            data = self.rfile.read(int(self.headers["content-length"]))
            # In previous versions of SimpleXMLRPCServer, _dispatch
            # could be overridden in this class, instead of in
            # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
            # check to see if a subclass implements _dispatch and dispatch
            # using that method if present.
            response = self.server._marshaled_dispatch(
                    data, getattr(self, '_dispatch', None)
                )
        except Exception as e: # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

            # shut down the connection
            self.wfile.flush()

            #modified as of http://docs.python.org/library/ssl.html
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()