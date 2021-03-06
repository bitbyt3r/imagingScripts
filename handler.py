from xmlrpclib import Fault
import os
import hmac
import uuid
from hashlib import sha256
class Image:
  def __init__(self, config):
    self.name = config['name']
    self.portBase = config['portbase']
    self.partFile = config['partitionfile']
    self.basePath = config['basepath']
    self.username = config['username']
    self.password = config['password']
    self.partitions = self.getPartitions()
    
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
        part['start'] = int(m.group(3))
        part['size'] = int(m.group(4))
        part['end'] = int(part['start'] + part['size'] - 1)
        part['number'] = int(m.group(2))
        part['type'] = m.group(5)
        part['bootable'] = bool(m.group(6))
        partitions.append(part)
    return partitions
    
class Imager:
  def __init__(self, batch):
    for i in partitions:
      self.udpCast(i)
    self.
    
class XMLRPCHandler:
    """
    Example implementation for login handling
    """

    def __init__(self, config):
        self.sessions = {}
        self.session_key = os.urandom(32)
        self.config = config
        self.images = {}
        self.clientConf = {}
        
    def _find_session_by_username(self, username):
        for session in self.sessions.itervalues():
            if session["username"] == username:
                return session

    def _invalidate_session_id(self, session_id):
        try:
            del self.sessions[session_id]
        except KeyError:
            pass

    def _clear_expired_sessions(self):
        for session_id in self.sessions.keys():
            last_visit = self.sessions[session_id]["last_visit"]
            if is_timestamp_expired(last_visit):
                self._invalidate_session_id(session_id)

    def _generate_session_id(self, username):
        return hmac.new(self.session_key, username + str(uuid.uuid4()), sha256).hexdigest()

    @require_login
    def logout(self, sid):
      self._invalidate_session_id(sid)
      
    @require_login
    def setImage(self, sid, image, batch):
      if image in self.images:
        if self.sessions[sid]['password'] == self.images[image]['password'] and self.sessions[sid]['username'] == self.images[image]['username']:
          if not batch in self.batches:
            self.batches[batch]['image'] = image
            self.batches[batch]['quantity'] = 0
          if self.batches[batch]['image'] == image:
            self.sessions['sid']['image'] = image
            self.batches[batch]['quantity'] += 1
          else:
            raise Fault("Wrong Batch", "The selected batch will not deploy the selected image. Please fix your config")
      else:
        raise Fault("Unknown image", "Please select a valid image, or define a new one")
      raise Fault("Incorrect username or password", "The given username or password do not match the selected image")
      
    @require_login
    def getConfig(self, sid):
      if 'image' in self.sessions['sid'] and self.sessions['sid']['image'] in self.images:
        return self.images[self.sessions['sid']['image']].clientConf()
      raise Fault("no image specified for client", "Please select an image before attempting to retrieve configuration")
        
    def _runBatch(batch):
      Imager(batch, _endBatch)
      
    def _endBatch(batch):
      self.batches[batch]['status'] = 'complete'
        
    @require_login
    def startBatch(self, batch):
      if not batch in self.batches:
        raise Fault("Unknown Batch", "The select batch does not exist")
      self._runBatch(batch)
    
    @require_login
    def getBatches(self):
      return self.batches

    def _registerImage(self, imageConfig):
      self.images[imageConfig['name']] = Image(imageConfig)
      self.passwords[imageConfig['name']] = imageConfig['password']
      self.usernames[imageConfig['name']] = imageConfig['username']

    def login(self, username, password):
        """
        Handle the login procedure. If the login is successful the session id is returned
        otherwise a xmlrpclib.Fault exception is raised.

        Args:
            username: The username
            password: The password

        Returns:
            A valid session id

        Raises:
            A xmlrpclib.Fault exception is raised
        """

        # check username and password
        if self.users.has_key(username):
            if self.users[username] == password:
                # generate session id and save it
                session_id = self._generate_session_id(username)
                self.sessions[session_id] = {"username"  : username,
                                             "session_id": session_id,
                                             "password"  : password,
                                             "last_visit": get_timestamp()}

                return session_id

        raise Fault("unknown username or password", "Please check your username and password")