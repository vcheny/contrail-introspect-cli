# contrail-introspect-cli
This script provides a Contrail CLI command mainly for troubleshooting purpose. It retrieves XML output from introspect services provided by Contrail main components e.g. control, config and compute(vrouter) nodes and makes them CLI friendly.

Contrail 2.22+ is supported.

Note: Entire scripts is kept in one single file intentionally for easy use.

## How to run
* Just like a regular python script
* It can run remotely or directly from control/compute nodes
* Python lib lxml and prettytable are required

## Usage

Use ```-h``` to list possible command options

```
root@comp45:~# ist -h
usage: ist [-h] [--version] [--debug] [--max-width MAX_WIDTH]
           {vr,ctr,cfg-api,cfg-sch,cfg-svc,collector,analytics} ...

A script to make Contrail Introspect output CLI friendly.

positional arguments:
  {vr,ctr,cfg-api,cfg-sch,cfg-svc,collector,analytics}
    vr                  Show vRouter info
    ctr                 Show Control node info
    cfg-api             Show contrail-api info
    cfg-sch             Show contrail-schema info
    cfg-svc             Show contrail-svc-monitor info
    collector           Show contrail-collector info
    analytics           Show contrail-analytics-api info

optional arguments:
  -h, --help            show this help message and exit
  --version             Show script version
  --debug               debug mode
  --max-width MAX_WIDTH
                        max width per column

root@comp45:~# ist vr -h
usage: ist vr [-h] [-H HOST] [-P PORT]
              {status,cpu,trace,uve,intf,vn,vrf,route,sg,acl,xmpp,xmpp-dns,stats,service}
              ...

positional arguments:
  {status,cpu,trace,uve,intf,vn,vrf,route,sg,acl,xmpp,xmpp-dns,stats,service}
    status              show node/component status
    cpu                 Show CPU load info
    trace               Show Sandesh trace buffer
    uve                 Show Sandesh UVE cache
    intf                Show vRouter interfaces
    vn                  Show Virtual Network
    vrf                 Show VRF
    route               Show routes
    sg                  Show Security Groups
    acl                 Show ACL info
    xmpp                Show Agent XMPP connections (route&config) status
    xmpp-dns            Show Agent XMPP connections (dns) status
    stats               Show Agent stats
    service             Service related info

optional arguments:
  -h, --help            show this help message and exit
  --host HOST           Introspect host(default='localhost')
  --port PORT           Introspect port(default='8085')

root@comp45:~# ist vr intf -h
usage: ist vr intf [-h] [-u UUID] [-v VN] [-m MAC] [-i IPV4] [-d] [name]

positional arguments:
  name                  Interface name

optional arguments:
  -h, --help            show this help message and exit
  -u UUID, --uuid UUID  Interface uuid
  -v VN, --vn VN        Virutal network
  -m MAC, --mac MAC     VM mac address
  -i IPV4, --ipv4 IPV4  VM IP address
  -d, --detail          Display detailed output
```

## Examples

### How to run
* from local
```
ist {vr,ctr,cfg-api,cfg-sch, cfg-svc,collector,analytics}

root@cont201:~# ist ctr status
module_id: contrail-control
state: Functional
```
* from remote
```
ist {vr,ctr,cfg-api,cfg-sch, cfg-svc} -H <Node IP>

[cheny-mbp:~]$ ist ctr --host cont201 status
module_id: contrail-control
state: Functional
```

### vRouter commands

* Interface related
```
root@comp45:~# ist vr intf -h
usage: ist vr intf [-h] [-u UUID] [-v VN] [-m MAC] [-i IPV4] [-d] [name]

positional arguments:
  name                  Interface name

optional arguments:
  -h, --help            show this help message and exit
  -u UUID, --uuid UUID  Interface uuid
  -v VN, --vn VN        Virutal network
  -m MAC, --mac MAC     VM mac address
  -i IPV4, --ipv4 IPV4  VM IP address
  -d, --detail          Display detailed output

[cheny-mbp:~]$ ist vr -H comp45 intf tap
+-------+----------------+--------+-------------------+---------------+---------------+------------+----------------------------+
| index | name           | active | mac_addr          | ip_addr       | mdata_ip_addr | vm_name    | vn_name                    |
+-------+----------------+--------+-------------------+---------------+---------------+------------+----------------------------+
| 4     | tap2df2ce68-23 | Active | 02:76:c4:8a:88:1d | 10.10.10.4    | 169.254.0.4   | VSRX-FW001 | default-domain:admin:VN-L  |
| 5     | tapa66c059a-73 | Active | 02:d7:b7:2f:1b:b0 | 20.20.20.4    | 169.254.0.5   | VSRX-FW001 | default-domain:admin:VN-R  |
| 3     | tapd47cd238-33 | Active | 02:29:49:5d:e5:d3 | 100.100.100.3 | 169.254.0.3   | VSRX-FW001 | default-domain:admin:Dummy |
+-------+----------------+--------+-------------------+---------------+---------------+------------+----------------------------+

root@comp45:~# ist vr intf -v default-domain:admin:VN-L
+-------+----------------+--------+-------------------+------------+---------------+------------+---------------------------+
| index | name           | active | mac_addr          | ip_addr    | mdata_ip_addr | vm_name    | vn_name                   |
+-------+----------------+--------+-------------------+------------+---------------+------------+---------------------------+
| 4     | tap2df2ce68-23 | Active | 02:76:c4:8a:88:1d | 10.10.10.4 | 169.254.0.4   | VSRX-FW001 | default-domain:admin:VN-L |
+-------+----------------+--------+-------------------+------------+---------------+------------+---------------------------+

root@comp45:~# ist vr intf tap2df2ce68-23 -d
ItfSandeshData
  index: 4
  name: tap2df2ce68-23
  uuid: 2df2ce68-233e-4f5b-a8f7-e0f8f55ccf31
  vrf_name: default-domain:admin:VN-L:VN-L
  active: Active
  dhcp_service: Enable
  dns_service: Enable
  type: vport
  label: 21
  vn_name: default-domain:admin:VN-L
  vm_uuid: 5075756e-ae49-4ced-88f8-46af16bfce3f
  vm_name: VSRX-FW001
  ip_addr: 10.10.10.4
  mac_addr: 02:76:c4:8a:88:1d
  policy: Enable
  fip_list
  mdata_ip_addr: 169.254.0.4
  service_vlan_list
  os_ifindex: 22
  fabric_port: NotFabricPort
  alloc_linklocal_ip: LL-Enable
  analyzer_name
  config_name: default-domain:admin:default-domain__admin__VSRX-FW__1__left__2
  sg_uuid_list
      VmIntfSgUuid
        sg_uuid: 8617f504-d10f-43dc-a0cc-93c8bb670f5f
  l2_label: 22
  vxlan_id: 5
  static_route_list
  l2_active: L2 Active
  vm_project_uuid: 513f8055-4f25-4f24-b9af-d542ee95c57f
  admin_state: Enabled
  flow_key_idx: 34
  allowed_address_pair_list
  ip6_addr: ::
  ip6_active: Ipv6 Inactive < no-ipv6-addr  >
  local_preference: 0
  tx_vlan_id: -1
  rx_vlan_id: -1
  parent_interface
  sub_type: Tap
  vrf_assign_acl_uuid: 2df2ce68-233e-4f5b-a8f7-e0f8f55ccf31
  vmi_type: Virtual Machine
  transport: Ethernet
  logical_interface_uuid: 00000000-0000-0000-0000-000000000000
  flood_unknown_unicast: false
  physical_device
  physical_interface
  ipv4_active: Active
  fixed_ip4_list
      10.10.10.4
  fixed_ip6_list
  fat_flow_list
  ```

* vrf related

```
root@comp45:~# ist vr vrf -h
usage: ist vr vrf [-h] [-d] [name]

positional arguments:
  name          VRF name

optional arguments:
  -h, --help    show this help message and exit
  -d, --detail  Display detailed output

root@comp76:~# ist vr vrf
+--------------------------------------------------------------+---------+---------+---------+-----------+----------+---------------------------+
| name                                                         | ucindex | mcindex | brindex | evpnindex | vxlan_id | vn                        |
+--------------------------------------------------------------+---------+---------+---------+-----------+----------+---------------------------+
| default-domain:admin:MGT:MGT                                 | 2       | 2       | 2       | 2         | 14       | default-domain:admin:MGT  |
| default-domain:admin:VN-L:VN-L                               | 3       | 3       | 3       | 3         | 5        | default-domain:admin:VN-L |
| default-domain:admin:VN-L:service-cc571e38-0cc7-42cc-b0d2    | 4       | 4       | 4       | 4         | 0        | N/A                       |
| -96dc3b77df2e-default-domain_admin_HairpinFW                 |         |         |         |           |          |                           |
| default-domain:admin:VN-R:VN-R                               | 1       | 1       | 1       | 1         | 4        | default-domain:admin:VN-R |
| default-domain:admin:VN-R:service-cc571e38-0cc7-42cc-b0d2    | 5       | 5       | 5       | 5         | 0        | N/A                       |
| -96dc3b77df2e-default-domain_admin_HairpinFW                 |         |         |         |           |          |                           |
| default-domain:default-project:ip-fabric:__default__         | 0       | 0       | 0       | 0         | 0        | N/A                       |
+--------------------------------------------------------------+---------+---------+---------+-----------+----------+---------------------------+

root@comp76:~# ist vr vrf default-domain:admin:VN-L:VN-L -d
VrfSandeshData
  name: default-domain:admin:VN-L:VN-L
  ucindex: 3
  mcindex: 3
  l2index: 3
  source: Config;
  uc6index: 3
  vn: default-domain:admin:VN-L
  table_label: -1
  vxlan_id: 5
  evpnindex: 3
  brindex: 3
```

* route related
```
root@comp45:~# ist vr route -h
usage: ist vr route [-h] [-v VRF] [-f {inet,inet6,bridge,layer2,evpn}]
                    [-p PREFIX] [-d] [-r]
                    [address]

positional arguments:
  address               Address

optional arguments:
  -h, --help            show this help message and exit
  -v VRF, --vrf VRF     VRF index, default: 0 (IP fabric)
  -f {inet,inet6,bridge,layer2,evpn}, --family {inet,inet6,bridge,layer2,evpn}
                        Route family
  -p PREFIX, --prefix PREFIX
                        IPv4 or IPv6 prefix
  -d, --detail          Display detailed output
  -r, --raw             Display raw output in plain text

root@comp45:~# ist vr route -v 3
10.10.10.0/24
    [Local] pref:100
     nh_index:1 , nh_type:discard, nh_policy:disabled, active_label:-1, vxlan_id:0
10.10.10.1/32
    [Local] pref:100
     to 0:0:0:0:0:1 via pkt0, assigned_label:-1, nh_index:7 , nh_type:interface, nh_policy:disabled, active_label:-1, vxlan_id:0
10.10.10.2/32
    [Local] pref:100
     to 0:0:0:0:0:1 via pkt0, assigned_label:-1, nh_index:7 , nh_type:interface, nh_policy:disabled, active_label:-1, vxlan_id:0
10.10.10.3/32
    [172.222.19.202] pref:200
     to f0:1c:2d:43:ee:2d via MPLSoUDP dip:172.222.19.205 sip:172.222.45.2 label:17, nh_index:21 , nh_type:tunnel, nh_policy:disabled, active_label:17, vxlan_id:0
    [172.222.19.203] pref:200
     to f0:1c:2d:43:ee:2d via MPLSoUDP dip:172.222.19.205 sip:172.222.45.2 label:17, nh_index:21 , nh_type:tunnel, nh_policy:disabled, active_label:17, vxlan_id:0
10.10.10.4/32
    [172.222.19.202] pref:200
     to 2:76:c4:8a:88:1d via tap2df2ce68-23, assigned_label:21, nh_index:34 , nh_type:interface, nh_policy:enabled, active_label:21, vxlan_id:0
    [172.222.19.203] pref:200
     to 2:76:c4:8a:88:1d via tap2df2ce68-23, assigned_label:21, nh_index:34 , nh_type:interface, nh_policy:enabled, active_label:21, vxlan_id:0
    [LocalVmPort] pref:200
     to 2:76:c4:8a:88:1d via tap2df2ce68-23, assigned_label:21, nh_index:34 , nh_type:interface, nh_policy:enabled, active_label:21, vxlan_id:0
20.20.20.3/32
    [172.222.19.202] pref:200
     to 2:76:c4:8a:88:1d via tap2df2ce68-23, assigned_label:21, nh_index:34 , nh_type:interface, nh_policy:enabled, active_label:21, vxlan_id:0
    [172.222.19.203] pref:200
     to 2:76:c4:8a:88:1d via tap2df2ce68-23, assigned_label:21, nh_index:34 , nh_type:interface, nh_policy:enabled, active_label:21, vxlan_id:0
20.20.20.4/32
    [172.222.19.202] pref:200
     to 2:76:c4:8a:88:1d via tap2df2ce68-23, assigned_label:21, nh_index:34 , nh_type:interface, nh_policy:enabled, active_label:21, vxlan_id:0
    [172.222.19.203] pref:200
     to 2:76:c4:8a:88:1d via tap2df2ce68-23, assigned_label:21, nh_index:34 , nh_type:interface, nh_policy:enabled, active_label:21, vxlan_id:0
33.100.100.1/32
    [172.222.19.202] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0
    [172.222.19.203] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0
169.254.169.254/32
    [LinkLocal] pref:100
     via vhost0, nh_index:6 , nh_type:receive, nh_policy:enabled, active_label:-1, vxlan_id:0
200.200.200.0/24
    [172.222.19.202] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0
    [172.222.19.203] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0

root@comp45:~# ist vr route -v 3 -p 200.200.200.0/24
200.200.200.0/24
    [172.222.19.202] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0
    [172.222.19.203] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0
root@comp45:~# ist vr route 3 -p 200.200.200.0/24 -d
200.200.200.0/24
    [172.222.19.202] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0
     dest_vn:[], sg:[], communities:[]
    [172.222.19.203] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0
     dest_vn:[], sg:[], communities:[]

root@comp45:~# ist vr route -v 3 -p 200.200.200.0/24 -r
RouteUcSandeshData
  src_ip: 200.200.200.0
  src_plen: 24
  src_vrf: default-domain:admin:VN-L:VN-L
  path_list
      PathSandeshData
        nh
          NhSandeshData
            type: tunnel
            ref_count: 8
            valid: true
            policy: disabled
            sip: 172.222.45.2
            dip: 192.168.0.204
            vrf: default-domain:default-project:ip-fabric:__default__
            mac: f0:1c:2d:43:ee:2d
            tunnel_type: MPLSoGRE
            nh_index: 17
            vxlan_flag: false
        label: 39
        vxlan_id: 0
        peer: 172.222.19.202
        dest_vn: default-domain:admin:VN-L
        unresolved: false
        sg_list
        supported_tunnel_type: MPLSoGRE
        active_tunnel_type: MPLSoGRE
        stale: false
        path_preference_data
          PathPreferenceSandeshData
            sequence: 0
            preference: 100
            ecmp: false
            wait_for_traffic: false
        active_label: 39
      PathSandeshData
        nh
          NhSandeshData
            type: tunnel
            ref_count: 8
            valid: true
            policy: disabled
            sip: 172.222.45.2
            dip: 192.168.0.204
            vrf: default-domain:default-project:ip-fabric:__default__
            mac: f0:1c:2d:43:ee:2d
            tunnel_type: MPLSoGRE
            nh_index: 17
            vxlan_flag: false
        label: 39
        vxlan_id: 0
        peer: 172.222.19.203
        dest_vn: default-domain:admin:VN-L
        unresolved: false
        sg_list
        supported_tunnel_type: MPLSoGRE
        active_tunnel_type: MPLSoGRE
        stale: false
        path_preference_data
          PathPreferenceSandeshData
            sequence: 0
            preference: 100
            ecmp: false
            wait_for_traffic: false
        active_label: 39
  ipam_subnet_route: false
  proxy_arp: true
  multicast: false

root@comp45:~# ist vr route 3 200.200.200.10
200.200.200.0/24
    [172.222.19.202] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0
    [172.222.19.203] pref:100
     to f0:1c:2d:43:ee:2d via MPLSoGRE dip:192.168.0.204 sip:172.222.45.2 label:39, nh_index:17 , nh_type:tunnel, nh_policy:disabled, active_label:39, vxlan_id:0
```

* Sandesh trace buffer
```
root@comp45:~# ist vr trace -h
usage: ist vr trace [-h] [name]

positional arguments:
  name        Trace buffer name, default: list available buffer names

optional arguments:
  -h, --help  show this help message and exit

root@comp45:~# ist vr trace
trace_buf_name: Acl
trace_buf_name: AgentDBwalkTrace
trace_buf_name: Arp
trace_buf_name: Config
trace_buf_name: Controller
trace_buf_name: ControllerDiscovery
trace_buf_name: ControllerInfo
trace_buf_name: ControllerRouteWalker
trace_buf_name: ControllerRxConfigXmppMessage
trace_buf_name: ControllerRxRouteXmppMessage
trace_buf_name: ControllerTxConfig
trace_buf_name: Dhcp
trace_buf_name: Dhcpv6
trace_buf_name: DiscoveryClient
trace_buf_name: DnsBind
trace_buf_name: Flow
trace_buf_name: FlowHandler
trace_buf_name: IFMapAgentTrace
trace_buf_name: IOTraceBuf
trace_buf_name: Icmpv6
trace_buf_name: KSync
trace_buf_name: KSync Error
trace_buf_name: Metadata
trace_buf_name: Multicast
trace_buf_name: Oper DB
trace_buf_name: OperIfmap
trace_buf_name: OperRouteTrace
trace_buf_name: Packet
trace_buf_name: PathPreference
trace_buf_name: TaskTrace
trace_buf_name: VersionTrace
trace_buf_name: Xmpp
trace_buf_name: XmppMessageTrace
trace_buf_name: XmppTrace

root@comp45:~# ist vr trace ControllerTxConfig | tail -n 9
</iq>
 file = controller/src/vnsw/agent/controller/controller_peer.cc line = 1596
1469069715363094 AgentXmppTrace: peer = 172.222.19.203 vrf =  event = <?xml version="1.0"?>
<iq type="set" from="comp45" to="network-control@contrailsystems.com/config">
<pubsub xmlns="http://jabber.org/protocol/pubsub">
<subscribe node="virtual-machine:5075756e-ae49-4ced-88f8-46af16bfce3f" />
</pubsub>
</iq>
 file = controller/src/vnsw/agent/controller/controller_peer.cc line = 1596

root@comp45:~# ist vr trace ControllerRxRouteXmppMessage | tail -n 33
1469200248365277 AgentXmppMessage: Received xmpp message from:  172.222.19.203 Port 5269 Size:  969 Packet:  <?xml version="1.0"?>
<message from="network-control@contrailsystems.com" to="comp45/bgp-peer">
	<event xmlns="http://jabber.org/protocol/pubsub">
		<items node="1/1/default-domain:admin:VN-R:VN-R">
			<item id="200.200.200.0/24">
				<entry>
					<nlri>
						<af>1</af>
						<safi>1</safi>
						<address>200.200.200.0/24</address>
					</nlri>
					<next-hops>
						<next-hop>
							<af>1</af>
							<address>172.222.45.2</address>
							<label>23</label>
							<tunnel-encapsulation-list>
								<tunnel-encapsulation>gre</tunnel-encapsulation>
								<tunnel-encapsulation>udp</tunnel-encapsulation>
							</tunnel-encapsulation-list>
						</next-hop>
					</next-hops>
					<version>1</version>
					<virtual-network>default-domain:admin:VN-L</virtual-network>
					<sequence-number>1</sequence-number>
					<security-group-list />
					<local-preference>200</local-preference>
					<med>100</med>
				</entry>
			</item>
		</items>
	</event>
</message> $ controller/src/vnsw/agent/controller/controller_init.cc 844
```

### Control node commands

* status
```
root@cont201:~# ist ctr status -d
module_id: contrail-control
state: Functional
description
Connetion Info:
+-----------+-------------+-------------------------+--------+--------------------------------------+
| type      | name        | server_addrs            | status | description                          |
+-----------+-------------+-------------------------+--------+--------------------------------------+
| IFMap     | IFMapServer | server_addrs            | Up     | Connection with IFMap Server (irond) |
|           |             |     172.222.19.203:8443 |        |                                      |
| Collector | n/a         | server_addrs            | Up     | Established                          |
|           |             |     172.222.19.201:8086 |        |                                      |
| Discovery | Collector   | server_addrs            | Up     | SubscribeResponse                    |
|           |             |     172.222.19.200:5998 |        |                                      |
| Discovery | IfmapServer | server_addrs            | Up     | SubscribeResponse                    |
|           |             |     172.222.19.200:5998 |        |                                      |
| Discovery | xmpp-server | server_addrs            | Up     | Publish Response - HeartBeat         |
|           |             |     172.222.19.200:5998 |        |                                      |
+-----------+-------------+-------------------------+--------+--------------------------------------+
```

* neighbor
```
root@cont201:~# ist ctr nei
+----------+----------------+----------+----------+-----------+-------------+-----------------+------------+-----------------------------+
| peer     | peer_address   | peer_asn | encoding | peer_type | state       | send_state      | flap_count | flap_time                   |
+----------+----------------+----------+----------+-----------+-------------+-----------------+------------+-----------------------------+
| cont202  | 172.222.19.202 | 13979    | BGP      | internal  | Established | in sync         | 0          | n/a                         |
| cont203  | 172.222.19.203 | 13979    | BGP      | internal  | Established | in sync         | 0          | n/a                         |
| sonics   | 192.168.0.200  | 13979    | BGP      | internal  | Established | in sync         | 0          | n/a                         |
| seahawks | 192.168.0.201  | 13979    | BGP      | internal  | Established | in sync         | 5          | 2016-Jul-26 09:30:07.886512 |
| camaro   | 192.168.0.204  | 13979    | BGP      | internal  | Active      | not advertising | 1          | 2016-Jul-28 12:06:24.868852 |
| comp204  | 172.222.19.204 | 0        | XMPP     | internal  | Established | in sync         | 0          | n/a                         |
| comp205  | 172.222.19.205 | 0        | XMPP     | internal  | Established | in sync         | 0          | n/a                         |
+----------+----------------+----------+----------+-----------+-------------+-----------------+------------+-----------------------------+
```

* vrf
```
root@cont201:~# ist ctr vrf  default-domain:admin:VN-L:VN-L
+--------------------------------+---------------------------+----------+----------+--------------------------+--------------------------+
| name                           | virtual_network           | vn_index | vxlan_id | import_target            | export_target            |
+--------------------------------+---------------------------+----------+----------+--------------------------+--------------------------+
| default-domain:admin:VN-L:VN-L | default-domain:admin:VN-L | 5        | 0        | import_target            | export_target            |
|                                |                           |          |          |     target:13979:33001   |     target:13979:33001   |
|                                |                           |          |          |     target:13979:8000002 |     target:13979:8000002 |
|                                |                           |          |          |     target:13979:8000004 |                          |
+--------------------------------+---------------------------+----------+----------+--------------------------+--------------------------+
```

* route related
```
root@cont201:~# ist ctr routes inet.0
+--------------------------------------------------------------+----------+-------+---------------+-----------------+------------------+
| name                                                         | prefixes | paths | primary_paths | secondary_paths | infeasible_paths |
+--------------------------------------------------------------+----------+-------+---------------+-----------------+------------------+
| default-domain:ATEST:VNx:VNx.inet.0                          | 0        | 0     | 0             | 0               | 0                |
| default-domain:admin:Dummy:Dummy.inet.0                      | 0        | 0     | 0             | 0               | 0                |
| default-domain:admin:MGT:MGT.inet.0                          | 0        | 0     | 0             | 0               | 0                |
| default-domain:admin:VN-L:VN-L.inet.0                        | 4        | 10    | 1             | 9               | 0                |
| default-domain:admin:VN-L:service-cc571e38-0cc7-42cc-b0d2    | 4        | 10    | 2             | 8               | 0                |
| -96dc3b77df2e-default-domain_admin_HairpinFW.inet.0          |          |       |               |                 |                  |
| default-domain:admin:VN-R:VN-R.inet.0                        | 4        | 10    | 1             | 9               | 0                |
| default-domain:admin:VN-R:service-cc571e38-0cc7-42cc-b0d2    | 4        | 10    | 2             | 8               | 0                |
| -96dc3b77df2e-default-domain_admin_HairpinFW.inet.0          |          |       |               |                 |                  |
| default-domain:default-                                      | 0        | 0     | 0             | 0               | 0                |
| project:__link_local__:__link_local__.inet.0                 |          |       |               |                 |                  |
| default-domain:default-project:default-virtual-network       | 0        | 0     | 0             | 0               | 0                |
| :default-virtual-network.inet.0                              |          |       |               |                 |                  |
| inet.0                                                       | 0        | 0     | 0             | 0               | 0                |
| default-domain:demo:hhao-left-net:hhao-left-net.inet.0       | 0        | 0     | 0             | 0               | 0                |
| default-domain:demo:hhao-left-v6net:hhao-left-v6net.inet.0   | 0        | 0     | 0             | 0               | 0                |
| default-domain:demo:hhao-right-net:hhao-right-net.inet.0     | 0        | 0     | 0             | 0               | 0                |
| default-domain:demo:hhao-right-v6net:hhao-right-v6net.inet.0 | 0        | 0     | 0             | 0               | 0                |
| default-domain:demo:hhao-test-left:hhao-test-left.inet.0     | 0        | 0     | 0             | 0               | 0                |
| default-domain:demo:mgt-net:mgt-net.inet.0                   | 0        | 0     | 0             | 0               | 0                |
+--------------------------------------------------------------+----------+-------+---------------+-----------------+------------------+

root@cont201:~# ist ctr route -h
usage: ist ctr route [-h] [-P PREFIX]
                     [-f {inet,inet6,evpn,ermvpn,rtarget,all}] [-l LAST] [-d]
                     [-r] [-p {BGP,XMPP,local,ServiceChain,all}] [-v VRF]
                     [-s SOURCE] [-t TABLE]
                     [address]

positional arguments:
  address               Show routes for given address

optional arguments:
  -h, --help            show this help message and exit
  -P PREFIX, --prefix PREFIX
                        Show routes exactally matching given prefix
  -f {inet,inet6,evpn,ermvpn,rtarget,all}, --family {inet,inet6,evpn,ermvpn,rtarget,all}
                        Show routes for given family. default:all
  -l LAST, --last LAST  Show routes modified during last time period (e.g.
                        10s, 5m, 2h, or 5d)
  -d, --detail          Display detailed output
  -r, --raw             Display raw output in plain text
  -p {BGP,XMPP,local,ServiceChain,all}, --protocol {BGP,XMPP,local,ServiceChain,all}
                        Show routes learned from given protocol
  -v VRF, --vrf VRF     Show routes in given routing instance
  -s SOURCE, --source SOURCE
                        Show routes learned from given source
  -t TABLE, --table TABLE
                        Show routes in given table


root@cont201:~# ist ctr route -t default-domain:admin:VN-L:VN-L.inet.0

default-domain:admin:VN-L:VN-L.inet.0: 6 destinations, 12 routes (1 primary, 11 secondary, 0 infeasible)

10.10.10.3/32, age: 1 day 12:40:44.546301, last_modified: 2016-Jul-21 02:53:34.144180
    [XMPP|comp205] age: 1 day 12:40:44.553029, localpref: 200, nh: 172.222.19.205, encap: ['gre', 'udp', 'udp-contrail'], label: 17, AS path: None
    [BGP|172.222.19.202] age: 1 day 12:28:15.575653, localpref: 200, nh: 172.222.19.205, encap: ['gre', 'udp', 'udp-contrail'], label: 17, AS path: None

10.10.10.4/32, age: 1 day 11:55:01.077706, last_modified: 2016-Jul-21 03:39:17.612775
    [BGP|172.222.19.202] age: 1 day 11:55:01.086113, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None
    [BGP|172.222.19.203] age: 1 day 11:55:01.087040, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None

20.20.20.3/32, age: 1 day 11:43:54.225656, last_modified: 2016-Jul-21 03:50:24.464825
    [ServiceChain|None] age: 1 day 11:43:54.235801, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None
    [BGP|172.222.19.202] age: 1 day 11:43:54.188976, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None
    [BGP|172.222.19.203] age: 1 day 11:43:54.193993, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None

20.20.20.4/32, age: 1 day 11:43:54.225236, last_modified: 2016-Jul-21 03:50:24.465245
    [ServiceChain|None] age: 1 day 11:43:54.238205, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None
    [BGP|172.222.19.202] age: 1 day 11:43:54.230359, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None
    [BGP|172.222.19.203] age: 1 day 11:43:54.196554, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None

33.100.100.1/32, age: 1 day 12:27:19.352008, last_modified: 2016-Jul-21 03:06:59.338473
    [BGP|192.168.0.204] age: 1 day 12:27:19.367453, localpref: 100, nh: 192.168.0.204, encap: [], label: 39, AS path: None

200.200.200.0/24, age: 0:23:30.329465, last_modified: 2016-Jul-22 15:10:48.361016
    [BGP|192.168.0.204] age: 0:23:30.345893, localpref: 100, nh: 192.168.0.204, encap: [], label: 39, AS path: None

root@cont201:~# ist ctr route -t default-domain:admin:VN-L:VN-L.inet.0 -P 10.10.10.4/32

default-domain:admin:VN-L:VN-L.inet.0: 6 destinations, 12 routes (1 primary, 11 secondary, 0 infeasible)

10.10.10.4/32, age: 1 day 12:01:50.982025, last_modified: 2016-Jul-21 03:39:17.612775
    [BGP|172.222.19.202] age: 1 day 12:01:50.987927, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None
    [BGP|172.222.19.203] age: 1 day 12:01:50.989104, localpref: 200, nh: 172.222.45.2, encap: ['gre', 'udp', 'udp-contrail'], label: 21, AS path: None

```

* List routes from SDN gateway (192.169.0.204) during last 1 hour

```
root@cont201:~# ist ctr route -t bgp.l3vpn.0 -s 192.168.0.204

bgp.l3vpn.0: 18 destinations, 28 routes (20 primary, 8 secondary, 0 infeasible)

13979:33001:33.100.100.1/32, age: 1 day 12:35:30.757845, last_modified: 2016-Jul-21 03:06:59.338383
    [BGP|192.168.0.204] age: 1 day 12:35:30.764064, localpref: 100, nh: 192.168.0.204, encap: [], label: 39, AS path: None

13979:33001:200.200.200.0/24, age: 0:31:41.735295, last_modified: 2016-Jul-22 15:10:48.360933
    [BGP|192.168.0.204] age: 0:31:41.742705, localpref: 100, nh: 192.168.0.204, encap: [], label: 39, AS path: None

root@cont201:~# ist ctr route -t bgp.l3vpn.0 -s 192.168.0.204 -l 1h

bgp.l3vpn.0: 18 destinations, 28 routes (20 primary, 8 secondary, 0 infeasible)

13979:33001:200.200.200.0/24, age: 0:31:45.741034, last_modified: 2016-Jul-22 15:10:48.360933
    [BGP|192.168.0.204] age: 0:31:45.744422, localpref: 100, nh: 192.168.0.204, encap: [], label: 39, AS path: None
```
