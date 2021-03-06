class Client:
  def __init__(self, name, sid, startFunc, username="", password=""):
    self.name = name
    self.username = username
    self.password = password
    self.sid = sid
    self.batch = None
    self.port = 0
    self.started = False
    self.startFunc = startFunc
    self.status = ("initialized", 0)
    self.keyStore = {}
  
  def start(self):
    self.startFunc(self)
    
  def getConfig(self):
    return {"portbase":self.port}