#!/usr/bin/python
import xmlrpclib
import getpass

def remoteCall(func, *args):
    try:
        ret = func(*args)
        return ret
    except xmlrpclib.Fault as e:
        print e

server = xmlrpclib.ServerProxy("https://rhesus.cs.umbc.edu:2048")
sid = remoteCall(server.login, raw_input("username:").strip(), getpass.getpass("password:").strip())
remoteCall(server.startUDPCast, sid)
