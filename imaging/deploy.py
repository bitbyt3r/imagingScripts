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
  updaterpmThread = commandThread("/usr/csee/sbin/updaterpm --"+config['rpmmode']+" --change-only", config, name="Updaterpm")
  cfengineBootstrap = commandThread("/var/cfengine/bin/cf-agent -B "+config['cfengineserver'], config, name="Cfengine Bootstrap")
  grubThread = commandThread("/usr/csee/sbin/fixgrub.py -w", config, name="fixgrub")
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
  image.start()
  image.join()
    
  completeSuccess = True
  for i in threads:
    if i.success:
      print i.name+" "*(strWidth-len(i.name))+"\t[\033[32m  Ok  \033[0m]"
    else:
      print i.name+" "*(strWidth-len(i.name))+"\t[\033[31mFailed\033[0m]"
      completeSuccess = False
  if completeSuccess:
    print "Fixing root's .bashrc"
    contents = []
    with open("/root/.bashrc", "r") as rcfile:
      contents = rcfile.readlines()
    with open("/root/.bashrc", "w") as rcfile:
      rcfile.write("".join(contents[:-3]))
    print "Setting default init level to 5"
    with open("/boot/grub/menu.lst", "r") as grubfile:
      contents = grubfile.readlines()
    with open("/boot/grub/menu.lst", "w") as grubfile:
      grubfile.write("".join(contents))
      replace = True
      for i in contents:
        if "Windows" in i:
          replace = False
      if replace:
        grubfile.write("title Microsoft Windows 7\n")
        grubfile.write("\trootnoverify (hd0,2)\n")
        grubfile.write("\tchainloader +1\n")
    print "Setting Windows to boot next"
    grubThread.start()
    grubThread.join()
    print "Cleaning /extra"
    os.system("rm -rf /extra/*")
    print "Everything succeeded!"
    if config['reboot']:
      rebootThread = commandThread("/sbin/init 6", config, name="restart")
      rebootThread.start()
      rebootThread.join()
    sys.exit(0)
  else:
    print "Errors occurred during run."
    sys.exit(1)
  
def installReqs():
  os.system("/bin/rm -rf /etc/yum.repos.d/*")
  os.system("/bin/cp -r /extra/imaging/repos/* /etc/yum.repos.d/")
  os.system("/usr/bin/yum install -y partimage")
  
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
