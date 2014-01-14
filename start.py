#!/usr/bin/python
import xmlrpclib
import getpass
import readline
import rlcompleter

def remoteCall(func, *args):
    try:
        ret = func(*args)
        return ret
    except xmlrpclib.Fault as e:
        print e

<<<<<<< .mine
def help():
  print "This utility controls the imaging server."
  print "The command line interface has the following commands:"
  print "\trun <batch> - Tells the server to start running the batch with whatever clients are currently subscribed."
  print "\tbatches - Retrieves a list of the batches currently configured on the server"
  print "\tclients - Retrieves a list of all registered clients on the server"
  print "\tstatus - Retrieves the last status update received from each client"

server = xmlrpclib.ServerProxy("https://rhesus.cs.umbc.edu:2048")
=======
server = xmlrpclib.ServerProxy("https://forge.cs.umbc.edu:2048")
>>>>>>> .r245
sid = remoteCall(server.login, "admin", "wearethebuilders")
serverCommands = {"run":server.run, "batches":server.getBatches, "clients":server.getClients, "status":server.getStatus}
localCommands = {"help":help,}
def complete(text, state):
  commands = list(serverCommands)+list(localCommands)
  for cmd in commands:
    if cmd.startswith(text):
      if not state:
        return cmd
      state -= 1
readline.parse_and_bind('tab:complete')
readline.set_completer(complete)
while True:
  command = raw_input(":").strip()
  if command.split(" ")[0] in serverCommands:
    if len(command.split(" ")) > 1:
      temp = remoteCall(serverCommands[command.split(" ")[0]], sid, *command.split(" ")[1:])
    else:
      temp = remoteCall(serverCommands[command], sid)
    if temp:
      print temp
  elif command.split(" ")[0] in localCommands:
    if len(command.split(" ")) > 1:
      temp = localCommands[command.split(" ")[0]](*command.split(" ")[1:])
    else:  
      temp = localCommands[command.split(" ")[0]]()
    if temp:
      print temp

