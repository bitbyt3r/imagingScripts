#!/usr/bin/python
import bjsonrpc
from bjsonrpc.handlers import BaseHandler
from SRPSocket import SRPSocket
import time

socket, key = SRPSocket.SRPSocket('localhost', 1338, 'mark', 'wsxzaq')
c = bjsonrpc.connection.Connection(socket, handler_factory=BaseHandler)
print c.call.echo("foo")
