#!/usr/bin/python
from bjsonrpc.handlers import BaseHandler
from bjsonrpc import createserver
import time

class ServerHandler(BaseHandler):
  def time(self):
    return time.time()
  def delta(self, start):
    return time.time() - start

s = createserver(handler_factory=ServerHandler)
s.serve()
