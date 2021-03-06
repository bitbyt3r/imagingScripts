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

# TODO: This should be more intelligent
DRIVE_PATH = "/dev/sda"

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
    print("udp-receiver --portbase {port} --nokbd --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | ntfsclone -r -O {path} -".format(port=serverConfig['portbase'], path=partition['path']))
    os.system("udp-receiver --portbase {port} --nokbd --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | ntfsclone -r -O {path} -".format(port=serverConfig['portbase'], path=partition['path']))
  elif partition['type'] in ['83','82']:
    print("udp-receiver --portbase {port} --nokbd --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | partimage -b restore {path} stdin".format(port=serverConfig['portbase'], path=partition['path']))
    os.system("udp-receiver --portbase {port} --nokbd --ttl 2 --pipe \"gunzip -c -\" 2>> /tmp/udp-receiver_stderr | partimage -b restore {path} stdin".format(port=serverConfig['portbase'], path=partition['path']))
  elif partition['type'] in ['5']:
    print("mkswap {path}".format(path=partition['path']))
    os.system("mkswap {path}".format(path=partition['path']))
  else:
    print "Unknown partition type %s" % partition['type']
    return False
  return True
def waitForServer(server, sid):
  while not(remoteCall(server.status, sid)):
    time.sleep(1)
      
def start(config):
  server = xmlrpclib.ServerProxy(config['servername'])
  sid = remoteCall(server.login, config['username'], config['password'])
  
  name = socket.gethostname()
  print "Logged in,", sid
  remoteCall(server.registerClient, sid, name)
  print "Registered"
  partitions = remoteCall(server.partList, sid)
  print "Got Partitions"
  waitForServer(server, sid)
  serverConfig = remoteCall(server.getConfig, sid)
  print "Got Config"
  if verifyPartitions(partitions):
    for i in partitions:
      if not udpCast(i, serverConfig):
        return False
  else:
    print "Error: The partitions on this system do not match the expected partitions received from the server."
    return False
  remoteCall(server.logout, sid)
  return True