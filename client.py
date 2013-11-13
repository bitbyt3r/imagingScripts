#!/usr/bin/python
import xmlrpclib

# get username and password
# connect and authenticate to server
# get desired partition map
# get list of partitions to copy
# format partitions if necessary
# wait for server
# spawn udp-cast session for each partition

def main():
  p = xmlrpclib.ServerProxy('http://test:foo@localhost:8080')
  print p.ping()
main()
