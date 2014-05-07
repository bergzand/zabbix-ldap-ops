#!/usr/bin/env python

import ldap
import json
import socket
import sys
import logging
import os.path
import sys
import argparse

SERVERURI = "ldapi:///"
BINDDN = "uid=monitor,ou=system,dc=bergzand,dc=net"
BINDPASS = "/etc/ldap.monitor"
MONITORDB = "cn=monitor"

ZABBIXHOST = 'ldap'
ZABBIXSERVER = 'zabbix.bergzand.net'
ZABBIXPORT = 10051
ZABBIXKEY = 'ldap.stats'


#check if bindpw is a file and return the content as a string, otherwise return the input as the password
def getpw(bindpw):
    if os.path.isfile(bindpw):
        try:
            with open (BINDPASS, "r") as passfile:
                bindpw=passfile.read()
        except IOError:
            print 'cant open file, IOError {0}: {1}'.format(IOError.errno, IOError.strerror)
    return bindpw

#send json object to the zabbix server
def sendtozabbix(data):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(3.0)
        s.connect((ZABBIXSERVER,ZABBIXPORT))
    except Exception as e:
        print '{0} {1}: {2}'.format(type(e).__name__, e.errno, e.strerror)
        exitstatus = 1
    else:
        s.sendall(data)
        data = s.recv(1024)
    finally: 
        s.close()

def ParseToLib(statistics, operations):
    zabbixData = { 'request': 'sender data', 'data': []}
    #parse statistics to the zabbixData
    for dn,entry in statistics:
        if "monitorCounter" in entry:
            rdn,group = ldap.dn.explode_dn(dn,notypes=True)[:2]
            item = { 'host': ZABBIXHOST, 
                'key': "{0}[{1},{2}]".format(
                    ZABBIXKEY,  group.lower() , rdn.lower()),
                'value' : entry['monitorCounter'][0]}
            zabbixData['data'].append(item)
    #parse operations for the zabbixData
    for dn,entry in operations:
        if "monitorOpCompleted" in entry:
            rdn,group = ldap.dn.explode_dn(dn,notypes=True)[:2]
            if rdn == 'Operations':
                rdn,group = 'total','operations'
            item = { 'host': ZABBIXHOST, 
                'key': "{0}[{1},{2}]".format(
                    ZABBIXKEY,  group.lower() , rdn.lower()),
                'value' : entry['monitorOpCompleted'][0]}
            zabbixData['data'].append(item)
    return zabbixData

#need to add arguments for:
# zabbix server
# zabbix port
# zabbix key
# zabbix hostname
# 
# ldapuri
# binddn
# bindpw
# monitordb

def argParse():
    parser = argparse.ArgumentParser(description="Get statistics from ldap and send them to a zabbix server")
    parser.add_argument('-z','--zabbixserver', nargs='?', default='zabbix')
    parser.add_argument('-p','--zabbixport', nargs='?', type=int,default='10051')
    parser.add_argument('-k','--zabbixkey', nargs='?', default='ldap.stats')
    parser.add_argument('-s','--zabbixhost', nargs='?', default='ldap')
    parser.add_argument('-H','--uri', nargs='?', default='ldapi:///')
    parser.add_argument('-D','--binddn', nargs='?')
    parser.add_argument('-w','--bindpw', nargs='?')
    parser.add_argument('-b','--monitordb', nargs='?', default='cn=monitor')
    args=parser.parse_args()

############
#main script
############
exitstatus = 0
zabbixvalue = 1
if len(sys.argv) > 0:
    argParse()
#get password
ldappass = getpw(BINDPASS)

#make ldap conn object
conn = ldap.initialize(SERVERURI)
#get ldap data
try:
    conn.simple_bind_s(BINDDN,ldappass)
    statistics = conn.search_s("cn=statistics,"+MONITORDB, ldap.SCOPE_SUBTREE,attrlist=['monitorCounter'])
    operations = conn.search_s("cn=operations,"+MONITORDB, ldap.SCOPE_SUBTREE,attrlist=['monitorOpCompleted'])
except Exception as e:
    print 'LDAP connection error: {0}'.format(type(e).__name__)
    zabbixvalue = 0
    exitstatus = 1
finally:
    conn.unbind()

if exitstatus == 0:
    data = ParseToLib(statistics, operations)
    #initial zabbixData object
    
    sendtozabbix(json.dumps(data))

#print the value for zabbix
print zabbixvalue
#exit with exitstatus
exit(exitstatus)
# vim: ai ts=4 sts=4 et sw=4 ft=python
