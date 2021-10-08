#!/usr/bin/python3


import json
import sys
import time
import os
import getopt
import cats
from operator import itemgetter

API_CLIENT_ID = "insertyourown"
API_KEY= "insertyourown"
VERBOSE = False
def print_help():
    print("running python " + str(sys.version_info))
    name = os.path.basename(__file__)
    print("Usage: " + name + " -h -d -v -X -t <table>")
    print(".. where options are ")
    print("  -h : help (this text)")
    print("  -v : verbose output")
    print("  -d : prints debug messages")
    print(" -t  <mac or hostname> build duplicate table based on mac or hostname")
    print("  -X : deletes the suggested duplicates")
    print()
    print('Script assumes a file creds.json with  structure: {"cloud":"cloud-geo","api_key":"your api key","api_client_id":"your client id"')
    print('cloud-geo should be one of us or eu')

def populate_tables_with_response(rsp,GUIDS,HOSTNAMES,MACS):
    hostname    = ""
    guid = ""
    data = rsp["data"]

    print("Number of cmmputers returned: {}".format(str(len(data))))
    # loop through all computers and store in GUIDS, HOSTNAMES, and MACS
    count = 0
    for computer in data:
        count = count +1
        if VERBOSE and count % 30 == 0:
            print("Processing number {}".format(str(count)))
        # iteration handling one Computer (identified by GUID) - populate the details for this computer
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
            "mac_string": "",
            "last_seen" : last_seen,
            "install_date" : install_date
        }
        ## append the details to the table keyed on GUIDs, should have no duplicates
        if connector_guid in GUIDS:
            print("found duplicate GUID "+guid)
            print("This should never happen!!!")
            GUIDS[connector_guid].append(details)
        else:
            GUIDS[connector_guid] = [details]
        
        ## add the details to the table for hostnames, this is a structure keyed on hostnames with a list of details
        ## if there are no duplicates (only one GUID for the hostname, the list will only contain one entry)
        if hostname in HOSTNAMES:
            if VERBOSE:
                print("found duplicate HOSTNAME "+hostname)
            HOSTNAMES[hostname].append(details)
        else:
            HOSTNAMES[hostname] = [details]

        ## add the details to the table for MAC addresses, this is a structure keyed on MACs witha list of details
        ## if there are no duplicates (only one GUID for the same hostname, the list will contain only one entry)
        ## we have to interate through each of the MAC addresses of the retrieved computer since there may be more than one
        if "network_addresses" in computer:
            network_addresses = computer["network_addresses"]
            for network_address in network_addresses:
                # iterate through all the interface card of the computer, each with different mac
                mac = network_address["mac"]
                if details["mac_string"]:
                    details["mac_string"] = details["mac_string"] + " " + mac
                else:
                    details["mac_string"] = mac
                    
                if mac in MACS:
                    ## the mac has been previously stored, check if we have a new GUID
                    this_mac = MACS[mac]
                    for m in this_mac:
                        if connector_guid != m["guid"]:
                            MACS[mac].append(details)
                            if VERBOSE:
                                print("found duplicate MAC with a different GUID "+mac)
                            break
                        else:
                            if VERBOSE:
                                print("found duplicate MAC  - but with same GUID:"+mac)

                else:
                    MACS[mac] = [details]
def main(argv):

    table = "mac"
    debug = False 
    delete = False
    VERBOSE = False
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
            VERBOSE = True
        if opt == ("-v"):
            VERBOSE = True
        if opt == '-X':
            delete = True
        if opt == "-t":
            table = arg
            if table != "mac" and table != "hostname":
                print("table should be either mac or hostname")
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

    if VERBOSE:
        print("Using CLOUD {} with API CLIENT ID {} and API KEY {}".format(CLOUD,API_CLIENT_ID,API_KEY))
    a = cats.AMP(cloud=CLOUD,api_client_id=API_CLIENT_ID,api_key=API_KEY,debug=debug,logfile="")

    #get all computers
    more = True
    block = 1
    while more:
        if VERBOSE:
            print("Fetching block {}".format(str(block)))
        (more,rsp) = a.getALLcomputers(block==1)
        populate_tables_with_response(rsp,GUIDS,HOSTNAMES,MACS)
        block = block + 1

    print("GUIDS table contains {} entries".format(str(len(GUIDS))))
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
    print("{} contains {} entries".format(itemname,str(len(TABLE))))
    duplicates_found = 0
    duplicates_deleted = 0
    for item in TABLE:
        if TABLE[item] and len(TABLE[item]) >1:
            print()
            print("-------------------------------------------------------")
            print("{} duplicate(s) Found for {} : {}".format(str(len(TABLE[item])-1),itemname,item))
            print("-------------------------------------------------------")
            print("Most recently seen with this {}: at top marked with >".format(itemname))
            print()
            print("{:<3}{:<38}{:<22}{:<22}{:<30}{}".format("?","GUID","LAST SEEN","INSTALLED","HOSTNAME","MAC ADDRESSES"))

            sorted_list = sorted(TABLE[item],key=itemgetter("last_seen"),reverse=True)
            duplicates_found = duplicates_found + len(sorted_list)-1
            most_recent = True

            for s in sorted_list:
                if most_recent:
                    sign = ">"
                else:
                    sign = "-"
                print("{:<3}{:<38}{:<22}{:<22}{:<30}{}".format(sign,s["guid"],s["last_seen"],s["install_date"],s["hostname"],s["mac_string"]))
                if not most_recent and delete:
                    answer = input("Delete this computer with GUID {}  [Y/y] [Q/q] for quit, any other character to go to next item: ".format(s["guid"]))
                    if (answer == "q" or answer =="Q"):
                        print("quitting before finding all duplicates....")
                        return()
                    if (answer == "y" or answer == "Y"):
                        # dum = a.computerDelete(guid=s["guid"])
                        duplicates_deleted = duplicates_deleted + 1
                        
                most_recent = False
    print()
    print("*********** SUMMARY *************************")
    print("Found {} duplicates: ".format(str(duplicates_found)))
    print("Deleted {} duplicates: ".format(str(duplicates_deleted)))

   
if __name__ == "__main__":
    main(sys.argv[1:])
