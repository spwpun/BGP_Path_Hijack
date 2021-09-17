#!/usr/bin/env python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, info, setLogLevel
from mininet.util import dumpNodeConnections, quietRun, moveIntf
from mininet.cli import CLI
from mininet.node import Switch, OVSKernelSwitch

from subprocess import Popen, PIPE, check_output
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

import sys
import os
import termcolor as T
import time

setLogLevel('info')

parser = ArgumentParser("Configure simple BGP network in Mininet.")
parser.add_argument('--rogue', action="store_true", default=False)
parser.add_argument('--sleep', default=3, type=int)
args = parser.parse_args()

FLAGS_rogue_as = args.rogue
ROGUE_AS_NAME = 'S4'

def log(s, col="green"):
    # Up to python3
    # print T.colored(s, col)
    print(T.colored(s,col))


class Router(Switch):
    """Defines a new router that is inside a network namespace so that the
    individual routing entries don't collide.

    """
    ID = 0
    def __init__(self, name, **kwargs):
        kwargs['inNamespace'] = True
        Switch.__init__(self, name, **kwargs)
        Router.ID += 1
        self.switch_id = Router.ID

    @staticmethod
    def setup():
        return

    def start(self, controllers):
        pass

    def stop(self):
        self.deleteIntfs()

    def log(self, s, col="magenta"):
        print(T.colored(s, col))
        #print T.colored(s, col)


class SimpleTopo(Topo):
    """The Autonomous System topology is a simple straight-line topology
    between AS1 -- AS2 -- AS3.  The rogue AS (AS4) connects to AS1 directly.

    """
    def __init__(self):
        # Add default members to class.
        super(SimpleTopo, self ).__init__()
        num_hosts_per_as = 3
        num_ases = 3
        num_hosts = num_hosts_per_as * num_ases
        # The topology has one router per AS
        routers = []
        for i in range(num_ases):
            router = self.addSwitch('S%d' % (i+1))
            routers.append(router)
        hosts = []
        for i in range(num_ases):
            router = 'S%d' % (i+1)
            for j in range(num_hosts_per_as):
                hostname = 'h%d-%d' % (i+1, j+1)
                host = self.addHost(hostname, ip = "1%d.0.%d.1/24"%(i+1, j+1), defaultRoute = "via 1%d.0.%d.254"%(i+1, j+1))
                hosts.append(host)
                self.addLink(router, host)
        # Add links between in ASes!
        for i in range(num_ases-1):
            self.addLink('S%d'%(i+1), 'S%d'%(i+2))

        # Lastly, added AS4!
        routers.append(self.addSwitch('S4'))
        for j in range(num_hosts_per_as):
            hostname = 'h%d-%d' % (4, j+1)
            host = self.addHost(hostname, ip = "13.0.%d.1/24"%(j+1), defaultRoute = "via 13.0.%d.254"%(j+1))
            hosts.append(host)
            self.addLink('S4', hostname)
        # This MUST be added at the end
        self.addLink('S1', 'S4')
        return


def getIP(hostname):
    AS, idx = hostname.replace('h', '').split('-')
    AS = int(AS)
    if AS == 4:
        AS = 3
    ip = '%s.0.%s.1/24' % (10+AS, idx)
    return ip


def getGateway(hostname):
    AS, idx = hostname.replace('h', '').split('-')
    AS = int(AS)
    # This condition gives AS4 the same IP range as AS3 so it can be an
    # attacker.
    if AS == 4:
        AS = 3
    gw = '%s.0.%s.254' % (10+AS, idx)
    return gw


def startWebserver(net, hostname, text="Default web server"):
    host = net.getNodeByName(hostname)
    return host.popen("sudo python3 webserver.py --text '%s'" % text, shell=True)


def main():
    os.system("rm -f /tmp/S*.log /tmp/S*.pid logs/*")
    os.system("mn -c >/dev/null 2>&1")
    os.system("killall -9 zebra bgpd > /dev/null 2>&1")
    os.system('pgrep -f webserver.py | xargs kill -9')

    net = Mininet(topo=SimpleTopo(), switch=Router)
    net.start()
    for router in net.switches:
        router.cmd("sudo sysctl -w net.ipv4.ip_forward=1")
        router.waitOutput()

    log("Waiting %d seconds for sysctl changes to take effect..."
        % args.sleep)
    sleep(args.sleep)

    for router in net.switches:
        if router.name == ROGUE_AS_NAME and not FLAGS_rogue_as:
            continue
        router.cmd("/home/mininet/usr/lib/frr/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid > logs/%s-zebra-stdout 2>&1" % (router.name, router.name, router.name))
        router.waitOutput()
        router.cmd("/home/mininet/usr/lib/frr/bgpd -f conf/bgpd-%s.conf -d -i /tmp/bgp-%s.pid > logs/%s-bgpd-stdout 2>&1" % (router.name, router.name, router.name), shell=True)
        # mannual start the interface 'lo'
        router.cmd("ifconfig lo up")
        # mannual add the route table
        #if router.name == "S1":
        #   router.cmd("route add -net 12.0.0.0/8 gw 9.0.0.2")
        #    router.cmd("route add -net 13.0.0.0/8 gw 9.0.0.2")
        #elif router.name == "S2":
        #    router.cmd("route add -net 11.0.0.0/8 gw 9.0.0.1")
        #    router.cmd("route add -net 13.0.0.0/8 gw 9.0.1.2")
        #elif router.name == "S3":
        #    router.cmd("route add -net 11.0.0.0/8 gw 9.0.1.1")
        #    router.cmd("route add -net 12.0.0.0/8 gw 9.0.1.1")
        router.waitOutput()
        log("Starting zebra and bgpd on %s" % router.name)

    for host in net.hosts:
    #    host.cmd("ifconfig %s-eth0 %s" % (host.name, getIP(host.name)))
        log("Config host %s-eth0 %s, gateway: %s"%(host.name, getIP(host.name), getGateway(host.name)))
    #    host.cmd("route add default gw %s" % (getGateway(host.name)))

    log("Starting web servers", 'yellow')
    startWebserver(net, 'h3-1', "Default web server")
    startWebserver(net, 'h4-1', "*** Attacker web server ***")

    CLI(net)
    net.stop()
    os.system("killall -9 zebra bgpd")
    os.system('pgrep -f webserver.py | xargs kill -9')


if __name__ == "__main__":
    main()
