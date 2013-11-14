#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xmlrpclib
import time
import getpass
import sys

def continue_xmlrpc_call(func, *args):
    try:
        ret = func(*args)
        return ret
    except xmlrpclib.Fault as e:
        print e


server = xmlrpclib.ServerProxy("https://localhost:2048")
sid = ""
while True:
  username = raw_input("User:")
  password = getpass.getpass("Pass:")
  username.strip()
  password.strip()
  sid = continue_xmlrpc_call(server.login, username, password)
  if sid:
    print "Login Successful"
    break
  else:
    print "Login Failed"

print sid
print continue_xmlrpc_call(server.hello, sid, "World")
