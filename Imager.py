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
      udpsendArgs = ['--nopointopoint',
              '--nokbd',
              '--full-duplex',
              '--min-receivers',
              str(len(self.batch.clients)),
              '--max-wait 30',
              '-f '+self.batch.image.partFile,
              '--portbase '+str(self.batch.basePort+self.batch.portOffset),
              '--ttl 2',
              '--log ./udp-sender.'+str(part['name'])+'.log',
              '--bw-period 30',
              '> ./udp-sender.'+str(part['name'])+'.stdout',
              '2> ./udp-sender.'+str(part['name'])+'.stderr',]
      print("udp-sender "+" ".join(udpsendArgs))
    self.endCallback(self.batch)
