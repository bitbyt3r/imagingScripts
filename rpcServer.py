#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
from hashlib import sha256
import hmac
import uuid
import time
from datetime import datetime
import re
import ConfigParser

import ssl
import socket
import SocketServer
import BaseHTTPServer
import SimpleHTTPServer
import SimpleXMLRPCServer
from xmlrpclib import Fault
import threading
import Queue


# Configure below
LISTEN_HOST = 'rhesus.cs.umbc.edu' # You should not use '' here, unless you have a real FQDN.
LISTEN_PORT = 2048

KEYFILE  = 'key.pem'  # Replace with your PEM formatted key file
CERTFILE = 'cert.pem'  # Replace with your PEM formatted certificate file

CONFIG_FILE = './images.conf'

# 2011/01/01 in UTC
EPOCH = 1293840000

def require_login(decorated_function):
    """
    Decorator that prevents access to action if not logged in.

    If the login check failed a xmlrpclib.Fault exception is raised
    """

    def wrapper(self, session_id, *args, **kwargs):
        """ Decorated methods must always have self and session_id """

        # check if a valid session is available
        if not self.sessions.has_key(session_id):
            self._clear_expired_sessions() # clean the session dict
            raise Fault("Session ID invalid", "Call login(user, pass) to aquire a valid session")

        last_visit = self.sessions[session_id]["last_visit"]

        # check if timestamp is valid
        if is_timestamp_expired(last_visit):
            self._clear_expired_sessions() # clean the session dict
            raise Fault("Session ID expired", "Call login(user, pass) to aquire a valid session")

        self.sessions[session_id]["last_visit"] = get_timestamp()
        return decorated_function(self, session_id, *args, **kwargs)

    return wrapper

def timestamp_to_datetime(timestamp):
    """
    Convert a timestamp from 'get_timestamp' into a datetime object

    Args:
        ts: An integer timestamp

    Returns:
        A datetime object
    """

    return datetime.utcfromtimestamp(timestamp + EPOCH)

def get_timestamp():
    """
    Returns the seconds since 1/1/2011.

    Returns:
        A integer timestamp
    """

    return int(time.time() - EPOCH)

def is_timestamp_expired(timestamp, max_age = 2700): # maxage in seconds (here: 2700 = 45 min)
    """
    Checks if the given timestamp is expired

    Args:
        timestamp: An integer timestamp
        max_age  : The maximal allowd age of the timestamp in seconds

    Returns:
        True if the timestamp is expired or False if the timestamp is valid
    """

    age = get_timestamp() - timestamp
    if age > max_age:
        return True
    return False


class SecureXMLRPCServer(BaseHTTPServer.HTTPServer,SimpleXMLRPCServer.SimpleXMLRPCDispatcher):
    def __init__(self, server_address, HandlerClass, logRequests=True, allow_none=False):
        """
        Secure XML-RPC server.
        It it very similar to SimpleXMLRPCServer but it uses HTTPS for transporting XML data.
        """
        self.logRequests = logRequests
        self.allow_none  = True

        SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self, self.allow_none, None)
        SocketServer.BaseServer.__init__(self, server_address, HandlerClass)

        self.socket = ssl.wrap_socket(socket.socket(), server_side=True, certfile=CERTFILE,
                            keyfile=KEYFILE, ssl_version=ssl.PROTOCOL_SSLv23)

        self.server_bind()
        self.server_activate()

class SecureXMLRpcRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    """
    Secure XML-RPC request handler class.
    It it very similar to SimpleXMLRPCRequestHandler but it uses HTTPS for transporting XML data.
    """

    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def do_POST(self):
        """Handles the HTTPS POST request.

        It was copied out from SimpleXMLRPCServer.py and modified to shutdown the socket cleanly.
        """

        try:
            # get arguments
            data = self.rfile.read(int(self.headers["content-length"]))
            # In previous versions of SimpleXMLRPCServer, _dispatch
            # could be overridden in this class, instead of in
            # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
            # check to see if a subclass implements _dispatch and dispatch
            # using that method if present.
            response = self.server._marshaled_dispatch(
                    data, getattr(self, '_dispatch', None)
                )
        except Exception as e: # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

            # shut down the connection
            self.wfile.flush()

            #modified as of http://docs.python.org/library/ssl.html
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()

class XMLRPCHandler:
    """
    Example implementation for login handling
    """

    def __init__(self):
        self.users       = {"test": "test", "foo": "bar"} # replace with your own authentication
        self.sessions    = dict()
        self.session_key = os.urandom(32)
        self.images, self.config = self._getConfig(CONFIG_FILE)
        self.currentImage = None
        self.clients = []
        self.ready = False
        def udpcaster():
          while True:
            proc = q.get()
            print proc
            os.system(proc)
            q.task_done()
            
        self.q = Queue()
        self.t = Thread(target=udpcaster)
        t.daemon = True
        t.start()
        
        if 'currentimage' in self.config:
          for i in self.images:
            if self.config['currentimage'] == i['name']:
              self.currentImage = i
        try:
          self.users.update({self.config['username']:self.config['password']})
        except:
          print "There is no username and password defined in the configuration file."
        self.partitions = self.partList()
        

          
    def _find_session_by_username(self, username):
        """
        Try to find a valid session by username.

        Args:
            username: The username to search for

        Returns:
            If a session is found it is returned otherwise None is returned
        """

        for session in self.sessions.itervalues():
            if session["username"] == username:
                return session

    def _invalidate_session_id(self, session_id):
        """
        Remove a session.

        Args:
            session_id: The session which should be removed
        """

        try:
            del self.sessions[session_id]
        except KeyError:
            pass

    def _clear_expired_sessions(self):
        """
        Clear all expired sessions
        """

        for session_id in self.sessions.keys():
            last_visit = self.sessions[session_id]["last_visit"]
            if is_timestamp_expired(last_visit):
                self._invalidate_session_id(session_id)

    def _generate_session_id(self, username):
        """
        Generates a new session id

        Returns:
            A new unique session_id
        """

        return hmac.new(self.session_key, username + str(uuid.uuid4()), sha256).hexdigest()

    def login(self, username, password):
        """
        Handle the login procedure. If the login is successfull the session id is returned
        otherwise a xmlrpclib.Fault exception is raised.

        Args:
            username: The username
            password: The password

        Returns:
            A valid session id

        Raises:
            A xmlrpclib.Fault exception is raised
        """

        # Check if a session with the username exists
        session = self._find_session_by_username(username)
        if session:
            if is_timestamp_expired(session["last_visit"]):
                self._invalidate_session_id(session["session_id"])
            else:
                if self.users[username] == password:
                    return session["session_id"]

        # check username and password
        if self.users.has_key(username):
            if self.users[username] == password:
                # generate session id and save it
                session_id = self._generate_session_id(username)
                self.sessions[session_id] = {"username"  : username,
                                             "session_id": session_id,
                                             "last_visit": get_timestamp()}

                return session_id

        raise Fault("unknown username or password", "Please check your username and password")
      
    def _getConfig(self, configFile):
      images = {}
      config = ConfigParser.ConfigParser()
      if not(os.path.isfile(configFile)):
        sys.exit("The config file "+configFile+" is not a file. That is unfortunate.")
      if config.read(configFile):
        sections = {}
        for i in config.sections():
          sections[i] = config.items(i)
      else:
        sys.exit("Config File is not valid.")
      if "main" in sections.keys():
        options = {}
        for i in sections["main"]:
          options[i[0]] = i[1]
      else:
        options = None
        print "No global options found. Strange. I might explode."
      for i in sections.keys():
        if not i == "main":
          images[i] = {}
          for j in sections[i]:
            images[i][j[0]] = j[1]
          if not "section" in images[i].keys():
            images[i]["section"] = i
      if options:
        options = self._replaceKeys(options, {})
      images = [self._replaceKeys(images[x], options) for x in images]
      return images, options
      
    def _replaceKeys(self, image, main):
      if main:
        for i in main.keys():
          if not i in image.keys():
            image[i] = main[i]
      madeProgress = True
      keysWithSubs = self._remainingSubs(image)
      while keysWithSubs and madeProgress:
        madeProgress = False
        for j in keysWithSubs.keys():
          if not any(map(lambda x: x in keysWithSubs.keys(), keysWithSubs[j])):
            for k in keysWithSubs[j]:
              if k in image.keys():
                image[j] = re.sub("<"+k+">", image[k], image[j])
                madeProgress = True
        keysWithSubs = self._remainingSubs(image)
      return image

    def _remainingSubs(self, image):
      keysWithSubs = {}
      for i in image.keys():
        if re.findall(".*<(.+?)>.*", image[i]):
          keysWithSubs[i] = re.findall(".*<(.+?)>.*", image[i])
      return keysWithSubs
    
    def partList(self, sid=None):
      if not self.currentImage:
        print "baz"
        raise Fault("The server currently has no image selected", "Please select an image before continuing")
      with open(self.currentImage['partitionfile'], "r") as partitionFile:
        print "foo"
        partLines = [x for x in partitionFile.readlines() if x[:4] == "/dev"]
      print "bar"
      print partLines
      partitions = []
      for i in partLines:
        print "bash"
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
          print partitions
          partitions.append(part)
        print partitions
      print partitions
      return partitions
    
    @require_login
    def getConfig(self, session_id):
      return (self.currentImage, self.config)
      
    @require_login
    def registerClient(self, session_id):
      self.clients.append(session_id)
      
    @require_login
    def isReady(self, session_id):
      return self.ready
      
    @require_login
    def startUDPCast(self, session_id):
      self.ready = True
      for i in self.partitions:
        part = i['path'].split("/")[-1]
        partFile = os.path.join(self.currentImage['basepath'], part+".ntfs-img")
        udpsendArgs = ['--nopointopoint',
                      '--nokbd',
                      '--full-duplex',
                      '--min-receivers',
                      str(len(self.clients)),
                      '--max-wait 30',
                      '-f '+partFile,
                      '--portbase '+str(self.currentImage['portbase']),
                      '--ttl 2',
                      '--log ./udp-sender.'+str(part)+'.log',
                      '--bw-period 30',
                      '> ./udp-sender.'+str(part)+'.stdout',
                      '2> ./udp-sender.'+str(part)+'.stderr',]
        self.q.put("udp-sender "+" ".join(udpsendArgs))

server_address = (LISTEN_HOST, LISTEN_PORT)
server = SecureXMLRPCServer(server_address, SecureXMLRpcRequestHandler)
server.register_introspection_functions()
server.register_instance(XMLRPCHandler())

sa = server.socket.getsockname()
print "Serving HTTPS on", sa[0], "port", sa[1]
server.serve_forever()
