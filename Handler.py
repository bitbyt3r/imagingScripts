from xmlrpclib import Fault
import os
import hmac
import uuid
from hashlib import sha256
from sslXMLRPC import *
from Client import Client

class ImagingHandler:
    def __init__(self, options):
        self.sessions = {}
        self.session_key = os.urandom(32)
        self.batches = {}
        self.clients = {}
        self.options = options
        self.users = {}
        self.clientselectpriority = self.options['clientselectpriority'].split(",")
        self.clientselectpriority = [x.strip() for x in self.clientselectpriority]
        
    def _registerBatches(self, batches):
      self.batches = batches
      for i in self.batches:
        self.users[self.batches[i].username] = self.batches[i].password
      
    @require_login
    def registerClient(self, sid, name, batch=False):
      client = Client(name, sid, self._startClient, self.sessions[sid]['username'], self.sessions[sid]['password'])
      print client.password, client.username
      self.clients[sid] = client
      if batch:
        return self.batches[batch].selectClient(seclient, "All", selectAll=True)
      for selectType in self.clientselectpriority:
        print "Foo"
        for batch,i in self.batches.iteritems():
          print "Bar", batch
          if self.batches[batch].selectClient(client, selectType):
            print "Baz"
            return True
      raise Fault("Client not Selected", "No batches currently include this client. Please add the client to a batch")
      
    def _startClient(self, client):
      self.clients[client.sid].started = True
      
    @require_login
    def getConfig(self, sid):
      return self.clients[sid].getConfig()
      
    @require_login
    def partList(self, sid):
      return self.clients[sid].batch.image.getPartitions()
      
    @require_login
    def getClients(self, sid):
      return [x.name for x in self.clients.values()]
      
    @require_login
    def getBatches(self, sid):
      return self.batches.keys()
      
    @require_login
    def status(self, sid):
      return self.clients[sid].started
      
    @require_login
    def run(self, sid, batch):
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
      pass

    def _generate_session_id(self, username):
        return hmac.new(self.session_key, username + str(uuid.uuid4()), sha256).hexdigest()

    @require_login
    def logout(self, sid):
      self.clients[sid].batch.clients.remove(self.clients[sid])
      del self.sessions[sid]
      del self.clients[sid]

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