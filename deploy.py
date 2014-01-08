#!/usr/bin/python -W ignore::DeprecationWarning
import threading
import os
import sys
import termios
import getpass
import imageClient
import time

response = None
responseFile = []
responseFileName = "build.conf"
strWidth = 27

def main():
  # install everything needed to run this script
  installReqs()
  # Get configuration for deployment
  config = getConfig()
  if config['debug'] in ["true", "True"]:
    config['debug'] = True
  else:
    config['debug'] = False
  # Everything from here on out should be multithreaded.
  threads = []
  # Certain things can happen at the same time, i.e. imaging and everything else,
  # but you cannot bootstrap cfengine while running it or before it is installed.
  # I take care of that below. Start() will start, and join() will return when
  # finished.
  image = imageThread(config)
  updaterpmThread = commandThread("/usr/csee/sbin/updaterpm --"+config['rpmmode'], config, name="updaterpm")
  cfengineBootstrap = commandThread("/var/cfengine/bin/cf-agent -B "+config['cfengineserver'], config, name="Cfengine Bootstrap")
  image.start()
  updaterpmThread.start()
  updaterpmThread.join()
  cfengineBootstrap.start()
  cfengineBootstrap.join()
  threads.append(image)
  threads.append(updaterpmThread)
  threads.append(cfengineBootstrap)
  for i in xrange(int(config['cfengineruntimes'])):
    cfengineRun = commandThread("/var/cfengine/bin/cf-agent -K", config, name="Cfengine Run #%d"% (i+1))
    cfengineRun.start()
    cfengineRun.join()
    threads.append(cfengineRun)
  image.join()
    
  completeSuccess = True
  for i in threads:
    if i.success:
      print i.name+" "*(strWidth-len(i.name))+"\t[\033[32m  Ok  \033[0m]"
    else:
      print i.name+" "*(strWidth-len(i.name))+"\t[\033[31mFailed\033[0m]"
      completeSuccess = False
  if completeSuccess:
    if config['debug']:
      print "Setting default init level", "\t[\033[32m  Ok  \033[0m]" 
    elif os.system("/bin/sed -i 's/3/5/g' /etc/inittab"):
      completeSuccess = False
      print "Setting default init level", "\t[\033[31mFailed\033[0m]"
    else:
      print "Setting default init level", "\t[\033[32m  Ok  \033[0m]"
  if completeSuccess:
    print "Everything succeeded!"
    if config['reboot']:
      commandThread("/sbin/init 6", config, name="restart")
    sys.exit(0)
  else:
    print "Errors occurred during run."
    sys.exit(1)
  
def installReqs():
  os.system("/usr/bin/yum install -y udpcast")
  os.system("/usr/bin/yum install -y partimage")
  os.system("/usr/bin/easy_install pyudev")
  
class commandThread(threading.Thread):
  def __init__(self, command, config, name="command"):
    threading.Thread.__init__(self)
    self.command = command
    self.success = False
    self.config = config
    self.name = name
  def run(self):
    print "Running", self.command
    if self.config['debug']:
      print self.command
      self.success = True
    else:
      if os.system(self.command):
        print "running of", self.command, "returned a non-zero exit code."
        self.success = False
      else:
        self.success = True

class imageThread(threading.Thread):
  def __init__(self, config):
    threading.Thread.__init__(self)
    self.config = config
    self.success = False
    self.name = "Image Thread"
  def run(self):
    print "Starting an image client"
    if self.config['debug']:
      print "Imaged!"
      self.success = True
    else:
      self.success = imageClient.start(self.config)
    
def userInput():
  global response
  while not response:
    response = raw_input("")

def passInput():
  global response
  while not response:
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
  print "%s:" % text,
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
    
def getConfig():
  import pyudev
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
  configNames = ['reboot', 'servername', 'username', 'password', 'debug', 'rpmmode', 'cfengineserver', 'cfengineruntimes']
  print "Please answer the following prompts or insert a flash drive with an answers file named build.conf"
  configVals = map(prompt, configNames)
  config = {}
  config.update(zip(configNames, configVals))
  observer.stop()
  return config
main()
