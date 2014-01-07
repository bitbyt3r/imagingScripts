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
    sleep(2)
    #self.endCallback(self.batch)
    #return
    self.readyFunc(self.batch)
    for part in self.batch.image.partitions:
      # TODO: Add client monitoring
      partFile = ""
      print part['type']
      if part['type'] == '7':
        partFile = os.path.join(self.batch.basepath, part['name']+".ntfs-img")
      elif part['type'] == '83':
        partFile = os.path.join(self.batch.basepath, part['name'])
      else:
        print "Partition type %s is unknown." % part['name']
      udpsendArgs = ['--nopointopoint',
              '--nokbd',
              '--full-duplex',
              '--min-receivers',
              str(len(self.batch.clients)),
              '--max-wait 30',
              '-f '+partFile,
              '--portbase '+str(self.batch.basePort+self.batch.portOffset),
              '--ttl 2',
              '--log ./udp-sender.'+str(part['name'])+'.log',
              '--bw-period 30',
              '> ./udp-sender.'+str(part['name'])+'.stdout',
              '2> ./udp-sender.'+str(part['name'])+'.stderr',]
      runstr = ("udp-sender "+" ".join(udpsendArgs))
      print runstr
      os.system(runstr)
    self.endCallback(self.batch)
