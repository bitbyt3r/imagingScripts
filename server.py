#!/usr/bin/python
from SRPSocket import SRPSocket
import SocketServer
from bjsonrpc.handlers import BaseHandler
import bjsonrpc
import time

class handler(BaseHandler):
    def _setup(self):
      self.add_method(self.time)
    def time(self):
        return time.time()
    def foo(self):
        return "foo"

class SecureServer(SRPSocket.SRPHost):
    def auth_socket(self, socket):
        server = bjsonrpc.server.Server(socket, handler_factory=handler)
        server.serve()

s = SocketServer.ForkingTCPServer(('', 1338), SecureServer)
s.serve_forever()
