#!/usr/bin/python
from bjsonrpc import connect

c = connect()
time1 = c.call.time()

print "Time:", time1
print "Delta:", c.call.delta(time1)
