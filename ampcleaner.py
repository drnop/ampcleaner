#!/usr/bin/python3


import json
import sys
import pprint
import time
import os
import getopt
import re
import cats
from operator import itemgetter

API_CLIENT_ID = "insertyourown"
API_KEY= "insertyourown"

def print_help():
    print("running python " + str(sys.version_info))
    name = os.path.basename(__file__)
    print("Usage: " + name + " -h -d debug -X -m group ")
    print(".. where options are ")
    print("  -h : help (this text)")
    print("  -v : verbose output")
    print("  -d : prints debug messages")
    print(" -t  <mac or hostname> build duplicate table based on mac or hostname")
    print("  -X : deletes the suggested duplicates")
    print(" -m groupname : moves the suggested duplicates to group")
    print()
    print('Script assumes a file creds.json with  structure: {"cloud":"cloud-geo","api_key":"your api key","api_client_id":"your client id"')
    print('cloud-geo should be one of us or eu')

  
def main(argv):

    table = "mac"
    debug = False 
    verbose = False  
    internal_ip = ""
    external_ip = ""
    hostname    = ""
    guid = ""
    destgroup = ""
    move = False
    delete = False

    GUIDS = {}
    MACS = {}
    HOSTNAMES = {}

    try:
        opts, args = getopt.getopt(argv,"hvdXm:t:")
    except getopt.GetoptError:
        print_help()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_help()
            sys.exit(2)
        if opt == ("-d"):
            debug = True
            verbose = True
        if opt == ("-v"):
            verbose = True
        if opt == '-X':
            delete = True
        if opt == "-t":
            table = arg
            if table != "mac" and table != "hostname":
                print("table should be either mac or hostname")
                sys.exit(2)
        if opt == ("-m"):
            move = True
            destgroup = arg
      
    if move and delete:
        print("You cannot both move and delete duplicates!")
        sys.exit(2)

    try:
        creds = json.loads(open("ampapi.json").read())
        CLOUD = creds["cloud"]
        API_CLIENT_ID = creds["api_client_id"]    
        API_KEY = creds["api_key"]
    except Exception as e:
        print(str(e))
        print("Failed to open ampapi.json")
        print("Ensure you have defined API_KEYs in the script for the script to work")
        sys.exit(2)

    if debug:
        print("Using API CLIENT ID {} and API KEY {}".format(API_CLIENT_ID,API_KEY))
    a = cats.AMP(cloud=CLOUD,api_client_id=API_CLIENT_ID,api_key=API_KEY,debug=debug,logfile="")

    if move:
        rsp = a.groups(groupname=destgroup)
        print(json.dumps(rsp,indent=4,sort_keys=True))

    #get all computers
    rsp = a.computers(internal_ip=internal_ip,external_ip=external_ip,hostname=hostname)
    data = rsp["data"]

    # loop through all computers and store in GUIDS, HOSTNAMES, and MACS
    for computer in data:
        connector_guid = computer["connector_guid"]
        hostname = computer["hostname"]
        if "network_addresses" in computer:
            network_addresses = computer["network_addresses"]
        else:
            network_addresses = []
        install_date = computer["install_date"]
        last_seen = computer["last_seen"]
        details = {
            "guid" : connector_guid,
            "hostname": hostname,
            "network_addresses": network_addresses,
            "last_seen" : last_seen,
            "install_date" : install_date
        }
        if connector_guid in GUIDS:
            print("found duplicate GUIID "+guid)
            GUIDS[connector_guid].append(details)
        else:
            GUIDS[connector_guid] = [details]
           
        if hostname in HOSTNAMES:
            print("found duplicate HOSTNAME "+hostname)
            HOSTNAMES[hostname].append(details)
        else:
            HOSTNAMES[hostname] = [details]
        #print(json.dumps(computer,indent=4,sort_keys=True))
        if "network_addresses" in computer:
            network_addresses = computer["network_addresses"]
            for network_address in network_addresses:
                mac = network_address["mac"]
                if mac in MACS:
                    this_mac = MACS[mac]
                    for m in this_mac:
                        if connector_guid != m["guid"]:
                            MACS[mac].append(details)
                            print("found duplicate MAC "+mac)
                            break
                        else:
                            print("found duplicate MAC  - but with same Connector Guid:"+mac)

                else:
                    MACS[mac] = [details]
        
    print("GUIDS")
    for item in GUIDS:
        if len(GUIDS[item]) >1:
            print("Duplicate Found for GUID: Should not happen!!!! " + item)
            print(json.dumps(GUIDS[item],indent=4,sort_keys=True))

    # ok 
    if table == "hostname":
        TABLE = HOSTNAMES
        print("CHECKING FOR DUPLICATE HOSTNAMES")
        itemname = "HOSTNAME"
    else:
        TABLE = MACS
        print("CHECKING FOR DUPLICATE MACS")
        itemname = "MAC"
    for item in TABLE:
        if TABLE[item] and len(TABLE[item]) >1:
            print("-----------------------------------")
            print("Duplicate(s) Found for {} : {}".format(itemname,item))
            print("-----------------------------------")
            sorted_list = sorted(TABLE[item],key=itemgetter("last_seen"),reverse=True)
            most_recent = True
            for s in sorted_list:
                #print(json.dumps(s,indent=4,sort_keys=True))
                if most_recent:
                    print("Most recently seen with this {}:".format(itemname))
                else:
                   
                    print("Likely stale duplicate of the most recently seen computer with this MAC")
                print("GUID: {} SEEN: {} INSTALLED: {} HOSTNAME:{} MACS:{}".format(s["guid"],s["last_seen"],s["install_date"],s["hostname"],str(s["network_addresses"])))
                
                if not most_recent and delete:
                    answer = input("Delete this computer with GUID {}  [Y/y]".format(s["guid"]))
                    if (answer == "y" or answer == "Y"):
                        dum = a.computerDelete(guid=s["guid"])
                        
                most_recent = False

   
if __name__ == "__main__":
    main(sys.argv[1:])
