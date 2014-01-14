#!/usr/bin/python -W ignore::DeprecationWarning
import threading
import os
import sys
import termios
import getpass
import imageClient
import time
import advancedInput

response = None
responseFile = []
responseFileName = "build.conf"
strWidth = 27

def main():
  # install everything needed to run this script
  installReqs()
  # Get configuration for deployment
  config = getConfig()
  time.sleep(3)
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
  image = commandThread("/extra/imaging/client.py Server=%s User=%s Pass=%s" % (config['servername'], config['username'], config['password']), config, name="Windows Imager")
  updaterpmThread = commandThread("/usr/csee/sbin/updaterpm --"+config['rpmmode'], config, name="Updaterpm")
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
    elif os.system("/bin/echo 'id:5:initdefault:' > /etc/inittab"):
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
  os.system("/bin/cp -r /extra/repos/* /etc/yum.repos.d/")
  os.system("/usr/bin/yum install -y udpcast partimage")
  
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
    
def getConfig():
  getInput = advancedInput.HybridListener()
  configNames = ['reboot', 'servername', 'username', 'password', 'debug', 'rpmmode', 'cfengineserver', 'cfengineruntimes']
  print "Please answer the following prompts or insert a flash drive with an answers file named build.conf"
  configVals = map(getInput.prompt, [x+":" for x in configNames])
  config = {}
  config.update(zip(configNames, configVals))
  getInput.stop()
  return config
main()
