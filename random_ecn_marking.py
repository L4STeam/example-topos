import subprocess

from ipmininet.clean import cleanup
from ipmininet.cli import IPCLI
from ipmininet.ipnet import IPNet
from ipmininet.iptopo import IPTopo
from ipmininet.router.config import OSPF
from ipmininet.router.config.base import RouterConfig
from ipmininet.router.config.ospf import OSPFRedistributedRoute


class MinimalRandomECNNet(IPTopo):
    """

    client ---- r1 ---- r2 ---- r3 ---- server

    """
    def __init__(self, *args, **kwargs):
        super(MinimalRandomECNNet, self).__init__(*args, **kwargs)

    def build(self, *args, **kwargs):
        r1 = self.addRouter("r1", config=RouterConfig)
        r1.addDaemon(OSPF)
        r2 = self.addRouter("r2", config=RouterConfig)
        r2.addDaemon(OSPF)
        r3 = self.addRouter("r3", config=RouterConfig)
        r3.addDaemon(OSPF)
        self.addLink(r1, r2, params1={"ip": "10.0.0.1/24"}, params2={"ip": "10.0.0.2/24"})
        self.addLink(r2, r3, params1={"ip": "10.0.1.1/24"}, params2={"ip": "10.0.1.2/24"})

        client = self.addHost("client")
        self.addLink(r1, client, params1={"ip": "10.1.0.1/24"}, params2={"ip": "10.1.0.2/24"})

        server = self.addHost("server")
        self.addLink(r3, server, params1={"ip": "10.2.0.1/24"}, params2={"ip": "10.2.0.2/24"})

        super(MinimalRandomECNNet, self).build(*args, **kwargs)

if __name__ == "__main__":
    try:
        subprocess.check_call(["modprobe", "prague"])
        net = IPNet(topo=MinimalRandomECNNet(), allocate_IPs=False)
        net.start()

        # Set TCP Prague for client1 and server1 and cubic for client2 and server2 Congestion Control on client1 and server1
        net["client1"].cmd("sysctl -w net.ipv4.tcp_congestion_control=prague")
        net["server1"].cmd("sysctl -w net.ipv4.tcp_congestion_control=prague")
        net["client2"].cmd("sysctl -w net.ipv4.tcp_congestion_control=cubic")
        net["server2"].cmd("sysctl -w net.ipv4.tcp_congestion_control=cubic")

        # Setup random ecn marking
        net["r2"].cmd("tc qdisc del dev r2-eth0")
        net["r2"].cmd("tc qdisc add dev r2-eth0 root handle 1:0 htb default 1 direct_qlen 1000")
        net["r2"].cmd("tc class add dev r2-eth0 parent 1:0 classid 1:1 htb rate 40Mbit ceil 40Mbit")
        net["r2"].cmd("tc qdisc add dev r2-eth0 parent 1:1 handle 2:0 netem loss 10 ecn")  # Mark 10% of packets with ECN

        IPCLI(net)
        net.stop()
    finally:
        cleanup()

