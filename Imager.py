import os
from threading import Thread
from time import sleep

class Imager:
  def __init__(self, batch, endFunc, readyFunc):
    self.endCallback = endFunc
    self.readyFunc = readyFunc
    self.batch = batch
    self.t = Thread(target=self.run)
    self.t.daemon = True
    self.t.start()
  def run(self):
    for i in self.batch.clients:
      i.port = self.batch.basePort
      print "Imaging: %s on port %d" % (i.name, i.port)
    self.readyFunc(self.batch)
#    sleep(5)
#    self.endCallback(self.batch)
#    return
    for part in self.batch.image.partitions:
      # TODO: Add client monitoring
      partFile = ""
      print part['type']
      if part['type'] == '7':
        partFile = os.path.join(self.batch.basepath, part['name']+".ntfs-img.aa")
      elif part['type'] == '83':
        partFile = os.path.join(self.batch.basepath, part['name']+".aa")
      else:
        print "Partition type %s is unknown." % part['name']
      udpsendArgs = ['--nopointopoint',
              '--nokbd',
              '--nopointopoint',
              '--full-duplex',
              '--max-wait 120',
              '--min-receivers',
              str(len(self.batch.clients)),
              '--log ./log',
              '--bw-period 2',
              '-f '+partFile,
              '--ttl 4',
              '--portbase '+str(self.batch.basePort+self.batch.portOffset),]
      runstr = ("udp-sender "+" ".join(udpsendArgs))
      print runstr
      os.system(runstr)
    self.endCallback(self.batch)
