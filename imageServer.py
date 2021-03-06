#!/usr/bin/python
from Handler import ImagingHandler
from configReader import getConf
#from Image import Image
from Batch import Batch
import sys
from time import sleep
from Client import Client
from sslXMLRPC import SecureXMLRPCServer, SecureXMLRpcRequestHandler

CONFIG_FILE = "./images.conf"

batchConf, options = getConf(CONFIG_FILE)
batches = {}
for i in batchConf:
  batches[i['section']] = Batch(i)
  
rpcHandler = ImagingHandler(options)
rpcHandler._registerBatches(batches)

server_address = (options['host'], int(options['port']))
print server_address
server = SecureXMLRPCServer(server_address, SecureXMLRpcRequestHandler)
server.register_introspection_functions()

server.register_instance(rpcHandler)

sa = server.socket.getsockname()
print "Serving HTTPS on", sa[0], "port", sa[1]
server.serve_forever()