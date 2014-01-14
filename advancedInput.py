import os
import sys
import termios
import threading
import pyudev
import getpass
import dbus

class HybridListener:
  def __init__(self, filename="build.conf", mountdir="/mnt/responseDev"):
    os.system("/sbin/service messagebus start")
    self.context = pyudev.Context()
    self.monitor = pyudev.Monitor.from_netlink(self.context)
    self.monitor.filter_by('block')
    self.mountDir = mountdir
    self.response = None
    self.responseFile = []
    self.responseFileName = filename
    bus = dbus.SystemBus()
    ud_manager_obj = bus.get_object("org.freedesktop.UDisks", "/org/freedesktop/UDisks")
    ud_manager = dbus.Interface(ud_manager_obj, 'org.freedesktop.UDisks')
    for i in sys.argv[1:]:
      self.responseFile.append("%s: %s" % (*i.split("=")))
    for dev in ud_manager.EnumerateDevices():
      device_obj = bus.get_object("org.freedesktop.UDisks", dev)
      device_props = dbus.Interface(device_obj, dbus.PROPERTIES_IFACE)
      if device_props.Get('org.freedesktop.UDisks.Device', "DeviceIsRemovable") and not device_props.Get('org.freedesktop.UDisks.Device', "DriveIsMediaEjectable"):
        self.readResponseFile('', device_props.Get('org.freedesktop.UDisks.Device', "DeviceFile"), nameOnly=True)
    self.observer = pyudev.MonitorObserver(self.monitor, self.readResponseFile)
    self.observer.start()
    
  def stop(self):
    self.observer.stop()
    self.enable_echo(sys.stdin.fileno(), True)
    
  def userInput(self):
    self.response = raw_input("")

  def passInput(self):
    self.response = getpass.getpass("")
    
  def enable_echo(self, fd, enabled):
    (iflag, oflag, cflag, lflag, ispeed, ospeed, cc) = termios.tcgetattr(fd)
    if enabled:
      lflag |= termios.ECHO
    else:
      lflag &= ~termios.ECHO
    new_attr = [iflag, oflag, cflag, lflag, ispeed, ospeed, cc]
    termios.tcsetattr(fd, termios.TCSANOW, new_attr)
    
  def prompt(self, text="", password=False):
    self.response = ""
    print "\r"+text,
    prompt = None
    if password:
      prompt = threading.Thread(target=self.passInput)
    else:
      prompt = threading.Thread(target=self.userInput)
    prompt.daemon = True
    prompt.start()
    while not self.response:
      for i in self.responseFile:
        if text in i:
          answer = i.split(text)[1].strip()
          if answer:
            prompt.join(0)
            if not password:
              print answer,
            print
            self.enable_echo(sys.stdin.fileno(), True)
            return answer
    prompt.join(0)
    self.enable_echo(sys.stdin.fileno(), True)
    return self.response
  
  def readResponseFile(self, action, device, nameOnly=False):
    if ('ID_FS_TYPE' in device and action == 'add')or nameOnly:
      if not os.path.exists(self.mountDir):
        os.makedirs(self.mountDir)
      if nameOnly:
        os.system("mount {device} {mountDir}".format(device=device, mountDir=self.mountDir))
      else:
        os.system("mount {device} {mountDir}".format(device=device.device_node, mountDir=self.mountDir))
      if self.responseFileName in os.listdir(self.mountDir):
        with open(os.path.join(self.mountDir, self.responseFileName), "r") as fileHandle:
          self.responseFile.extend(fileHandle.readlines())
      os.system("umount {mountDir}".format(mountDir=self.mountDir))
