from xmlrpclib import Fault
import os
import hmac
import uuid
from hashlib import sha256
from sslXMLRPC import require_login

class ImagingHandler:
    def __init__(self, options):
        self.sessions = {}
        self.session_key = os.urandom(32)
        self.batches = {}
        self.clients = {}
        self.options = options
        
    def _registerBatches(self, batches):
      self.batches = batches
      
    @require_login
    def registerClient(self, name, sid, batch=False):
      client = Client(name, sid, self._startClient)
      self.clients[sid] = client
      if batch:
        self.batches[batch].selectClient(seclient, "All", selectAll=True)
        return
      for selectType in self.options['clientselectpriority']:
        for batch,i in self.batches.iteritems():
          if self.batches[batch].selectClient(client, selectType):
            return
      raise Fault("Client not Selected", "No batches currently include this client. Please add the client to a batch")
      
    def _startClient(self, client):
      self.clients[client.sid].start = True
      
    @require_login
    def getConfig(self, sid):
      return self.clients[sid].getConfig()
      
    @require_login
    def partList(self, sid):
      return self.clients[sid].batch.image.getPartitions()
      
    @require_login
    def getBatches(self):
      return self.batches.keys()
      
    @require_login
    def status(self, sid):
      return self.clients[sid].start
      
    @require_login
    def run(self, batch):
      self.batches[batch].run()
        
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

    def login(self, username, password):
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