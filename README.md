# contrail-introspect-cli

## SSL Support
This is a very slightly modified fork of https://github.com/vcheny/contrail-introspect-cli
The modifications are to add support for SSL enabled introspect endpoints.
When SSL is enabled we need to use SSL/TLS Client Authentication.  The modifications allow passing of client side cert/key pair and a CA.
```set_ssl_envs``` contains example environment variable settings.
Alternatively use ```--key_file, --ca_file & --cert_file``` to pass as CLI arguments.
see ```ist.py --help``` for more details.

The rest of the README is verbatim from https://github.com/vcheny/contrail-introspect-cli

## Introduction
This script provides a Contrail CLI command mainly for troublelshooting prupose. It retrieves XML output from introspect services provided by Contrail main components e.g. control, config and comptue(vrouter) nodes and makes them CLI friendly.

Contrail 2.22+ is supported.

Note: Entire scripts is kept in one single file intentionally for easy use.

## Dependencies
* lxml
* prettytable
* requests

## Usage

Use ```-h``` to list possible command options

```
root@comp45:~# ist -h
usage: ist [-h] [--version] [--debug] [--host HOST] [--port PORT]
           [--proxy PROXY] [--token TOKEN]
           {alarm_gen,analytics,cfg_api,cfg_disc,cfg_schema,cfg_svcmon,collector,ctr,dm,dns,nodemgr_analytics,nodemgr_cfg,nodemgr_ctr,nodemgr_db,nodemgr_vr,qe,vr}
           ...

A script to make Contrail Introspect output CLI friendly.

positional arguments:
  {alarm_gen,analytics,cfg_api,cfg_disc,cfg_schema,cfg_svcmon,collector,ctr,dm,dns,nodemgr_analytics,nodemgr_cfg,nodemgr_ctr,nodemgr_db,nodemgr_vr,qe,vr}
    alarm_gen           contrail-alarm-gen
    analytics           contrail-analytics-api
    cfg_api             contrail-api
    cfg_disc            contrail-discovery
    cfg_schema          contrail-schema
    cfg_svcmon          contrail-svc-monitor
    collector           contrail-collector
    ctr                 contrail-control
    dm                  contrail-device-manager
    dns                 contrail-dns
    nodemgr_analytics   contrail-analytics-nodemgr
    nodemgr_cfg         contrail-config-nodemgr
    nodemgr_ctr         contrail-control-nodemgr
    nodemgr_db          contrail-database-nodemgr
    nodemgr_vr          contrail-vrouter-nodemgr
    qe                  contrail-query-engine
    vr                  contrail-vrouter-agent

optional arguments:
  -h, --help            show this help message and exit
  --version             Script version
  --debug               Verbose mode
  --host HOST           Introspect host address. Default: localhost
  --port PORT           Introspect port number
  --proxy PROXY         Introspect proxy URL
  --token TOKEN         Token for introspect proxy requests

root@comp45:~# ist vr -h
usage: ist vr [-h]
              {status,cpu,trace,uve,intf,vn,vrf,route,sg,acl,hc,ifmap,baas,xmpp,xmpp-dns,stats,service,si,nh,vm,mpls,vrfassign,linklocal,vxlan,mirror}
              ...

positional arguments:
  {status,cpu,trace,uve,intf,vn,vrf,route,sg,acl,hc,ifmap,baas,xmpp,xmpp-dns,stats,service,si,nh,vm,mpls,vrfassign,linklocal,vxlan,mirror}
    status              Node/component status
    cpu                 CPU load info
    trace               Sandesh trace buffer
    uve                 Sandesh UVE cache
    intf                Show vRouter interfaces
    vn                  Show Virtual Network
    vrf                 Show VRF
    route               Show routes
    sg                  Show Security Groups
    acl                 Show ACL info
    hc                  Health Check info
    ifmap               IFMAP info
    baas                Bgp As A Service info
    xmpp                Show Agent XMPP connections (route&config) status
    xmpp-dns            Show Agent XMPP connections (dns) status
    stats               Show Agent stats
    service             Service related info
    si                  Service instance info
    nh                  NextHop info
    vm                  VM info
    mpls                MPLS info
    vrfassign           VrfAssign info
    linklocal           LinkLocal service info
    vxlan               vxlan info
    mirror              mirror info

optional arguments:
  -h, --help            show this help message and exit

root@comp45:~# ist vr intf -h
usage: ist vr intf [-h] [-f {table,text}] [-c [COLUMNS [COLUMNS ...]]]
                   [--max_width MAX_WIDTH] [-u UUID] [-v VN] [-n NAME]
                   [-m MAC] [-i IPV4]
                   [search]

positional arguments:
  search                Search string

optional arguments:
  -h, --help            show this help message and exit
  -f {table,text}, --format {table,text}
                        Output format.
  -c [COLUMNS [COLUMNS ...]], --columns [COLUMNS [COLUMNS ...]]
                        Column(s) to include
  --max_width MAX_WIDTH
                        Max width per column
  -u UUID, --uuid UUID  Interface uuid
  -v VN, --vn VN        Virutal network
  -n NAME, --name NAME  Interface name
  -m MAC, --mac MAC     VM mac address
  -i IPV4, --ipv4 IPV4  VM IP address
```

## Examples

### How to run
* from local
```
root@cont101:~# ist ctr status
module_id: contrail-control
state: Functional
description
+-----------+-------------+-----------------------+--------+--------------------------------------+
| type      | name        | server_addrs          | status | description                          |
+-----------+-------------+-----------------------+--------+--------------------------------------+
| IFMap     | IFMapServer |   172.18.101.103:8443 | Up     | Connection with IFMap Server (irond) |
| Collector | n/a         |   172.18.101.101:8086 | Up     | Established                          |
| Discovery | Collector   |   172.18.101.100:5998 | Up     | SubscribeResponse                    |
| Discovery | IfmapServer |   172.18.101.100:5998 | Up     | SubscribeResponse                    |
| Discovery | xmpp-server |   172.18.101.100:5998 | Up     | Publish Response - HeartBeat         |
+-----------+-------------+-----------------------+--------+--------------------------------------+
```
* from remote
```
[cheny-mbp:~]$ ist --host cont101 ctr status
Introspect Host: cont101
module_id: contrail-control
state: Functional
description
+-----------+-------------+-----------------------+--------+--------------------------------------+
| type      | name        | server_addrs          | status | description                          |
+-----------+-------------+-----------------------+--------+--------------------------------------+
| IFMap     | IFMapServer |   172.18.101.103:8443 | Up     | Connection with IFMap Server (irond) |
| Collector | n/a         |   172.18.101.101:8086 | Up     | Established                          |
| Discovery | Collector   |   172.18.101.100:5998 | Up     | SubscribeResponse                    |
| Discovery | IfmapServer |   172.18.101.100:5998 | Up     | SubscribeResponse                    |
| Discovery | xmpp-server |   172.18.101.100:5998 | Up     | Publish Response - HeartBeat         |
+-----------+-------------+-----------------------+--------+--------------------------------------+
```
* from remote using [introspect proxy](https://github.com/Juniper/contrail-web-controller/blob/master/specs/introspect_proxy_without_login.md)
```
[cacdtl01ps3910:~]$ source openrc
[cacdtl01ps3910:~]$ export token=$(openstack token issue -f value -c id)
[cacdtl01ps3910:~]$ ist --proxy https://contrail-webui:8143 --host 172.29.24.88 ctr status
Introspect Host: 172.29.24.88
module_id: contrail-control
state: Functional
description
+-----------+-------------+----------------------+--------+--------------------------------------+
| type      | name        | server_addrs         | status | description                          |
+-----------+-------------+----------------------+--------+--------------------------------------+
| IFMap     | IFMapServer |   172.29.24.100:8443 | Up     | Connection with IFMap Server (irond) |
| Collector | n/a         |   172.29.24.82:8086  | Up     | Established                          |
| Discovery | Collector   |   172.29.24.77:5998  | Up     | SubscribeResponse                    |
| Discovery | IfmapServer |   172.29.24.77:5998  | Up     | SubscribeResponse                    |
| Discovery | xmpp-server |   172.29.24.77:5998  | Up     | Publish Response - HeartBeat         |
+-----------+-------------+----------------------+--------+--------------------------------------+
```

### vRouter commands

* Interface related
```
root@comp155:~# ist vr intf
+-------+----------------+--------+-------------------+------------+---------------+---------+----------------------------+
| index | name           | active | mac_addr          | ip_addr    | mdata_ip_addr | vm_name | vn_name                    |
+-------+----------------+--------+-------------------+------------+---------------+---------+----------------------------+
| 0     | eth1           | Active | n/a               | n/a        | n/a           | n/a     | n/a                        |
| 4     | tap5a233e07-94 | Active | 02:5a:23:3e:07:94 | 20.20.20.3 | 169.254.0.4   | vm_x    | default-domain:admin:vn_xy |
| 5     | tap7268190b-3f | Active | 02:72:68:19:0b:3f | 10.10.10.3 | 169.254.0.5   | vm_c    | default-domain:admin:vn_c  |
| 3     | tap844fc340-2b | Active | 02:84:4f:c3:40:2b | 1.2.3.3    | 169.254.0.3   | vm1     | default-domain:admin:vn1   |
| 1     | vhost0         | Active | n/a               | n/a        | n/a           | n/a     | n/a                        |
| 2     | pkt0           | Active | n/a               | n/a        | n/a           | n/a     | n/a                        |
+-------+----------------+--------+-------------------+------------+---------------+---------+----------------------------+

root@comp155:~# ist vr intf -h
usage: ist vr intf [-h] [-f {table,text}] [-c [COLUMNS [COLUMNS ...]]]
                   [--max_width MAX_WIDTH] [-u UUID] [-v VN] [-n NAME]
                   [-m MAC] [-i IPV4]
                   [search]

positional arguments:
  search                Search string

optional arguments:
  -h, --help            show this help message and exit
  -f {table,text}, --format {table,text}
                        Output format.
  -c [COLUMNS [COLUMNS ...]], --columns [COLUMNS [COLUMNS ...]]
                        Column(s) to include
  --max_width MAX_WIDTH
                        Max width per column
  -u UUID, --uuid UUID  Interface uuid
  -v VN, --vn VN        Virutal network
  -n NAME, --name NAME  Interface name
  -m MAC, --mac MAC     VM mac address
  -i IPV4, --ipv4 IPV4  VM IP address

root@comp155:~# ist vr intf -v default-domain:admin:vn1 -f text
ItfSandeshData
  index: 3
  name: tap844fc340-2b
  uuid: 844fc340-2b68-4866-87aa-9aee3d45f2fd
  vrf_name: default-domain:admin:vn1:vn1
  active: Active
  ipv4_active: Active
  l2_active: L2 Active
  ip6_active: Ipv6 Inactive < no-ipv6-addr  >
  health_check_active: Active
  dhcp_service: Enable
  dns_service: Enable
  type: vport
  label: 17
  l2_label: 18
  vxlan_id: 4
  vn_name: default-domain:admin:vn1
  vm_uuid: 00ff4531-41ca-485d-8584-f0218d5f930c
  vm_name: vm1
  ip_addr: 1.2.3.3
  mac_addr: 02:84:4f:c3:40:2b
  policy: Enable
  fip_list
      FloatingIpSandeshList
        ip_addr: 10.85.190.131
        vrf_name: default-domain:admin:public:public
        installed: Y
        fixed_ip: 1.2.3.3
  mdata_ip_addr: 169.254.0.3
  service_vlan_list
  os_ifindex: 11
  fabric_port: NotFabricPort
  alloc_linklocal_ip: LL-Enable
  analyzer_name
  config_name: default-domain:admin:844fc340-2b68-4866-87aa-9aee3d45f2fd
  sg_uuid_list
      VmIntfSgUuid
        sg_uuid: 80e317f8-39f1-4825-a432-fb440184cf4b
  static_route_list
  vm_project_uuid: f5d82829-4cee-4498-9064-9a8c50643c2f
  admin_state: Enabled
  flow_key_idx: 20
  allowed_address_pair_list
  ip6_addr: ::
  local_preference: 0
  tx_vlan_id: -1
  rx_vlan_id: -1
  parent_interface
  subnet: --NA--
  sub_type: Tap
  vrf_assign_acl_uuid: --NA--
  vmi_type: Virtual Machine
  transport: Ethernet
  logical_interface_uuid: 00000000-0000-0000-0000-000000000000
  flood_unknown_unicast: false
  physical_device
  physical_interface
  fixed_ip4_list
      1.2.3.3
  fixed_ip6_list
  fat_flow_list
  metadata_ip_active: Active
  service_health_check_ip: 0.0.0.0
  alias_ip_list
  drop_new_flows: false

root@comp155:~# ist vr intf -v default-domain:admin:vn1 -c uuid name active policy flood_unknown_unicast
+--------------------------------------+----------------+--------+--------+-----------------------+
| uuid                                 | name           | active | policy | flood_unknown_unicast |
+--------------------------------------+----------------+--------+--------+-----------------------+
| 844fc340-2b68-4866-87aa-9aee3d45f2fd | tap844fc340-2b | Active | Enable | false                 |
+--------------------------------------+----------------+--------+--------+-----------------------+
```

* vrf related

```
root@comp155:~# ist vr vrf -h
usage: ist vr vrf [-h] [-f {table,text}] [-c [COLUMNS [COLUMNS ...]]]
                  [--max_width MAX_WIDTH]
                  [name]

positional arguments:
  name                  VRF name

optional arguments:
  -h, --help            show this help message and exit
  -f {table,text}, --format {table,text}
                        Output format.
  -c [COLUMNS [COLUMNS ...]], --columns [COLUMNS [COLUMNS ...]]
                        Column(s) to include
  --max_width MAX_WIDTH
                        Max width per column
root@comp155:~# ist vr vrf
+--------------------------------------+---------+---------+---------+-----------+----------+-----------------------------+
| name                                 | ucindex | mcindex | brindex | evpnindex | vxlan_id | vn                          |
+--------------------------------------+---------+---------+---------+-----------+----------+-----------------------------+
| default-domain:admin:public:public   | 2       | 2       | 2       | 2         | 5        | default-domain:admin:public |
| default-domain:admin:vn1:vn1         | 1       | 1       | 1       | 1         | 4        | default-domain:admin:vn1    |
| default-domain:admin:vn_c:vn_c       | 4       | 4       | 4       | 4         | 9        | default-domain:admin:vn_c   |
| default-domain:admin:vn_xy:vn_xy     | 3       | 3       | 3       | 3         | 7        | default-domain:admin:vn_xy  |
| default-domain:default-project:ip-   | 0       | 0       | 0       | 0         | 0        | N/A                         |
| fabric:__default__                   |         |         |         |           |          |                             |
+--------------------------------------+---------+---------+---------+-----------+----------+-----------------------------+
```

* route related
```
root@comp155:~# ist vr route -h
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

root@comp155:~# ist vr route -v 2
  if nh.find("policy"):
0.0.0.0/0
    [10.173.150.152] pref:100
     to f0:1c:2d:41:90:0 via MPLSoGRE dip:192.168.0.204 sip:10.173.150.155 label:27, nh_index:29 , nh_type:tunnel, nh_policy:, active_label:27, vxlan_id:0
    [10.173.150.153] pref:100
     to f0:1c:2d:41:90:0 via MPLSoGRE dip:192.168.0.204 sip:10.173.150.155 label:27, nh_index:29 , nh_type:tunnel, nh_policy:, active_label:27, vxlan_id:0
10.85.190.128/29
    [Local] pref:100
     nh_index:1 , nh_type:discard, nh_policy:, active_label:-1, vxlan_id:0
10.85.190.129/32
    [Local] pref:100
     to 0:0:0:0:0:1 via pkt0, assigned_label:-1, nh_index:8 , nh_type:interface, nh_policy:, active_label:-1, vxlan_id:0
10.85.190.130/32
    [Local] pref:100
     to 0:0:0:0:0:1 via pkt0, assigned_label:-1, nh_index:8 , nh_type:interface, nh_policy:, active_label:-1, vxlan_id:0
10.85.190.131/32
    [10.173.150.152] pref:200
     to 2:84:4f:c3:40:2b via tap844fc340-2b, assigned_label:17, nh_index:20 , nh_type:interface, nh_policy:, active_label:17, vxlan_id:0
    [10.173.150.153] pref:200
     to 2:84:4f:c3:40:2b via tap844fc340-2b, assigned_label:17, nh_index:20 , nh_type:interface, nh_policy:, active_label:17, vxlan_id:0
    [LocalVmPort] pref:200
     to 2:84:4f:c3:40:2b via tap844fc340-2b, assigned_label:17, nh_index:20 , nh_type:interface, nh_policy:, active_label:17, vxlan_id:0
    [INET-EVPN] pref:100
     nh_index:0 , nh_type:None, nh_policy:, active_label:-1, vxlan_id:0
169.254.169.254/32
    [LinkLocal] pref:100
     via vhost0, nh_index:6 , nh_type:receive, nh_policy:, active_label:-1, vxlan_id:0

root@comp155:~# ist vr route -v 2 -p 10.85.190.131/32
10.85.190.131/32
 [10.173.150.152] pref:200
  to 2:84:4f:c3:40:2b via tap844fc340-2b, assigned_label:17, nh_index:20 , nh_type:interface, nh_policy:enabled, active_label:17, vxlan_id:0
 [10.173.150.153] pref:200
  to 2:84:4f:c3:40:2b via tap844fc340-2b, assigned_label:17, nh_index:20 , nh_type:interface, nh_policy:enabled, active_label:17, vxlan_id:0
 [LocalVmPort] pref:200
  to 2:84:4f:c3:40:2b via tap844fc340-2b, assigned_label:17, nh_index:20 , nh_type:interface, nh_policy:enabled, active_label:17, vxlan_id:0
 [INET-EVPN] pref:100
  nh_index:0 , nh_type:None, nh_policy:, active_label:-1, vxlan_id:0


  root@comp155:~# ist vr route -v 2 -p 10.85.190.131/32 -r
  RouteUcSandeshData
    src_ip: 10.85.190.131
    src_plen: 32
    src_vrf: default-domain:admin:public:public
    path_list
        PathSandeshData
          nh
            NhSandeshData
              type: interface
              ref_count: 12
              valid: true
              policy: enabled
              itf: tap844fc340-2b
              mac: 2:84:4f:c3:40:2b
              mcast: disabled
              nh_index: 20
              vxlan_flag: false
          label: 17
          vxlan_id: 0
          peer: 10.173.150.152
          dest_vn_list
              default-domain:admin:public
          unresolved: false
          sg_list
              8000001
          supported_tunnel_type: MPLSoGRE MPLSoUDP
          active_tunnel_type: MPLSoUDP
          stale: false
          path_preference_data
            PathPreferenceSandeshData
              sequence: 0
              preference: 200
              ecmp: true
          active_label: 17
          ecmp_hashing_fields: l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,
          communities
        PathSandeshData
          nh
            NhSandeshData
              type: interface
              ref_count: 12
              valid: true
              policy: enabled
              itf: tap844fc340-2b
              mac: 2:84:4f:c3:40:2b
              mcast: disabled
              nh_index: 20
              vxlan_flag: false
          label: 17
          vxlan_id: 0
          peer: 10.173.150.153
          dest_vn_list
              default-domain:admin:public
          unresolved: false
          sg_list
              8000001
          supported_tunnel_type: MPLSoGRE MPLSoUDP
          active_tunnel_type: MPLSoUDP
          stale: false
          path_preference_data
            PathPreferenceSandeshData
              sequence: 0
              preference: 200
              ecmp: true
          active_label: 17
          ecmp_hashing_fields: l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,
          communities
        PathSandeshData
          nh
            NhSandeshData
              type: interface
              ref_count: 12
              valid: true
              policy: enabled
              itf: tap844fc340-2b
              mac: 2:84:4f:c3:40:2b
              mcast: disabled
              nh_index: 20
              vxlan_flag: false
          label: 17
          vxlan_id: 0
          peer: LocalVmPort
          dest_vn_list
              default-domain:admin:public
          unresolved: false
          sg_list
              8000001
          supported_tunnel_type: MPLSoGRE MPLSoUDP
          active_tunnel_type: MPLSoUDP
          stale: false
          path_preference_data
            PathPreferenceSandeshData
              sequence: 0
              preference: 200
              ecmp: true
              wait_for_traffic: false
              dependent_ip: default-domain:admin:vn1:vn1 : 1.2.3.3
          active_label: 17
          ecmp_hashing_fields: l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,
          communities
        PathSandeshData
          nh
            NhSandeshData
              type
              ref_count: 0
              nh_index: 0
          label: -1
          vxlan_id: 0
          peer: INET-EVPN
          dest_vn_list
          unresolved: false
          gw_ip: 10.85.190.128
          vrf
          sg_list
          supported_tunnel_type: MPLSoGRE MPLSoUDP VxLAN
          active_tunnel_type: MPLSoUDP
          stale: false
          path_preference_data
            PathPreferenceSandeshData
              sequence: 0
              preference: 100
              ecmp: false
              wait_for_traffic: true
          active_label: -1
          ecmp_hashing_fields: l3-source-address,l3-destination-address,l4-protocol,l4-source-port,l4-destination-port,
          communities
    ipam_subnet_route: false
    proxy_arp: false
    multicast: false

root@comp155:~# ist vr route -v 2 10.85.190.131
0.0.0.0/0
    [10.173.150.152] pref:100
     to f0:1c:2d:41:90:0 via MPLSoGRE dip:192.168.0.204 sip:10.173.150.155 label:27, nh_index:29 , nh_type:tunnel, nh_policy:disabled, active_label:27, vxlan_id:0
    [10.173.150.153] pref:100
     to f0:1c:2d:41:90:0 via MPLSoGRE dip:192.168.0.204 sip:10.173.150.155 label:27, nh_index:29 , nh_type:tunnel, nh_policy:disabled, active_label:27, vxlan_id:0
10.85.190.128/29
    [Local] pref:100
     nh_index:1 , nh_type:discard, nh_policy:disabled, active_label:-1, vxlan_id:0
10.85.190.131/32
    [10.173.150.152] pref:200
     to 2:84:4f:c3:40:2b via tap844fc340-2b, assigned_label:17, nh_index:20 , nh_type:interface, nh_policy:enabled, active_label:17, vxlan_id:0
    [10.173.150.153] pref:200
     to 2:84:4f:c3:40:2b via tap844fc340-2b, assigned_label:17, nh_index:20 , nh_type:interface, nh_policy:enabled, active_label:17, vxlan_id:0
    [LocalVmPort] pref:200
     to 2:84:4f:c3:40:2b via tap844fc340-2b, assigned_label:17, nh_index:20 , nh_type:interface, nh_policy:enabled, active_label:17, vxlan_id:0
    [INET-EVPN] pref:100
     nh_index:0 , nh_type:None, nh_policy:, active_label:-1, vxlan_id:0
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
