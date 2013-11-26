from Image import Image
from Imager import Imager

class Batch:
  # TODO: Configuration should come from config dict
  def __init__(self, config):
    self.config = config
    self.name = config['section']
    self.image = Image(name=config['imagename'], partitionFile=config['partitionfile'])
    self.clients = []
    self.portOffset = 0
    self.basePort = int(config['baseport'])
    self.clientSelect = config['clientselect']
    self.clientCriteria = config['criteria']
    self.numsubbatches = int(config['subbatches'])
    if self.numsubbatches < 1:
      self.numsubbatches = 1
    self.subbatches = []
    self.imagers = []
    
  def selectClient(self, client, selectType, selectAll=False):
    if selectAll:
      self.clients.append(client)
      client.batch = self
      return True
    if self.clientSelect == "All" and selectType == "All":
      self.clients.append(client)
      client.batch = self
      return True
    if self.clientSelect == "IP" and client.ip in self.clientCriteria and selectType == "IP":
      self.clients.append(client)
      client.batch = self
      return True
    if self.clientSelect == "NameMatch" and self.clientCriteria in client.name and selectType == "NameMatch":
      self.clients.append(client)
      client.batch = self
      return True
    return False
      
  # TODO: Run function that creates sub-batches and and imager for each, runs them
  def run(self):
    offset = 0
    for i in xrange(self.numsubbatches):
      subconfig = dict(self.config)
      subconfig['section'] += "-sub%d" % i
      subconfig['baseport'] = self.basePort + offset
      offset += 1
      self.subbatches.append(Batch(subconfig))
    for i in xrange(len(self.clients)):
      self.subbatches[i%self.numsubbatches].clients.append(self.clients[i])
    for i in self.subbatches:
      self.imagers.append(Imager(i, self.completed, self.ready))
      
  def ready(self, batch):
    for i in batch.clients:
      i.start()
      
  def completed(self, batch):
    print "Finished imaging: ", batch.name
    self.subbatches.remove(batch)
    if not self.subbatches:
      print "Finished imaging: ", self.name