#!/usr/bin/python -W ignore::DeprecationWarning
import xmlrpclib
import time
import getpass
import sys
import parted
import os
import threading
import pyudev
import termios

# TODO: This should be more intelligent
DRIVE_PATH = "/dev/sda"

if os.geteuid() != 0:
  sys.exit("You will need to be root to run this script successfully.")

def remoteCall(func, *args):
    try:
        ret = func(*args)
        return ret
    except xmlrpclib.Fault as e:
        print e

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
    localParts.append(part)
    
  # The slice here is to remove the filesystem type from the tuple received from the server.
  # At this point, we don't care about filesystems.
  print localParts
  print imageParts
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

def udpCast(partition, serverConfig):
  if partition['type'] in ['7','f']:
    print("udp-receiver --portbase {port} --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | ntfsclone -r -O {path} -".format(port=serverConfig['port'], path=partition['path']))
    os.system("udp-receiver --portbase {port} --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | ntfsclone -r -O {path} -".format(port=serverConfig['port'], path=partition['path']))
  elif partition['type'] in ['83','82']:
    os.system("udp-receiver --portbase {port} --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | partimage -b restore {path} stdin".format(port=serverConfig['port'], path=partition['path']))
  elif partition['type'] in ['5']:
    os.system("mkswap {path}".format(path=partition['path']))
  else:
    sys.exit("Unknown partition type %s" % partition['type'])

response = None
responseFile = []
responseFileName = "build.conf"
def userInput():
  global response
  response = raw_input("")

def passInput():
  global response
  response = getpass.getpass("")
  
def enable_echo(fd, enabled):
  (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(fd)
  if enabled:
    lflag |= termios.ECHO
  else:
    lflag &= ~termios.ECHO
  new_attr = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
  termios.tcsetattr(fd, termios.TCSANOW, new_attr)
  
def prompt(text="", password=False):
  global response
  response = ""
  print text,
  prompt = None
  if password:
    prompt = threading.Thread(target=passInput)
  else:
    prompt = threading.Thread(target=userInput)
  prompt.daemon = True
  prompt.start()
  while not response:
    for i in responseFile:
      if text in i:
        answer = i.split(text)[1].strip()
        if answer:
          prompt.join(0)
          if not password:
            print answer
          enable_echo(sys.stdin.fileno(), True)
          return answer
  prompt.join(0)
  enable_echo(sys.stdin.fileno(), True)
  return response
    
# Client Procedure:
# Get username/password
# Contact server, collect sid
# Request Partition layout
# Verify Drive Format
# Wait for server to start
# Spawn udpcast session(s)

context = pyudev.Context()
monitor = pyudev.Monitor.from_netlink(context)
monitor.filter_by('block')
mountDir = "/mnt/responseDev"
def readResponseFile(action, device):
  if 'ID_FS_TYPE' in device and action == 'add':
    if not os.path.exists(mountDir):
      os.makedirs(mountDir)
    os.system("mount {device} {mountDir}".format(device=device.device_node, mountDir=mountDir))
    if responseFileName in os.listdir(mountDir):
      with open(os.path.join(mountDir, responseFileName), "r") as fileHandle:
        global responseFile
        responseFile = fileHandle.readlines()
observer = pyudev.MonitorObserver(monitor, readResponseFile)
observer.start()
        
sid = ""
server = xmlrpclib.ServerProxy(prompt("Server:"))
while True:
  username = prompt("User:")
  password = prompt("Pass:", password=True)
  servername = prompt("Server:")
  username = username.strip()
  password = password.strip()
  servername = servername.strip()
  sid = remoteCall(server.login, username, password)
  if sid:
    print "Login Successful"
    break
  else:
    print "Login Failed"
    
observer.stop()
    
partitions = remoteCall(server.partList, sid)
print "Got Partitions"
serverConfig = remoteCall(server.getConfig, sid)
print "Got Config"
if verifyPartitions(partitions):
  remoteCall(server.registerClient, sid)
  for i in partitions:
    udpCast(i, serverConfig)
else:
  sys.exit("Error: The partitions on this system do not match the expected partitions received from the server.")
sys.exit("Success!")
