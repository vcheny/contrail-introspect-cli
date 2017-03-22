#! /usr/bin/env python

# Author        : Yan Chen <vcheny@outlook.com>
# Platform      : Contrail 2.22+
version = '1.0.4'
# Date          : 2017-03-21

# This script provides a Contrail CLI command mainly for troublelshooting prupose.
# It retrieves XML output from introspect services provided by Contrail main components
# e.g. control, config and comptue(vrouter) nodes and makes them CLI friendly.

import sys, os
import argparse
import socket, struct
from urllib2 import urlopen, URLError, HTTPError
from datetime import datetime
from lxml import etree
from prettytable import PrettyTable

debug = False

class Introspec:

    output_etree = []
    tbl_col_max_width = 60

    def __init__ (self, host, port, max_width):
        self.host_url = "http://" + host + ":" + str(port) + "/"
        self.tbl_col_max_width = int(max_width)

    # get instrosepc output
    def get (self, path):

        self.output_etree = []

        while True:
            url = self.host_url + path.replace(' ', '%20')
            if debug: print "DEBUG: retriving url " + url
            try:
              response = urlopen(url)
            except HTTPError as e:
                print 'The server couldn\'t fulfill the request.'
                print 'URL: ' + url
                print 'Error code: ', e.code
                sys.exit(1)
            except URLError as e:
                print 'Failed to reach destination'
                print 'URL: ' + url
                print 'Reason: ', e.reason
                sys.exit(1)
            else:
                ISOutput = response.read()
                response.close()

            self.output_etree.append(etree.fromstring(ISOutput))

            if 'Snh_PageReq?x=' in path:
                break

            # some routes output from vrouter may have pagination
            pagination = self.output_etree[-1].xpath("//Pagination/req/PageReqData")
            if len(pagination):
                if (pagination[0].find("next_page").text is not None):
                    all = pagination[0].find("all").text
                    if(all is not None):
                        path = 'Snh_PageReq?x=' + all
                        self.output_etree = []
                        continue
                    else:
                        print "Warning: all page in pagination is empty!"
                        break
                else:
                    break

            next_batch = self.output_etree[-1].xpath("//next_batch")

            if not len(next_batch):
                break

            if (next_batch[0].text and next_batch[0].attrib['link']):
                path = 'Snh_' + next_batch[0].attrib['link'] + '?x=' + next_batch[0].text
            else:
                break
        if debug: print "instrosepct get completes\n"

    # print the introspect output in a table. args lists interested fields.
    def printTbl(self, xpathExpr, *args):

        #fields = args if len(args) else [ e.tag for e in self.output_etree[0].xpath(xpathExpr)[0]]

        if len(args):
            fields = args
        else:
            elist = self.output_etree[0].xpath(xpathExpr)
            if len(elist):
                fields = [ e.tag for e in elist[0]]
            else:
                return

        tbl = PrettyTable(fields)
        tbl.align = 'l'
        tbl.max_width = self.tbl_col_max_width

        # start building the table
        for tree in self.output_etree:
            for item in tree.xpath(xpathExpr):
                row = []
                for field in fields:
                    f = item.find(field)
                    if f is not None:
                        if f.text:
                            row.append(f.text)
                        elif list(f):
                            for e in f:
                                row.append(self.elementToStr('', e).rstrip())
                        else:
                            row.append("n/a")
                    else:
                        row.append("non-exist")
                tbl.add_row(row)

        print tbl

    # print the introspect output in human readable text
    def printText(self, xpathExpr):
        for tree in self.output_etree:
            for element in tree.xpath(xpathExpr):
                print self.elementToStr('', element).rstrip()

    # convernt etreenode sub-tree into a string
    def elementToStr(self, indent, etreenode):
        elementStr=''

        if etreenode.tag == 'more':   #skip more element
            return elementStr

        if etreenode.text and etreenode.tag == 'element':
            return indent + etreenode.text + "\n"
        elif etreenode.text:
            return indent + etreenode.tag + ': ' + etreenode.text.replace('\n', '\n' + indent + (len(etreenode.tag)+2)*' ') + "\n"
        elif etreenode.tag != 'list':
            elementStr += indent + etreenode.tag + "\n"

        if 'type' in etreenode.attrib:
            if etreenode.attrib['type'] == 'list' and etreenode[0].attrib['size'] == '0':
                return elementStr

        for element in etreenode:
            elementStr += self.elementToStr(indent + '  ', element)

        return elementStr

    def showRoute_VR(self, xpathExpr, family, address, mode):

        indent = ' ' * 4

        ADDR_INET4 = 4
        ADDR_INET6 = 6
        ADDR_NONE = 0

        addr_type = ADDR_NONE
        if is_ipv4(address):
            addr_type = ADDR_INET4
        elif is_ipv6(address):
            addr_type = ADDR_INET6

        for tree in self.output_etree:
            for route in tree.xpath(xpathExpr):
                if 'inet' in family:
                    prefix = route.find("src_ip").text + '/' + route.find("src_plen").text
                else:
                    prefix = route.find("mac").text

                if family == 'inet' and addr_type == ADDR_INET4:
                    if not addressInNetwork(address, prefix):
                        if debug: print "DEBUG: skipping " + prefix
                        continue
                elif family == 'inet6' and addr_type == ADDR_INET6:
                    if not addressInNetwork6(address, prefix):
                        if debug: print "DEBUG: skipping " + prefix
                        continue

                if mode == "raw":
                    print self.elementToStr('', route).rstrip()
                    continue

                output = prefix + "\n"

                for path in route.xpath(".//PathSandeshData"):
                    nh = path.xpath("nh/NhSandeshData")[0]

                    peer = path.find("peer").text
                    pref = path.xpath("path_preference_data/PathPreferenceSandeshData/preference")[0].text

                    path_info = "%s[%s] pref:%s\n" % (indent, peer, pref)

                    path_info += indent + ' '
                    nh_type = nh.find('type').text
                    if nh_type == "interface":
                        mac = nh.find('mac').text
                        itf = nh.find("itf").text
                        label = path.find("label").text
                        path_info += "to %s via %s, assigned_label:%s, " % (mac, itf, label)

                    elif nh_type == "tunnel":
                        tunnel_type = nh.find("tunnel_type").text
                        dip = nh.find("dip").text
                        sip = nh.find("sip").text
                        label = path.find("label").text
                        if nh.find('mac') is not None:
                            mac = nh.find('mac').text
                            path_info += "to %s via %s dip:%s sip:%s label:%s, " % (mac, tunnel_type, dip, sip, label)
                        else:
                            path_info += "via %s dip:%s sip:%s label:%s, " % (tunnel_type, dip, sip, label)

                    elif nh_type == "receive":
                        itf = nh.find("itf").text
                        path_info += "via %s, " % (itf)

                    elif nh_type == "arp":
                        mac = nh.find('mac').text
                        itf = nh.find("itf").text
                        path_info += "via %s, " % (mac)

                    elif 'Composite' in str(nh_type):
                        comp_nh = str(nh.xpath(".//itf/text()"))
                        path_info += "via %s, " % (comp_nh)

                    elif 'vlan' in str(nh_type):
                        mac = nh.find('mac').text
                        itf = nh.find("itf").text
                        path_info += "to %s via %s, " % (mac, itf)

                    nh_index = nh.find("nh_index").text
                    policy = nh.find("policy").text if nh.find("policy") is not None else ''
                    active_label = path.find("active_label").text
                    vxlan_id = path.find("vxlan_id").text
                    path_info += "nh_index:%s , nh_type:%s, nh_policy:%s, active_label:%s, vxlan_id:%s" %\
                                 (nh_index, nh_type, policy, active_label, vxlan_id)

                    if mode == "detail":
                        path_info += "\n"
                        path_info += indent + ' dest_vn:' + str(path.xpath("dest_vn_list/list/element/text()"))
                        path_info += ', sg:' + str(path.xpath("sg_list/list/element/text()"))
                        path_info += ', communities:' +  str(path.xpath("communities/list/element/text()"))
                    output += path_info + "\n"

                print output.rstrip()

    def pathToStr(self, indent, path, mode):

        path_info = ''
        if mode == 'raw':
            for item in path:
                 path_info += self.elementToStr(indent, item)
            return path_info.rstrip()

        now = datetime.utcnow()

        path_modified = path.find("last_modified").text
        t1 = datetime.strptime(path_modified, '%Y-%b-%d %H:%M:%S.%f')
        path_age = str(now - t1).replace(',', '')
        path_proto = path.find("protocol").text
        path_source = path.find("source").text
        path_lp = path.find("local_preference").text
        path_as = path.find("as_path").text
        path_nh = path.find("next_hop").text
        path_label = path.find("label").text
        path_vn = path.find("origin_vn").text
        path_pri_tbl = path.find("primary_table").text
        path_vn_path = str(path.xpath("origin_vn_path/list/element/text()"))
        path_encap = str(path.xpath("tunnel_encap/list/element/text()"))
        path_comm = str(path.xpath("communities/list/element/text()"))
        path_sqn = path.find("sequence_no").text
        path_flags = path.find("flags").text

        path_info = "%s[%s|%s] age: %s, localpref: %s, nh: %s, encap: %s, label: %s, AS path: %s" % \
                    (indent, path_proto, path_source, path_age, path_lp, path_nh, path_encap, path_label, path_as)

        if mode == 'detail':
            path_info += "\n%sprimary table: %s, origin vn: %s, origin_vn_path: %s" % (2*indent, path_pri_tbl, path_vn, path_vn_path)
            path_info += "\n%scommunities: %s" % (2*indent, path_comm)
            path_info += "\n%slast modified: %s" % (2*indent, path_modified)

        return path_info

    def routeToStr(self, indent, route, mode):

        route_info = ''
        now = datetime.utcnow()

        prefix = route.find("prefix").text
        prefix_modified = route.find("last_modified").text
        t1 = datetime.strptime(prefix_modified, '%Y-%b-%d %H:%M:%S.%f')
        prefix_age = str(now - t1).replace(',', '')

        route_info += "%s%s, age: %s, last_modified: %s" % (indent, prefix, prefix_age, prefix_modified)

        for path in route.xpath('.//ShowRoutePath'):
            route_info += "\n" + self.pathToStr(indent*2, path, mode)

        return route_info.rstrip()

    def showRoute_CTR(self, address, protocol, tbl, source, family, last, mode):

        ADDR_INET4 = 4
        ADDR_INET6 = 6
        ADDR_NONE = 0

        indent = ' ' * 4

        now = datetime.utcnow()

        ## building xpath to filter tables based on family...
        xpath_tbl = '//ShowRouteTable'
        addr_type = ADDR_NONE
        if is_ipv4(address):
            addr_type = ADDR_INET4
            if ((not tbl or family == "inet") or
                    (tbl and (tbl[-6:] == 'inet.0' or tbl[-7:] == 'l3vpn.0'))):
                xpath_tbl += '[re:test(routing_table_name/text(), "(inet|l3vpn).0$")]'
            elif not (family == "all"):
                xpath_tbl += '[re:test(routing_table_name/text(), "' + family + '.0$")]'
        elif is_ipv6(address):
            addr_type = ADDR_INET6
            if ((not tbl or family == "inet6") or
                    (tbl and (tbl[-7:] == 'inet6.0'))):
                xpath_tbl += '[re:test(routing_table_name/text(), "inet6.0$")]'
            elif not (family == "all"):
                xpath_tbl += '[re:test(routing_table_name/text(), "' + family + '.0$")]'
        elif not(family == "all"):
            if (family == "inet"):
                xpath_tbl += '[re:test(routing_table_name/text(), "(inet|l3vpn).0$")]'
            else:
                xpath_tbl += '[re:test(routing_table_name/text(), "' + family + '.0$")]'

        # building xpath to fitler routes based on protocol, source etc.
        xpath_pth = './/ShowRoutePath'
        path_cond = []
        if not (protocol == "all"):
            path_cond.append("protocol='%s'" % (protocol))
        if not (source == "all"):
            path_cond.append("source='%s'" % (source))
        if (len(path_cond)):
            xpath_pth += '[' + ' and '.join(path_cond) + ']'

        printedTbl = {}

        for tree in self.output_etree:
            for table in tree.xpath(xpath_tbl, namespaces={'re':'http://exslt.org/regular-expressions'}):
                tbl_name = table.find('routing_table_name').text

                prefix_count = table.find('prefixes').text
                tot_path_count = table.find('paths').text
                pri_path_count = table.find('primary_paths').text
                sec_path_count = table.find('secondary_paths').text
                ifs_path_count = table.find('infeasible_paths').text

                if not(tbl_name in printedTbl):
                    print  "\n%s: %s destinations, %s routes (%s primary, %s secondary, %s infeasible)" \
                            % (tbl_name, prefix_count, tot_path_count, pri_path_count, sec_path_count, ifs_path_count)
                    printedTbl[tbl_name] = True

                # check if route lookup is needed based on address type and route table name
                lookup = ADDR_NONE
                if addr_type == ADDR_INET4 and (tbl_name[-6:] == 'inet.0' or tbl_name[-7:] == 'l3vpn.0'):
                    lookup = ADDR_INET4
                elif addr_type == ADDR_INET6 and (tbl_name[-7:] == 'inet6.0'):
                    lookup = ADDR_INET6

                # start processing each route
                for route in table.xpath(".//ShowRoute"):

                    paths = route.xpath(xpath_pth)
                    if not (len(paths)):
                        continue

                    prefix = route.find("prefix").text

                    # skip routes if not matched or covering the address
                    if address not in prefix:
                        if lookup == ADDR_INET4:
                            if not(addressInNetwork(address, prefix)):
                                continue
                        elif lookup == ADDR_INET6:
                            if tbl_name == 'bgp.l3vpn-inet6.0':
                                real_prefix = ':'.join(prefix.split(':')[2:])
                                if not(addressInNetwork6(address, real_prefix)):
                                    continue
                            elif not(addressInNetwork6(address, prefix)):
                                continue
                        else:
                            continue

                    prefix_modified = route.find("last_modified").text
                    t1 = datetime.strptime(prefix_modified, '%Y-%b-%d %H:%M:%S.%f')
                    prefix_age = str(now - t1).replace(',', '')

                    if (last and (now - t1).total_seconds() > last):
                        for path in paths:
                            path_modified = path.find("last_modified").text
                            t1 = datetime.strptime(path_modified, '%Y-%b-%d %H:%M:%S.%f')
                            path_age = str(now - t1).replace(',', '')
                            if not ((now - t1).total_seconds() > last) :
                                print "\n%s, age: %s, last_modified: %s" % (prefix, prefix_age, prefix_modified)
                                print self.pathToStr(indent, path, mode)
                    else:
                        print "\n%s, age: %s, last_modified: %s" % (prefix, prefix_age, prefix_modified)
                        for path in paths:
                            print self.pathToStr(indent, path, mode)

    def showSCRoute(self, xpathExpr):

        fields = ['src_virtual_network', 'dest_virtual_network', 'service_instance', 'state', 'connected_route', 'more_specifics', 'ext_connecting_rt']

        tbl = PrettyTable(fields)
        tbl.align = 'l'

        # start building the table
        for tree in self.output_etree:
            for sc in tree.xpath(xpathExpr):
                row = []
                for field in fields[0:4]:
                    f = sc.find(field)
                    if f is not None:
                        if f.text:
                            row.append(f.text)
                        elif list(f):
                            row.append(self.elementToStr('', f).rstrip())
                        else:
                            row.append("n/a")
                    else:
                        row.append("non-exist")

                service_chain_addr = sc.xpath('./connected_route/ConnectedRouteInfo/service_chain_addr')[0]
                row.append(self.elementToStr('', service_chain_addr).rstrip())

                specifics = ''
                PrefixToRouteListInfo = sc.xpath('./more_specifics/list/PrefixToRouteListInfo')
                for p in PrefixToRouteListInfo:
                    specifics += "prefix: %s, aggregate: %s\n" % (p.find('prefix').text, p.find('aggregate').text)
                row.append(specifics.rstrip())

                ext_rt = ''
                ext_rt_prefix_list = sc.xpath('./ext_connecting_rt_info_list//ext_rt_prefix')
                for p in ext_rt_prefix_list:
                    ext_rt += p.text + "\n"
                row.append(ext_rt.rstrip())

                tbl.add_row(row)

        print tbl

    def showSCRouteDetail(self, xpathExpr):

        indent = ' ' * 4

        fields = ['src_virtual_network', 'dest_virtual_network', 'service_instance', 'src_rt_instance', 'dest_rt_instance', 'state']
        for tree in self.output_etree:

            for sc in tree.xpath(xpathExpr):

                for field in fields:
                    print "%s: %s" % (field, sc.find(field).text)

                print "connectedRouteInfo:"
                print "%sservice_chain_addr: %s" % (indent, sc.xpath('./connected_route/ConnectedRouteInfo/service_chain_addr')[0].text)
                for route in sc.xpath('./connected_route//ShowRoute'):
                    print self.routeToStr(indent, route, 'detail')

                print "more_specifics:"
                specifics = ''
                PrefixToRouteListInfo = sc.xpath('./more_specifics/list/PrefixToRouteListInfo')
                for p in PrefixToRouteListInfo:
                    specifics += "%sprefix: %s, aggregate: %s\n" % (indent, p.find('prefix').text, p.find('aggregate').text)
                print specifics.rstrip()

                print "ext_connecting_rt_info_list:"
                for route in sc.xpath('.//ExtConnectRouteInfo/ext_rt_svc_rt/ShowRoute'):
                    print self.routeToStr(indent, route, 'detail')

                print "aggregate_enable:%s\n" % (sc.find("aggregate_enable").text)

class Contrail_CLI:

    def __init__(self, parser, host, port, max_width):

        parser.add_argument('--host', default=host, help="Introspect host(default='%(default)s')")
        parser.add_argument('--port', default=port, help="Introspect port(default='%(default)s')")
        self.subparser = parser.add_subparsers()

        parser_status = self.subparser.add_parser('status', help='show node/component status')
        parser_status.add_argument('-d', '--detail', action="store_true", help='Display detailed output')
        parser_status.set_defaults(func=self.SnhNodeStatus)

        parser_cpu = self.subparser.add_parser('cpu', help='Show CPU load info')
        parser_cpu.set_defaults(func=self.SnhCpuLoadInfo)

        parser_trace = self.subparser.add_parser('trace', help='Show Sandesh trace buffer')
        parser_trace.add_argument('name', nargs='?', default='list', help='Trace buffer name, default: list available buffer names')
        parser_trace.set_defaults(func=self.SnhTrace)

        parser_uve = self.subparser.add_parser('uve', help='Show Sandesh UVE cache')
        parser_uve.add_argument('name', nargs='?', default='list', help='UVE type name, default: list available type names')
        parser_uve.set_defaults(func=self.SnhUve)

        self.IST = Introspec(host, port, max_width)

    def SnhNodeStatus(self, args):
        self.IST.get('Snh_SandeshUVECacheReq?tname=NodeStatus')
        self.IST.printText('//ProcessStatus/module_id')
        self.IST.printText('//ProcessStatus/state')
        if args.detail:
            self.IST.printText('//ProcessStatus/description')
            print 'Connetion Info:'
            self.IST.printTbl('//ConnectionInfo')

    def SnhCpuLoadInfo(self, args):
        self.IST.get('Snh_CpuLoadInfoReq')
        self.IST.printText("//CpuLoadInfo/*")

    def SnhTrace(self, args):
        if args.name == "list":
            self.IST.get('Snh_SandeshTraceBufferListRequest')
            self.IST.printText('//trace_buf_name')
        else:
            self.IST.get('Snh_SandeshTraceRequest?x=' + str(args.name))
            self.IST.printText('//element')

    def SnhUve(self, args):
        if args.name == "list":
            self.IST.get('Snh_SandeshUVETypesReq')
            self.IST.printText('//type_name')
        else:
            self.IST.get('Snh_SandeshUVECacheReq?x=' + str(args.name))
            self.IST.printText('//*[@type="sandesh"]/data/*')

class Config_API_CLI(Contrail_CLI):

    def __init__(self, parser, host, port, max_width):

        IShost = 'localhost' if host is None else host
        ISport ='8084' if port is None else port

        Contrail_CLI.__init__(self, parser, IShost, ISport, max_width)

class Config_SCH_CLI(Contrail_CLI):

    def __init__(self, parser, host, port, max_width):

        IShost = 'localhost' if host is None else host
        ISport ='8087' if port is None else port

        Contrail_CLI.__init__(self, parser, IShost, ISport, max_width)

        self.parse_args()

    def parse_args(self):
        parser_vn = self.subparser.add_parser('vn', help='List Virtual Networks')
        parser_vn.add_argument('name', nargs='?', default='', help='Virtual Network name')
        parser_vn.set_defaults(func=self.SnhVnList)

        parser_ri = self.subparser.add_parser('ri', help='List Routing Instances')
        parser_ri.add_argument('name', nargs='?', default='', help='Routing Instance name')
        parser_ri.add_argument('-v', '--vn', default='', help='Virtual Network name')
        parser_ri.set_defaults(func=self.SnhRoutintInstanceList)

        parser_sc = self.subparser.add_parser('sc', help='List Service Chains')
        parser_sc.add_argument('name', nargs='?', default='', help='Service Chain name')
        parser_sc.set_defaults(func=self.SnhServiceChainList)

        parser_ob = self.subparser.add_parser('object', help='List Schema-transformer Ojbects (Only available in Contrail 3.0+')
        parser_ob.add_argument('name', nargs='?', default='', help='object_id or fq_name')
        parser_ob.add_argument('-t', '--type', default='', help='Object type')
        parser_ob.add_argument('-d', '--detail', action="store_true", help='Display detailed output')
        parser_ob.set_defaults(func=self.SnhStObjectReq)

    def SnhVnList(self, args):
        self.IST.get('Snh_VnList?vn_name=' + args.name)
        self.IST.printTbl("//VirtualNetwork", "name", "policies", "connections", "routing_instances")

    def SnhRoutintInstanceList(self, args):
        self.IST.get('Snh_RoutintInstanceList?vn_name=' + args.vn + '&ri_name=' + args.name)
        self.IST.printTbl("//RoutingInstance", "name", "connections")

    def SnhServiceChainList(self, args):
        self.IST.get('Snh_ServiceChainList?sc_name=' + args.name)
        self.IST.printTbl("//ServiceChain")

    def SnhStObjectReq(self, args):
        self.IST.get('Snh_StObjectReq?object_type=' + args.type + '&object_id_or_fq_name=' + args.name)
        if args.detail:
            self.IST.printText("//StObject")
        else:
            self.IST.printTbl("//StObject", 'object_type', 'object_uuid', 'object_fq_name')

class Config_SVC_CLI(Contrail_CLI):

    def __init__(self, parser, host, port, max_width):

        IShost = 'localhost' if host is None else host
        ISport ='8088' if port is None else port

        Contrail_CLI.__init__(self, parser, IShost, ISport, max_width)

        self.parse_args()

    def parse_args(self):
        parser_si = self.subparser.add_parser('si', help='List Service instances')
        parser_si.add_argument('name', nargs='?', default='', help='Service instance name')
        parser_si.add_argument('-r', '--raw', action="store_true", help='Display raw output in plain text')
        parser_si.set_defaults(func=self.SnhServiceInstanceList)

    def SnhServiceInstanceList(self, args):
        self.IST.get('Snh_ServiceInstanceList?si_name=' + args.name)
        if args.raw:
            self.IST.printText("//ServiceInstance")
        else:
            self.IST.printTbl("//ServiceInstance")

class Control_CLI(Contrail_CLI):

    def __init__(self, parser, host, port, max_width):

        IShost = 'localhost' if host is None else host
        ISport ='8083' if port is None else port

        Contrail_CLI.__init__(self, parser, IShost, ISport, max_width)
        self.parse_args()

    def parse_args(self):

        parser_nei = self.subparser.add_parser('nei', help='Show BGP/XMPPP neighbors')
        parser_nei.add_argument('search', nargs='?', default='', type=str, help='search string')
        parser_nei.add_argument('-t', '--type', choices=['BGP', 'XMPP'], default='', help='Neighbor types (BGP or XMPP)')
        parser_nei.set_defaults(func=self.SnhBgpNeighbor)

        parser_ri = self.subparser.add_parser('ri', help='Show routing instances')
        parser_ri.add_argument('search', nargs='?', default='', type=str,  help='Search string')
        parser_ri.add_argument('-d', '--detail', action="store_true", help='Display detailed output')
        parser_ri.set_defaults(func=self.SnhRoutingInstance)

        parser_routesummary = self.subparser.add_parser('routes', help='Show route summary')
        parser_routesummary.add_argument('search', nargs='?', default='', help='Only lists matched instances')
        parser_routesummary.add_argument('-f', '--family', choices=['inet', 'inet6', 'evpn', 'ermvpn', 'all'], default='inet', help="Route family(default='%(default)s')")
        parser_routesummary.set_defaults(func=self.SnhShowRouteSummary)

        parser_rtable = self.subparser.add_parser('rtable', help='Show route table names')
        parser_rtable.add_argument('search', nargs='?', default='', help='Only lists matched tables')
        parser_rtable.add_argument('-f', '--family', choices=['inet', 'inet6', 'evpn', 'ermvpn', 'all'], default='inet', help="Route family(default='%(default)s')")
        parser_rtable.set_defaults(func=self.SnhShowRTable)

        parser_route = self.subparser.add_parser('route', help='Show route')
        parser_route.add_argument('address', nargs='?', default='', help='Show routes for given address')
        parser_route.add_argument('-P', '--prefix', default='', help='Show routes exactally matching given prefix')
        parser_route.add_argument('-f', '--family', choices=['inet', 'inet6', 'evpn', 'ermvpn', 'rtarget', 'all'], default="all", help='Show routes for given family. default:all')
        parser_route.add_argument('-l', '--last', type=valid_period, help='Show routes modified during last time period (e.g. 10s, 5m, 2h, or 5d)')
        parser_route.add_argument('-d', '--detail', action="store_true", help='Display detailed output')
        parser_route.add_argument('-r', '--raw', action="store_true", help='Display raw output in plain text')
        parser_route.add_argument('-p', '--protocol', choices=['BGP', 'XMPP', 'local', 'ServiceChain', 'all'], default='all', help='Show routes learned from given protocol')
        parser_route.add_argument('-v', '--vrf', default='', help='Show routes in given routing instance')
        parser_route.add_argument('-s', '--source', default='all', help='Show routes learned from given source')
        parser_route.add_argument('-t', '--table', default='', help='Show routes in given table')
        parser_route.set_defaults(func=self.SnhShowRoute)



        ## XMPP
        parser_sub = self.subparser.add_parser('xmpp', help='Show XMPP info')
        parser_xmpp = parser_sub.add_subparsers()

        parser_xmpp_trace = parser_xmpp.add_parser('trace', help='XMPP message traces')
        parser_xmpp_trace.set_defaults(func=self.SnhXmppMsg)

        parser_xmpp_stats = parser_xmpp.add_parser('stats', help='XMPP server stats')
        parser_xmpp_stats.set_defaults(func=self.SnhXmppStats)

        parser_xmpp_conn = parser_xmpp.add_parser('conn', help='XMPP connections')
        parser_xmpp_conn.set_defaults(func=self.SnhXmppConn)

        ## IFMAP
        parser_sub = self.subparser.add_parser('ifmap', help='Show IFMAP info')
        parser_ifmap = parser_sub.add_subparsers()

        parser_ifmap_xmpp = parser_ifmap.add_parser('xmppclient', help='IFMAP xmpp clients info')
        parser_ifmap_xmpp.add_argument('client', nargs='?', help='client index or name')
        parser_ifmap_xmpp.add_argument('-t', '--type', choices=['node', 'link', 'all'], default='all', help='IFMAP data types')
        parser_ifmap_xmpp.set_defaults(func=self.SnhXmppClient)

        parser_ifmap_tbl = parser_ifmap.add_parser('table', help='IFMAP table  info')
        parser_ifmap_tbl.add_argument('-t', '--table', default='', help='ifmap table e.g. access-control-list, security-group etc')
        parser_ifmap_tbl.add_argument('-s', '--search', default='', help='fq_node_name')
        parser_ifmap_tbl.set_defaults(func=self.SnhIFMapTableShow)

        parser_ifmap_node = parser_ifmap.add_parser('node', help='IFMAP node data info')
        parser_ifmap_node.add_argument('name', nargs='?', help='fq_node_name')
        parser_ifmap_node.set_defaults(func=self.SnhIFMapNodeShow)

        parser_ifmap_link = parser_ifmap.add_parser('link', help='IFMAP link data info')
        parser_ifmap_link.add_argument('search', nargs='?', default='', help='search string')
        parser_ifmap_link.set_defaults(func=self.SnhIFMapLinkShow)

        ## ServiceChain
        parser_sc = self.subparser.add_parser('sc', help='Show ServiceChain info')
        parser_sc.add_argument('search', nargs='?', default='', help='search string')
        parser_sc.add_argument('-s', '--state', choices=['pending', 'all'], default='all', help='servicechain state. Default = all')
        parser_sc.add_argument('-d', '--detail', action="store_true", default=False, help='Display detailed output')
        parser_sc.add_argument('-r', '--route', action="store_true", default=False, help='include route info.')
        parser_sc.set_defaults(func=self.SnhSC)

        ## Config related
        parser_sub = self.subparser.add_parser('config', help='Show related config info')
        parser_config = parser_sub.add_subparsers()

        parser_config_ri = parser_config.add_parser('ri', help='Routing instances')
        parser_config_ri.add_argument('search', nargs='?', default='', type=str, help='Search string')
        parser_config_ri.add_argument('-d', '--detail', action="store_true", help='Display detailed output')
        parser_config_ri.set_defaults(func=self.SnhShowBgpInstanceConfigReq)

        parser_config_rp = parser_config.add_parser('rp', help='Routing Policy (available on Contrail 3.0+)')
        parser_config_rp.add_argument('search', nargs='?', default='', type=str, help='Search string')
        parser_config_rp.set_defaults(func=self.SnhShowBgpRoutingPolicyConfigReq)

        parser_config_bgp = parser_config.add_parser('bgp', help='BGP neighbor')
        parser_config_bgp.add_argument('search', nargs='?', default='', type=str, help='Search string')
        parser_config_bgp.add_argument('-t', '--type', choices=['bgpaas', 'fabric','all'], default='all', help='filter by router_type. Default = all')
        parser_config_bgp.set_defaults(func=self.SnhShowBgpNeighborConfigReq)

        ## RT
        parser_rt = self.subparser.add_parser('rt', help='Show RtGroup info')
        parser_rt.add_argument('search', nargs='?', default='', help='search string')
        parser_rt.add_argument('-d', '--detail', action="store_true", default=False, help='Display detailed output')
        parser_rt.set_defaults(func=self.SnhShowRtGroupReq)

    def SnhShowRtGroupReq(self, args):
        if args.detail:
            self.IST.get('Snh_ShowRtGroupReq?search_string=' + args.search)
        else:
            self.IST.get('Snh_ShowRtGroupSummaryReq?search_string=' + args.search)
        xpath = '//ShowRtGroupInfo'
        self.IST.printTbl(xpath)

    def SnhShowBgpNeighborConfigReq(self, args):
        self.IST.get('Snh_ShowBgpNeighborConfigReq?search_string=' + args.search)
        xpath = '//ShowBgpNeighborConfig'
        if args.type == 'bgpaas':
            xpath += "[contains(router_type, '%s')]" % args.type
        elif args.type == 'fabric':
            xpath += "[router_type[not(normalize-space())]]"
        self.IST.printText(xpath)

    def SnhShowBgpRoutingPolicyConfigReq(self, args):
        self.IST.get('Snh_ShowBgpRoutingPolicyConfigReq?search_string=' + args.search)
        xpath = '//ShowBgpRoutingPolicyConfig'
        self.IST.printText(xpath)

    def SnhShowBgpInstanceConfigReq(self, args):
        self.IST.get('Snh_ShowBgpInstanceConfigReq?search_string=' + args.search)
        xpath = '//ShowBgpInstanceConfig'

        if (args.search and args.detail):
            self.IST.printText(xpath)
        else:
            self.IST.printTbl(xpath, 'name', 'virtual_network_index', 'vxlan_id', 'import_target', 'export_target', 'has_pnf', 'last_change_at')

    def SnhSC(self, args):
        if args.state == 'pending':
            self.IST.get('Snh_ShowPendingServiceChainReq?search_string=' + args.search)
            self.IST.printText('//pending_chains/list/element')
        else:
            self.IST.get('Snh_ShowServiceChainReq?search_string=' + args.search)
            if args.route:
                if args.detail:
                    self.IST.showSCRouteDetail('//ShowServicechainInfo')
                else:
                    self.IST.showSCRoute('//ShowServicechainInfo')
            else:
                self.IST.printTbl('//ShowServicechainInfo', 'src_virtual_network', 'dest_virtual_network', 'service_instance', 'src_rt_instance', 'dest_rt_instance', 'state')

    def SnhIFMapTableShow(self, args):
        self.IST.get('Snh_IFMapTableShowReq?table_name=' + args.table + '&search_string=' + args.search)
        #self.IST.printTbl('//IFMapNodeShowInfo', 'node_name', 'interests', 'advertised', 'dbentryflags', 'last_modified', 'neighbors')
        self.IST.printTbl('//IFMapNodeShowInfo', 'node_name', 'interests', 'advertised', 'dbentryflags', 'last_modified')

    def SnhIFMapLinkShow(self, args):
        self.IST.get('Snh_IFMapLinkTableShowReq?search_string=' + args.search)
        self.IST.printText('//metadata|//left|//right')

    def SnhIFMapNodeShow(self, args):
        if args.name is not None:
            self.IST.get('Snh_IFMapNodeShowReq?fq_node_name=' + args.name)
            self.IST.printText('//IFMapObjectShowInfo/data')
            print "Neighbor:"
            self.IST.printText('//neighbors/list/element')
        elif args.search is not None:
            self.IST.get('Snh_IFMapTableShowReq?search_string=' + args.search)
            self.IST.printText('//node_name')
        else:
            self.IST.get('Snh_IFMapNodeTableListShowReq')
            self.IST.printTbl('//IFMapNodeTableListShowEntry')

    def SnhXmppClient(self, args):
        if args.client is None:
            self.IST.get('Snh_IFMapXmppClientInfoShowReq')
            self.IST.printTbl('//IFMapXmppClientInfo')
        else:
            if args.type != 'link':
                self.IST.get('Snh_IFMapPerClientNodesShowReq?client_index_or_name=' + args.client)
                self.IST.printTbl('//IFMapPerClientNodesShowInfo')
            if args.type != 'node':
                self.IST.get('Snh_IFMapPerClientLinksShowReq?client_index_or_name=' + args.client)
                self.IST.printText('//IFMapPerClientLinksShowInfo')

    def SnhXmppMsg(self, args):
        self.IST.get('Snh_SandeshTraceRequest?x=XmppMessageTrace')
        self.IST.printText('//element')

    def SnhXmppStats(self, args):
        self.IST.get('Snh_ShowXmppServerReq')
        self.IST.printText('//ShowXmppServerResp/*')

    def SnhXmppConn(self, args):
        self.IST.get('Snh_ShowXmppConnectionReq')
        self.IST.printTbl('//ShowXmppConnection')

    def SnhBgpNeighbor(self, args):
        self.IST.get('Snh_BgpNeighborReq?search_string=' + args.search)

        xpath = "//BgpNeighborResp[encoding='" + args.type + "']" if args.type else  "//BgpNeighborResp"

        if (args.search):
            self.IST.printText(xpath + "/*")
        else:
            self.IST.printTbl(xpath, "peer", "peer_address", "peer_asn", "encoding", "peer_type", "state", "send_state", "flap_count", "flap_time")

    def SnhRoutingInstance(self, args):
        self.IST.get('Snh_ShowRoutingInstanceReq?search_string=' + args.search)
        xpath = "//ShowRoutingInstance"

        if (args.search and args.detail):
            self.IST.printText(xpath + "/*")
        else:
            #self.IST.printTbl(xpath, "name", "virtual_network", "vn_index", "vxlan_id", "import_target", "export_target")
            self.IST.printTbl(xpath, "name", "vn_index", "vxlan_id", "import_target", "export_target", "routing_policies")

    def SnhShowRouteSummary(self, args):
        self.IST.get('Snh_ShowRouteSummaryReq?search_string=' + args.search)
        xpath = "//ShowRouteTableSummary"
        if args.family != 'all':
            xpath += "[contains(name, '%s.0')]" % args.family

        self.IST.printTbl(xpath, "name", "prefixes", "paths", "primary_paths", "secondary_paths", "infeasible_paths")

    def SnhShowRTable(self, args):
        self.IST.get('Snh_ShowRouteSummaryReq?search_string=' + args.search)
        xpath = "//ShowRouteTableSummary/name"
        if args.family != 'all':
            xpath = "//ShowRouteTableSummary[contains(name, '%s.0')]/name" % args.family

        self.IST.printText(xpath)

    def SnhShowRoute(self, args):
        path = 'Snh_ShowRouteReq?routing_table=' + args.table + \
                '&routing_instance=' + args.vrf +\
                '&prefix=' + args.prefix

        self.IST.get(path)

        if args.detail:
            mode = 'detail'
        elif args.raw:
            mode = 'raw'
        else:
            mode ='brief'

        self.IST.showRoute_CTR(args.address, args.protocol, args.table, args.source, args.family, args.last, mode)

class vRouter_CLI(Contrail_CLI):
    def __init__(self, parser, host, port, max_width):

        IShost = 'localhost' if host is None else host
        ISport ='8085' if port is None else port

        Contrail_CLI.__init__(self, parser, IShost, ISport, max_width)
        self.parse_args()

    def parse_args(self):

        parser_intf = self.subparser.add_parser('intf', help='Show vRouter interfaces')
        parser_intf.add_argument('search', nargs='?', default='', help='Search string')
        parser_intf.add_argument('-u', '--uuid', default='', help='Interface uuid')
        parser_intf.add_argument('-v', '--vn', default='', help='Virutal network')
        parser_intf.add_argument('-n', '--name', default='', help='Interface name')
        parser_intf.add_argument('-m', '--mac', default='', help='VM mac address')
        parser_intf.add_argument('-i', '--ipv4', default='', help='VM IP address')
        parser_intf.add_argument('-d', '--detail', action="store_true", help='Display detailed output')
        parser_intf.set_defaults(func=self.SnhItf)

        parser_vn = self.subparser.add_parser('vn', help='Show Virtual Network')
        parser_vn.add_argument('name', nargs='?', default='', help='VN name')
        parser_vn.add_argument('-u', '--uuid', default='', help='VN uuid')
        parser_vn.add_argument('-d', '--detail', action="store_true", help='Display detailed output')
        parser_vn.set_defaults(func=self.SnhVn)

        parser_vrf = self.subparser.add_parser('vrf', help='Show VRF')
        parser_vrf.add_argument('name', nargs='?', default='', help='VRF name')
        parser_vrf.add_argument('-d', '--detail', action="store_true", help='Display detailed output')
        parser_vrf.set_defaults(func=self.SnhVrf)

        parser_route = self.subparser.add_parser('route', help='Show routes')
        parser_route.add_argument('address', nargs='?', default='', help='Address')
        parser_route.add_argument('-v', '--vrf', type=int, default=0, help='VRF index, default: 0 (IP fabric)')
        parser_route.add_argument('-f', '--family', choices=['inet', 'inet6', 'bridge', 'layer2', 'evpn'], default='', help='Route family')
        parser_route.add_argument('-p', '--prefix', default='/', help='IPv4 or IPv6 prefix')
        #parser_route.add_argument('-m', '--mac', default='', help='MAC address')
        #parser_route.add_argument('-D', '--destination', type=valid_ipv4, help='Show matched routes (only IPv4 is supported)')
        parser_route.add_argument('-d', '--detail', action="store_true", help='Display detailed output')
        parser_route.add_argument('-r', '--raw', action="store_true", help='Display raw output in plain text')
        parser_route.set_defaults(func=self.SnhRoute)

        parser_sg = self.subparser.add_parser('sg', help='Show Security Groups')
        parser_sg.set_defaults(func=self.SnhSg)

        parser_acl = self.subparser.add_parser('acl', help='Show ACL info')
        parser_acl.add_argument('uuid', nargs='?', default='', help='ACL uuid')
        parser_acl.set_defaults(func=self.SnhAcl)

        parser_hc = self.subparser.add_parser('hc', help='Health Check info')
        parser_hc.add_argument('name', nargs='?', default='', help='HC name')
        parser_hc.set_defaults(func=self.SnhHealthCheck)

        parser_ifmap = self.subparser.add_parser('ifmap', help='IFMAP info')
        parser_ifmap.add_argument('-t', '--table', default='', help='Table names. e.g. virtual-router, virtual-machine-interface, type:virtual-machine, instance-ip')
        parser_ifmap.add_argument('-n', '--node', default='', help='Node sub string')
        parser_ifmap.add_argument('-l', '--link', default='', help='Link sub string')
        parser_ifmap.set_defaults(func=self.SnhShowIFMap)

        parser_baas = self.subparser.add_parser('baas', help='Bgp As A Service info')
        parser_baas.set_defaults(func=self.SnhBaaS)

        parser_xmpp = self.subparser.add_parser('xmpp', help='Show Agent XMPP connections (route&config) status')
        parser_xmpp.add_argument('-d', action="store_true", help='Show Agent XMPP connection details')
        parser_xmpp.set_defaults(func=self.SnhXmpp)

        parser_xmppdns = self.subparser.add_parser('xmpp-dns', help='Show Agent XMPP connections (dns) status')
        parser_xmppdns.add_argument('-d', action="store_true", help='Show Agent XMPP connection details')
        parser_xmppdns.set_defaults(func=self.SnhDNSXmpp)

        parser_stats = self.subparser.add_parser('stats', help='Show Agent stats')
        parser_stats.set_defaults(func=self.SnhAgentStats)


        ## Service subcommand
        parser_sub = self.subparser.add_parser('service', help='Service related info')
        parser_svc = parser_sub.add_subparsers()

        parser_svc_stats = parser_svc.add_parser('stats', help='All service stats')
        parser_svc_stats.set_defaults(func=self.SnhSvcStats)

        parser_icmp = parser_svc.add_parser('icmp', help='icmp stats or pkt trace')
        parser_icmp.add_argument('-d', action="store_true", help='Show packet trace details')
        parser_icmp.set_defaults(func=self.SnhIcmp)

        parser_icmp6 = parser_svc.add_parser('icmp6', help='icmpv6 stats or pkt trace')
        parser_icmp6.add_argument('-d', action="store_true", help='Show packet trace details')
        parser_icmp6.set_defaults(func=self.SnhIcmp6)

        parser_dhcp = parser_svc.add_parser('dhcp', help='dhcp stats or pkt trace')
        parser_dhcp.add_argument('-d', action="store_true", help='Show packet trace details')
        parser_dhcp.set_defaults(func=self.SnhDhcp)

        parser_dhcp6 = parser_svc.add_parser('dhcp6', help='dhcpv6 stats or pkt trace')
        parser_dhcp6.add_argument('-d', action="store_true", help='Show packet trace details')
        parser_dhcp6.set_defaults(func=self.SnhDhcp6)

        parser_arp = parser_svc.add_parser('arp', help='ARP stats or pkt trace')
        parser_arp.add_argument('-d', action="store_true", help='Show packet trace details')
        parser_arp.add_argument('-i', action="store_true", help='Show arp stats per interface')
        parser_arp.set_defaults(func=self.SnhArp)

        parser_arpCache = parser_svc.add_parser('arpCache', help='ARP Cache')
        parser_arpCache.set_defaults(func=self.SnhArpCache)

        parser_dns = parser_svc.add_parser('dns', help='dns stats or pkt trace')
        parser_dns.add_argument('-d', action="store_true", help='Show packet trace details')
        parser_dns.set_defaults(func=self.SnhDns)

        parser_meta = parser_svc.add_parser('metadata', help='Metadata info')
        parser_meta.set_defaults(func=self.SnhMetadata)

    def SnhItf(self, args):
        path = 'Snh_ItfReq?name=' + args.name + '&type=&uuid=' + args.uuid + '&vn=' + args.vn + '&mac=' + args.mac + '&ipv4_address=' + args.ipv4
        self.IST.get(path)

        xpath = "//ItfSandeshData"
        if args.search: xpath += "[contains(., '%s')]" % args.search

        if args.detail:
            self.IST.printText(xpath)
        else:
            self.IST.printTbl(xpath, "index", "name", "active", "mac_addr", "ip_addr", "mdata_ip_addr", "vm_name", "vn_name")

    def SnhVn(self, args):
        path = 'Snh_VnListReq?name=' + args.name + '&uuid=' + args.uuid
        self.IST.get(path)
        if args.detail:
            self.IST.printText("//VnSandeshData")
        else:
            self.IST.printTbl("//VnSandeshData", "name", "uuid", "layer2_forwarding", "ipv4_forwarding", "enable_rpf", "bridging", "ipam_data")

    def SnhVrf(self, args):
        path = 'Snh_VrfListReq?name=' + args.name
        self.IST.get(path)
        if args.detail:
            self.IST.printText("//VrfSandeshData")
        else:
            self.IST.printTbl("//VrfSandeshData", "name", "ucindex", "mcindex", "brindex", "evpnindex", "vxlan_id", "vn")

    def SnhSg(self, args):
        self.IST.get('Snh_SgListReq')
        self.IST.printTbl("//SgSandeshData")

    def SnhAcl(self, args):
        self.IST.get('Snh_AclReq?uuid=' + args.uuid)
        self.IST.printText("//AclSandeshData")

    def SnhRoute(self, args):

        if args.family =='':
            if args.address == '' or is_ipv4(args.address):
                args.family = 'inet'
            elif is_ipv6(args.address):
                args.family = 'inet6'
            else:
                args.family = 'layer2'

        if args.family == 'inet':
            p=args.prefix.split('/')
            if len(p) == 1: p.append('32')
            path = 'Snh_Inet4UcRouteReq?vrf_index=' + str(args.vrf) + '&src_ip=' + p[0] + '&prefix_len=' + p[1] + '&stale='
            xpath = '//RouteUcSandeshData'
            if args.address and not is_ipv4(args.address): xpath += "[contains(src_ip, '%s')]" % args.address

        elif args.family == 'inet6':
            p=args.prefix.split('/')
            if len(p) == 1: p.append('128')
            path = 'Snh_Inet6UcRouteReq?vrf_index=' + str(args.vrf) + '&src_ip=' + p[0] + '&prefix_len=' + p[1] + '&stale='
            xpath = '//RouteUcSandeshData'
            if args.address and not is_ipv6(args.address): xpath += "[contains(src_ip, '%s')]" % args.address

        else:
            mapping = {
                'bridge': ['Snh_BridgeRouteReq?vrf_index=', '//RouteL2SandeshData'],
                'evpn': ['Snh_EvpnRouteReq?vrf_index=', '//RouteEvpnSandeshData'],
                'layer2': ['Snh_Layer2RouteReq?vrf_index=', '//RouteL2SandeshData']
            }
            path = mapping.get(args.family, '')[0] + str(args.vrf)
            xpath = mapping.get(args.family, '')[1]
            if args.address: xpath += "[contains(mac, '%s')]" % args.address

        if args.detail:
            mode = 'detail'
        elif args.raw:
            mode = 'raw'
        else:
            mode ='brief'

        self.IST.get(path)
        self.IST.showRoute_VR(xpath, args.family, args.address, mode)

    def SnhXmpp(self, args):
        self.IST.get('Snh_AgentXmppConnectionStatusReq')
        if args.d:
            self.IST.printText("//AgentXmppData")
        else:
            self.IST.printTbl("//AgentXmppData", "controller_ip", "state", "peer_name", "peer_address", "cfg_controller", "flap_count", "flap_time")

    def SnhDNSXmpp(self, args):
        self.IST.get('Snh_AgentDnsXmppConnectionStatusReq')
        if args.d:
            self.IST.printText("//AgentXmppDnsData")
        else:
            self.IST.printTbl("//AgentXmppDnsData", "dns_controller_ip", "state", "peer_name", "peer_address", "flap_count", "flap_time")

    def SnhAgentStats(self, args):
        self.IST.get('Snh_AgentStatsReq')
        self.IST.printText("//__IpcStatsResp_list/*")

    def SnhSvcStats(self, args):
        self.IST.get('Snh_ShowAllInfo')
        self.IST.printText("//*[self::PktStats or self::DhcpStats or self::ArpStats or self::DnsStats or self::IcmpStats or self::MetadataResponse]")

    def SnhIcmp(self, args):
        self.IST.get('Snh_IcmpInfo')
        if args.d:
            self.IST.printText("//IcmpPktSandesh")
        else:
            self.IST.printText("//IcmpStats/*")

    def SnhIcmp6(self, args):
        self.IST.get('Snh_Icmpv6Info')
        if args.d:
            self.IST.printText("//Icmpv6PktSandesh")
        else:
            self.IST.printText("//Icmpv6Stats/*")

    def SnhDhcp(self, args):
        self.IST.get('Snh_DhcpInfo')
        if args.d:
            self.IST.printText("//DhcpPktSandesh")
        else:
            self.IST.printText("//DhcpStats/*")

    def SnhDhcp6(self, args):
        self.IST.get('Snh_Dhcpv6Info')
        if args.d:
            self.IST.printText("//Dhcpv6PktSandesh")
        else:
            self.IST.printText("//Dhcpv6Stats/*")

    def SnhArp(self, args):
        if args.i:
            self.IST.get('Snh_InterfaceArpStatsReq')
            self.IST.printTbl("//InterfaceArpStats")
        else:
            self.IST.get('Snh_ArpInfo')
            if args.d:
                self.IST.printText("//ArpPktSandesh")
            else:
                self.IST.printText("//ArpStats/*")

    def SnhArpCache(self, args):
        self.IST.get('Snh_ShowArpCache')
        self.IST.printTbl("//ArpSandeshData")

    def SnhDns(self, args):
        self.IST.get('Snh_DnsInfo')
        if args.d:
            self.IST.printText("//DnsPktSandesh")
        else:
            self.IST.printText("//DnsStats/*")

    def SnhMetadata(self, args):
        self.IST.get('Snh_MetadataInfo')
        self.IST.printText("//MetadataResponse/*")

    def SnhHealthCheck(self,args):
        self.IST.get('Snh_HealthCheckSandeshReq')
        if args.name:
            self.IST.printText("//HealthCheckSandeshData[contains(name,'%s')]//HealthCheckInstanceSandeshData/*" % args.name)
        else:
            self.IST.printTbl("//HealthCheckSandeshData", "uuid", "name", "monitor_type",
                "http_method", "url_path", "expected_codes", "delay", "timeout", "max_retries")

    def SnhBaaS(self,args):
        self.IST.get('Snh_BgpAsAServiceSandeshReq')
        self.IST.printTbl("//BgpAsAServiceSandeshList")

    def SnhShowIFMap(self, args):
        path = 'Snh_ShowIFMapAgentReq?table_name=' + args.table + '&node_sub_string=' + args.node + "&link_type_sub_string=" + args.link
        self.IST.get(path)
        self.IST.printText("//element")


class Collector_CLI(Contrail_CLI):

    def __init__(self, parser, host, port, max_width):

        IShost = 'localhost' if host is None else host
        ISport ='8089' if port is None else port

        Contrail_CLI.__init__(self, parser, IShost, ISport, max_width)

        self.parse_args()

    def parse_args(self):
        parser_svr = self.subparser.add_parser('server', help='Show collector server info')
        parser_svr.add_argument('type', nargs='?', choices=['stats', 'generators', 'all'], default='all', help='stats|connection|all')
        parser_svr.set_defaults(func=self.SnhShowCollectorServerReq)

        parser_redis = self.subparser.add_parser('redis', help='Show redis server UVE info')
        parser_redis.set_defaults(func=self.SnhRedisUVERequest)

    def SnhShowCollectorServerReq(self, args):
        self.IST.get('Snh_ShowCollectorServerReq')
        if args.type != 'generators':
            self.IST.printText("/ShowCollectorServerResp/rx_socket_stats")
            self.IST.printText("/ShowCollectorServerResp/tx_socket_stats")
            self.IST.printText("/ShowCollectorServerResp/stats")
            self.IST.printText("/ShowCollectorServerResp/cql_metrics")
        if args.type != "stats":
            print 'generators:'
            self.IST.printTbl("//GeneratorSummaryInfo")

    def SnhRedisUVERequest(self, args):
        self.IST.get('Snh_RedisUVERequest')
        self.IST.printText("//RedisUveInfo/*")

class Analytics_CLI(Contrail_CLI):
    def __init__(self, parser, host, port, max_width):

        IShost = 'localhost' if host is None else host
        ISport ='8090' if port is None else port

        Contrail_CLI.__init__(self, parser, IShost, ISport, max_width)

# class Query_Engine_CLI(Contrail_CLI):
#     def __init__(self, parser):
#         IShost ='localhost'
#         ISport ='8091'
#         Contrail_CLI.__init__(self, parser, IShost, ISport)

# class Device_Manager_CLI(Contrail_CLI):
#     def __init__(self, parser):
#         IShost ='localhost'
#         ISport ='8096'
#         Contrail_CLI.__init__(self, parser, IShost, ISport)

# class Discovery_CLI(Contrail_CLI):
#     def __init__(self, parser):
#         IShost ='localhost'
#         ISport ='5997'
#         Contrail_CLI.__init__(self, parser, IShost, ISport)

# Modules for contrail-analytics-nodemgr
# http://10.85.19.196:8104

# Modules for contrail-database-nodemgr
# http://10.85.19.196:8103

# Modules for contrail-control-nodemgr
# http://10.85.19.196:8101

#Modules for contrail-config-nodemgr
# http://10.85.19.196:8100

# HttpPortConfigNodemgr = 8100
# HttpPortControlNodemgr = 8101
# HttpPortVRouterNodemgr = 8102
# HttpPortDatabaseNodemgr = 8103
# HttpPortAnalyticsNodemgr = 8104



def valid_period(s):
    if (not (s[-1] in 'smhdw') and s[0:-1].isdigit()):
        msg = "Not a valid time period. format: number followed one of charactors (s: seconds, m: minutes, h: hours, w:weeks)"
        raise argparse.ArgumentTypeError(msg)
    else:
        mapping = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        return int(s[0:-1]) * mapping.get(s[-1], 0)

# def valid_ipv4(addr):
#     if is_ipv4(addr):
#         return addr
#     else:
#         msg = "Not a valid IPv4 addeess."
#         raise argparse.ArgumentTypeError(msg)

def is_ipv4(addr):
    try:
        socket.inet_pton(socket.AF_INET, addr)
    except socket.error:
        return False
    return True

def is_ipv6(addr):
    try:
        socket.inet_pton(socket.AF_INET6, addr)
    except socket.error:
        return False
    return True

def addressInNetwork(addr, prefix):
    ipaddr = struct.unpack('!L',socket.inet_aton(addr))[0]
    pure_prefix = prefix.split(':')[-1]  # strip RD info if any
    netaddr,bits = pure_prefix.split('/')
    netaddr = struct.unpack('!L',socket.inet_aton(netaddr))[0]
    netmask = ((1<<(32-int(bits))) - 1)^0xffffffff
    return ipaddr & netmask == netaddr & netmask

def addressInNetwork6(addr, prefix):
    addr_upper,addr_lower = struct.unpack('!QQ',socket.inet_pton(socket.AF_INET6, addr))
    #if debug: print "{0:b}".format(ip_lower)
    netaddr,bits = prefix.split('/')
    net_upper,net_lower = struct.unpack('!QQ',socket.inet_pton(socket.AF_INET6, netaddr))
    if int(bits) < 65 :
        netmask = ((1<<(64-int(bits))) - 1)^0xffffffffffffffff
        return addr_upper & netmask == net_upper & netmask
    elif addr_upper != net_upper:
        return False
    else:
        netmask = ((1<<(128-int(bits))) - 1)^0xffffffffffffffff
        return addr_lower & netmask == net_lower & netmask

def main():

    argv = sys.argv[1:]

    if '--version' in argv:
        print version
        sys.exit()

    host = os.environ.get('INTROSPECT_HOST', None)
    port = os.environ.get('INTROSPECT_PORT', None)

    try:
        host = argv[argv.index('--host') + 1]
    except ValueError:
        pass

    try:
        port = argv[argv.index('--port') + 1]
    except ValueError:
        pass

    try:
        max_width = argv[argv.index('--max-width') + 1]
    except ValueError:
        max_width = 60
        pass

    if host:
        print "Introspect Host: " + host

    global debug
    if '--debug' in argv:
        debug = True

    parser = argparse.ArgumentParser(prog='ist', description='A script to make Contrail Introspect output CLI friendly.')
    parser.add_argument('--version', action="store_true", help="Show script version")
    parser.add_argument('--debug', action="store_true", help="debug mode")
    parser.add_argument('--max-width', type=int, default=60, help="max width per column")

    roleparsers = parser.add_subparsers()

    parse_vr = roleparsers.add_parser('vr', help='Show vRouter info')
    vRouter_CLI(parse_vr, host, port, max_width)

    parse_ctr = roleparsers.add_parser('ctr', help='Show Control node info')
    Control_CLI(parse_ctr, host, port, max_width)

    parse_cfg_api = roleparsers.add_parser('cfg-api', help='Show contrail-api info')
    Config_API_CLI(parse_cfg_api, host, port, max_width)

    parse_cfg_sch = roleparsers.add_parser('cfg-sch', help='Show contrail-schema info')
    Config_SCH_CLI(parse_cfg_sch, host, port, max_width)

    parse_cfg_svc = roleparsers.add_parser('cfg-svc', help='Show contrail-svc-monitor info')
    Config_SVC_CLI(parse_cfg_svc, host, port, max_width)

    parse_collector = roleparsers.add_parser('collector', help='Show contrail-collector info')
    Collector_CLI(parse_collector, host, port, max_width)

    parse_analytics = roleparsers.add_parser('analytics', help='Show contrail-analytics-api info')
    Analytics_CLI(parse_analytics, host, port, max_width)

    # parse_qe = roleparsers.add_parser('qe', help='Show contrail-query-engine info')
    # Query_Engine_CLI(parse_qe)

    # parse_dm = roleparsers.add_parser('dm', help='Show device manager info')
    # Device_Manager_CLI(parse_dm)

    # parse_disc = roleparsers.add_parser('disc', help='Show contrail-discovery info')
    # Discovery_CLI(parse_disc)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
