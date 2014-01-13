#!/usr/bin/python -W ignore::DeprecationWarning
import xmlrpclib
import time
import sys
import parted
import os
import socket
import subprocess
import advancedInput

# TODO: This should be more intelligent
DRIVE_PATH = "/dev/sda"

if os.geteuid() != 0:
  sys.exit("You will need to be root to run this script successfully.")

OK = "[\033[32m  Ok  \033[0m] "
FAIL = "[\033[31mFailed\033[0m] "

# Simple wrapper to catch xmlrpc exceptions
def remoteCall(func, *args):
    try:
        ret = func(*args)
        return ret
    except xmlrpclib.Fault as e:
        print e

# Check to make sure partitions on disk match the required
# partitions from the server
def verifyPartitions(imageParts):
  disk = parted.disk.Disk(device=parted.device.Device(path=DRIVE_PATH))
  localParts = []
  for i in disk.partitions:
    # This tuple describes all of the information the server sends about partitions except for the filesystem type
    part = {}
    part['path'] = i.path
    part['number'] = i.number
    part['start'] = int(i.geometry.start)
    part['end'] = int(i.geometry.end)
    part['size'] = int(i.geometry.length)
    part['bootable'] = bool(i.getFlag(parted.PARTITION_BOOT))
    part['name'] = part['path'].split("/")[2]
    localParts.append(part)
    
  # The slice here is to remove the filesystem type from the tuple received from the server.
  # At this point, we don't care about filesystems.
  imagePartSettings = set()
  for image in imageParts:
    for i in image.items():
      if not 'type' in i:
        tup = list(i)
        tup.append(image['path'])
        imagePartSettings.add(tuple(tup))
    localPartSettings = set()
    for local in localParts:
      for i in local.items():
        tup = list(i)
        tup.append(local['path'])
        localPartSettings.add(tuple(tup))
    return imagePartSettings <= localPartSettings
    
# Run the given command in a shell. If getProc, returns a process object
def cmd(command, getProc=False):
  print command
  if getProc:
    p = subprocess.Popen([command], stdout=subprocess.PIPE, shell=True, universal_newlines=True)
    return p
  else:
    return os.system(command) == 0

# Initiate a udp-receiver and pipe it into the necessary imaging tool. This is 
# done outside of python on purpose, it should not be slowed down by anything.
def udpCast(partition, serverConfig, statusCallback):
  if partition['type'] in ['7','f']:
    return not os.system("udp-receiver --portbase {port} --nokbd --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | ntfsclone -r -O {path} -".format(port=serverConfig['portbase'], path=partition['path']))
  elif partition['type'] in ['83','82']:
    return not os.system("udp-receiver --portbase {port} --nokbd --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | partimage -b restore {path} stdin".format(port=serverConfig['portbase'], path=partition['path']))
  elif partition['type'] in ['5']:
    return not os.system("mkswap {path}".format(path=partition['path']))
  else:
    sys.exit(FAIL+"Unknown partition type %s" % partition['type'])

def repartition(shouldRepart, partMap):
  if not shouldRepart:
    return True
  if not partMap:
    sys.exit(FAIL+"No partition map received.")
  partMapFile = "/tmp/partMap"
  with open(partMapFile, "w") as partFile:
    partFile.write(partMap)
  # This is a bit weird because things exit 0 on success, which python interprets
  # as False. All of the commands have succeeded if none return True.
  return not any([os.system("swapoff -a"),
                  os.system("sfdisk --force "+DRIVE_PATH+" < "+partMapFile),
                  os.system("partprobe"),
                  os.system("swapon /dev/sda2"),])
        
def waitForServer(server, sid):
  while not(remoteCall(server.status, sid)):
    time.sleep(1)

# Get all of the server options from the user or a build.conf file
getInput = advancedInput.HybridListener(filename="build.conf")

# The sid is the unique key that identifies this client to the server.
sid = ""
server = xmlrpclib.ServerProxy(getInput.prompt("Server:"))
while not sid:
  username = getInput.prompt("User:")
  password = getInput.prompt("Pass:", password=True)
  username = username.strip()
  password = password.strip()
  try:
    sid = remoteCall(server.login, username, password)
  except socket.error:
    getInput.stop()
    sys.exit(FAIL+"Could not connect to server")
    
    
# Remove the udev hooks that listen for device insertion
getInput.stop()

if sid:
  print OK+"Logged in"
else:
  print FAIL+"Could not log in"

# This is a commonly used server function, so I wrap it more nicely
def setStatus(type, num):
  remoteCall(server.updateStatus, sid, (type, num))

name = socket.gethostname()
remoteCall(server.registerClient, sid, name)
partitions = remoteCall(server.partList, sid)

# The server has to tell us when to start imaging
setStatus("waiting", 0)
waitForServer(server, sid)

# We cannot pull our config until the server has told us it is ready.
# Do that now:
setStatus("gettingConfig", 0)
serverConfig = remoteCall(server.getConfig, sid)
if serverConfig:
  print OK+"Got Configuration"
else:
  print FAIL+"Could not get configuration"

# This server command will return a tuple:
#  -A boolean of whether to rewrite the partition table
#  -The partition table to write, in a form compatible
#   with sfdisk
setStatus("reparting", 0)
if repartition(*remoteCall(server.getPartMap, sid)):
  print OK+"Successfully repartitioned"
else:
  print FAIL+"Could not repartition"

# Actually image the system
if verifyPartitions(partitions):
  print OK+"Partitions are valid"
  for i in partitions:
    setStatus("imaging", int(i['number']))
    if udpCast(i, serverConfig, setStatus):
      print OK+"Successfully imaged %s" % i['name']
    else:
      print FAIL+"Could not image %s" % i['name']
else:
  print FAIL+"Partitions are not valid!"
  setStatus("error", 1)
  sys.exit(FAIL+"Error: The partitions on this system do not match the expected partitions received from the server.")
  
# All done! Log out and exit.
setStatus("done", 0)
remoteCall(server.logout, sid)
sys.exit(OK+"Success!")
