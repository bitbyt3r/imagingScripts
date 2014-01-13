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
import socket
import subprocess

# TODO: This should be more intelligent
DRIVE_PATH = "/dev/sda"

if os.geteuid() != 0:
  sys.exit("You will need to be root to run this script successfully.")

if '-s' in sys.argv:
  os.system("yum install -y partimage udpcast python-pyudev nano")

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
    
def cmd(command, getProc=False):
  print command
  if getProc:
    p = subprocess.Popen([command], stdout=subprocess.PIPE, shell=True, universal_newlines=True)
    return p
  else:
    return os.system(command) == 0

def udpCast(partition, serverConfig, statusCallback):
  if partition['type'] in ['7','f']:
    statusCallback("begun", 0)
    os.system("udp-receiver --portbase {port} --nokbd --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | ntfsclone -r -O {path} -".format(port=serverConfig['portbase'], path=partition['path']))
    statusCallback("gettingimage", 0)
  elif partition['type'] in ['83','82']:
    os.system("udp-receiver --portbase {port} --nokbd --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | partimage -b restore {path} stdin".format(port=serverConfig['portbase'], path=partition['path']))
    statusCallback("ext",0)
  elif partition['type'] in ['5']:
    os.system("mkswap {path}".format(path=partition['path']))
  else:
    statusCallback("error",0)
    sys.exit("Unknown partition type %s" % partition['type'])

def repartition(shouldRepart, partMap):
  if not shouldRepart:
    return
  if not partMap:
    sys.exit("Error: No partition map received.")
  partMapFile = "/tmp/partMap"
  with open(partMapFile, "w") as partFile:
    partFile.write(partMap)
  os.system("swapoff -a")
  os.system("sfdisk --force "+DRIVE_PATH+" < "+partMapFile)
  os.system("partprobe") 
  os.system("swapon /dev/sda2") 

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
    os.system("umount {mountDir}".format(mountDir=mountDir))
observer = pyudev.MonitorObserver(monitor, readResponseFile)
observer.start()
        
def waitForServer(server, sid):
  while not(remoteCall(server.status, sid)):
    time.sleep(1)
        
sid = ""
server = xmlrpclib.ServerProxy(prompt("Server:"))
while True:
  username = prompt("User:")
  password = prompt("Pass:", password=True)
  username = username.strip()
  password = password.strip()
  sid = remoteCall(server.login, username, password)
  if sid:
    break
    
observer.stop()
enable_echo(sys.stdin.fileno(), True)

def setStatus(type, num):
  remoteCall(server.updateStatus, sid, (type, num))

name = socket.gethostname()
remoteCall(server.registerClient, sid, name)
partitions = remoteCall(server.partList, sid)
setStatus("waiting", 0)
waitForServer(server, sid)
serverConfig = remoteCall(server.getConfig, sid)
setStatus("getconf", 0)
repartition(*remoteCall(server.getPartMap, sid))
for i in partitions:
  if i['type'] in ['7','f']:
    setStatus("format-ntfs",0)
    os.system("mkfs.ntfs -F -f -L Windows {path}".format(path=i['path']))

setStatus("reparted", 0)
if verifyPartitions(partitions):
  setStatus("imaging", 0)
  for i in partitions:
    udpCast(i, serverConfig, setStatus)
else:
  setStatus("error", 1)
  sys.exit("Error: The partitions on this system do not match the expected partitions received from the server.")
setStatus("done", 0)
remoteCall(server.logout, sid)
os.system("mkdir /tmp/foo")
os.system("mount /dev/sda1 /tmp/foo")
os.chroot("/tmp/foo")
os.system("/usr/csee/sbin/fixgrub.py -w")
sys.exit("Success!")
