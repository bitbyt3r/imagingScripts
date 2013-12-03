#!/usr/bin/python
import xmlrpclib
import getpass

def remoteCall(func, *args):
    try:
        ret = func(*args)
        return ret
    except xmlrpclib.Fault as e:
        print e

server = xmlrpclib.ServerProxy("https://forge.cs.umbc.edu:2048")
sid = remoteCall(server.login, raw_input("username:").strip(), getpass.getpass("password:").strip())
commands = {"run":server.run, "getbatches":server.getBatches, "getclients":server.getClients}
while True:
  command = raw_input(":").strip()
  if command.split(" ")[0] in commands:
    if len(command.split(" ")) > 1:
      print remoteCall(commands[command.split(" ")[0]], sid, *command.split(" ")[1:])
    else:
      print remoteCall(commands[command], sid)
