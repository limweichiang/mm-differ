# ArubaOS 8 mm-differ

## Objective
mm-differ is built to validate that the Aruba OS 8 Mobility Master configuration hierarchies and configurations within the hierachies are identical between and Active and Standby instance.

## Requirements
* Python 3 (Developed with Python 3.6.3; also tested on Python 3.7.4)
* Paramiko Module (Developed with Paramiko 2.6.0)

## Usage
```
$ python mm-differ.py -h
usage: mm-differ.py [-h] --first-mm FIRST_MM --second-mm SECOND_MM --admin
                    ADMIN

Aruba Mobility Master Configuration Hierarchy Comparator

optional arguments:
  -h, --help            show this help message and exit
  --first-mm FIRST_MM   First Mobility Master
  --second-mm SECOND_MM
                        Second Mobility Master
  --admin ADMIN         Mobility Master admin user name
```

## Example
```
$ python mm-differ.py --first-mm 192.168.1.31 --second-mm 192.168.1.32 --admin admin
Password for admin: 
Connecting to MM1 - 192.168.1.31...
Connecting to MM2 - 192.168.1.32...

Verifying configuration hierarchy is identical across MMs...
192.168.1.31 : ['/', '/md', '/md/wlan', '/md/wlan/cluster', '/md/wlan/cluster/00:00:29:00:00:01', '/md/wlan/cluster/00:00:29:00:00:02', '/md/wlan/standalone', '/mm', '/mm/mynode']
192.168.1.32 : ['/', '/md', '/md/wlan', '/md/wlan/cluster', '/md/wlan/cluster/00:00:29:00:00:01', '/md/wlan/cluster/00:00:29:00:00:02', '/md/wlan/standalone', '/mm', '/mm/mynode']
Successful

Verifying configuration at each hierarchy level is consistent across MMs...
 - Verifying config node / is consistent... Successful
 - Verifying config node /md is consistent... Successful
 - Verifying config node /md/wlan is consistent... Successful
 - Verifying config node /md/wlan/cluster is consistent... Successful
 - Verifying config node /md/wlan/cluster/00:00:29:00:00:01 is consistent... Successful
 - Verifying config node /md/wlan/cluster/00:00:29:00:00:02 is consistent... Successful
 - Verifying config node /md/wlan/standalone is consistent... Successful
 - Verifying config node /mm is consistent... Successful
 - Verifying config node /mm/mynode is consistent... Failed... Running diff to show differences
 -- '-' denote lines unique to 192.168.1.31
 -- '+' denote lines unique to 192.168.1.32
  master-l3redundancy 
      l3-peer-ip-address 192.168.2.30 ipsec [redacted]  
      l3-sync-state Primary 
      l3-sync-time 2 
  !
  controller-ip vlan 101 
  interface mgmt 
      shutdown 
  !
- vlan 1 
- !
  vlan 101 
  !
  interface gigabitethernet 0/0/0 
-     description GE0/0/0 
      switchport mode trunk 
-     switchport trunk allowed vlan 1,101 
      no spanning-tree 
      trusted 
      trusted vlan 1-4094 
  !
[... snipped ...]
  interface vlan 101 
-     ip address 192.168.1.31 255.255.255.0 
?                          ^
+     ip address 192.168.1.32 255.255.255.0 
?                          ^
  !
  ip default-gateway 192.168.1.1 
+ mgmt-user admin root [redacted] 
- mgmt-user admin root [redacted]  
- ip name-server 1.1.1.1 
- 
- hostname mm1 
?            ^
+ hostname mm2 
?            ^
  clock timezone Asia/Singapore 
  country SG 
  vrrp 101 
      ip address 192.168.1.30 
-     description "MM VRRP" 
      authentication [redacted]  
-     preempt 
-     priority 255 
      vlan 101 
      no shutdown 
  !
  master-redundancy 
  !
```
