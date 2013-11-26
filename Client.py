class Client:
  def __init__(self, name, sid, startFunc):
    self.name = name
    self.sid = sid
    self.batch = None
    self.port = 0
    self.startFunc = startFunc
  
  def start(self):
    self.startFunc(self)
    
  def getConfig(self):
    return {"portbase":self.port}