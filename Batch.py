from Image import Image
from Imager import Imager
import time

class Batch:
  def __init__(self, config):
    self.config = config
    self.name = config['section']
    self.image = Image(name=config['imagename'], partitionFile=config['partitionfile'], imageParts=[x.strip() for x in config['imageparts'].split(",")])
    self.clients = []
    self.portOffset = 0
    self.username = config['username']
    self.password = config['password']
    self.basePort = int(config['baseport'])
    self.clientSelect = config['clientselect']
    self.clientCriteria = config['criteria']
    self.numsubbatches = int(config['subbatches'])
    if self.numsubbatches < 1:
      self.numsubbatches = 1
    self.subbatches = []
    self.imagers = []
    self.basepath = config['basepath']
    self.repartition = config['repartition'].lower() in ['true', 'y', 't', 'yes']
    
  def selectClient(self, client, selectType, selectAll=False):
    if client.username != self.username:
      print "Wrong username"
      return False
    if client.password != self.password:
      print "Wrong password"
      return False
    if selectAll:
      self.clients.append(client)
      client.batch = self
      return True
    print self.clientSelect, selectType
    if self.clientSelect == "All" and selectType == "All":
      self.clients.append(client)
      client.batch = self
      return True
    if self.clientSelect == "IP" and client.ip in self.clientCriteria and selectType == "IP":
      self.clients.append(client)
      client.batch = self
      return True
    if self.clientSelect == "NameMatch" and selectType == "NameMatch":
      for i in self.clientCriteria.split(","):
        if i in client.name:
          self.clients.append(client)
          client.batch = self
          return True
    return False
      
  def run(self):
    offset = 0
    for i in xrange(self.numsubbatches):
      subconfig = dict(self.config)
      subconfig['section'] += "-sub%d" % i
      subconfig['baseport'] = self.basePort + offset
      offset += 2
      self.subbatches.append(Batch(subconfig))
    for i in xrange(len(self.clients)):
      self.subbatches[i%self.numsubbatches].clients.append(self.clients[i])
    for i in self.subbatches:
      self.imagers.append(Imager(i, self.completed, self.ready))
      
  def ready(self, batch):
    for i in batch.clients:
      time.sleep(1)
      i.start()
      
  def completed(self, batch):
    print "Finished imaging: ", batch.name
    self.subbatches.remove(batch)
    if not self.subbatches:
      print "Finished imaging: ", self.name
