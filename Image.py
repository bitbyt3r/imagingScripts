import re

class Image:
  def __init__(self, name, partitionFile, imageParts):
    self.name = name
    self.partFile = partitionFile
    self.imageParts = imageParts
    self.partitions = self.getPartitions()
    self.partMap = ""
    
  def clientConf(self):
    clientConf = {}
    clientConf['name'] = self.name
    clientConf['portBase'] = self.portBase
    clientConf['partitions'] = self.partitions
    return clientConf
    
  def getPartitions(self):
    with open(self.partFile, "r") as partitionFile:
      partLines = [x for x in partitionFile.readlines() if x[:4] == "/dev"]
    partitions = []
    for i in partLines:
      m = re.search('(/dev/sda(\d))\s:\sstart=\s*(\d+),\ssize=\s*(\d+),\sId=\s*(\d+|f),*\s*(bootable)?', i)
      if m:
        part = {}
        part['path'] = m.group(1)
        part['name'] = m.group(1).split("/")[-1]
        part['start'] = int(m.group(3))
        part['size'] = int(m.group(4))
        part['end'] = int(part['start'] + part['size'] - 1)
        part['number'] = int(m.group(2))
        part['type'] = m.group(5)
        part['bootable'] = bool(m.group(6))
        if part['name'] in self.imageParts:
          partitions.append(part)
    return partitions
    
  def getPartMap(self):
    if not self.partMap:
      with open(self.partFile, "r") as partitionFile:
        self.partMap = partitionFile.read()
    return self.partMap