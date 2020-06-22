#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Sandesh Http
#

import pkgutil
import importlib
import sys
#
# Prevent:
# Exception KeyError: KeyError(40918224,) in <module 'threading' from '/usr/lib64/python2.7/threading.pyc'> ignored
# as per
# http://stackoverflow.com/questions/8774958/keyerror-in-module-threading-after-a-successful-py-test-run
#
if 'threading' in sys.modules:
    del sys.modules['threading']
from gevent import monkey; monkey.patch_all()
from gevent.server import StreamServer
from gevent.pywsgi import WSGIServer
import bottle
import cStringIO
from transport import TTransport
from protocol import TXMLProtocol
import os
import socket
from gevent import ssl

class SandeshStdLog(object):
    def __init__(self, server_name, http_port):
        self._server_name = server_name
        self._port = http_port

    def write(self, text):
        sys.stderr.write('[' + self._server_name + ':' + str(self._port) + ']' + text)

class SandeshHttp(object):

    _HTTP_SERVER_IP = '0.0.0.0'
    _http_response = None
    _http_response_context = None
    _logger = None

    WebFilesList = [
    '/css/bootstrap.min.css',
    '/css/DT_bootstrap.css',
    '/css/images/sort_asc.png',
    '/css/images/sort_asc_disabled.png',
    '/css/images/sort_both.png',
    '/css/images/sort_desc.png',
    '/css/images/sort_desc_disabled.png',
    '/css/style.css',
    '/js/bootstrap.min.js',
    '/js/DT_bootstrap.js',
    '/js/jquery-2.0.3.min.js',
    '/js/jquery.dataTables.min.js',
    '/js/util.js',
    '/universal_parse.xsl']

    def __init__(self, sandesh, module, port, pkg_list, sandesh_config=None,
            http_server_ip=None):
        self._sandesh = sandesh
        self._logger = sandesh.logger()
        self._module = module
        self._http_ip = http_server_ip \
                if http_server_ip is not None else SandeshHttp._HTTP_SERVER_IP
        self._http_port = port
        self._http_request_dict = {}
        self._http_app = bottle.Bottle()
        self._create_homepage(pkg_list)
        # Register the homepage
        self._http_app.route('/', 'GET', self._get_homepage)
        self._http_app.route('/index.html', 'GET', self._get_homepage)
        self._http_app.route('/<link:re:\w+.xml>', 'GET', self._get_indexpage)
        # Get the path of universal_parse.xsl and jquery and register the same
        self._webfiles_path = None
        self._universal_parse_xsl_path = None
        self._jquery_collapse_storage_js_path = None
        self._jquery_collapse_js_path = None
        self._jquery_1_8_1_js_path = None
        self._http_server = None
        self._sandesh_config = sandesh_config
        self._std_log = SandeshStdLog("Introspect", self._http_port)

        try:
            imp_pysandesh = __import__('pysandesh')
        except ImportError:
            self._logger.error('Failed to import "pysandesh"')
        else:
            self._webfiles_path = imp_pysandesh.__path__[0]
            self._universal_parse_xsl_path = imp_pysandesh.__path__[0]
            self._jquery_collapse_storage_js_path = imp_pysandesh.__path__[0]
            self._jquery_collapse_js_path = imp_pysandesh.__path__[0]
            self._jquery_1_8_1_js_path = imp_pysandesh.__path__[0]

        for elem in SandeshHttp.WebFilesList:
            #import pdb; pdb.set_trace()
            self._http_app.route(elem, 'GET', self._get_webfiles)

    #end __init__

    def stop_http_server(self):
        if self._http_server:
            self._http_server.stop()
            self._http_server = None
            self._logger.error('Stopped http server')
    # end stop_http_server

    def start_http_server(self):
        try:
            sock = StreamServer.get_listener((self._http_ip,
                    self._http_port), family=socket.AF_INET)
        except socket.error as e:
            self._logger.error('Unable to open HTTP Port %d, %s' %
                (self._http_port, e))
            sys.exit()
        else:
            self._http_port = sock.getsockname()[1]
            self._sandesh.record_port("http", self._http_port)
            self._logger.error('Starting Introspect on HTTP Port %d' %
                self._http_port)
            if self._sandesh_config:
                if self._sandesh_config.tcp_keepalive_enable:
                    self.set_socket_options(sock)
                if self._sandesh_config.introspect_ssl_enable:
                    ca_certs=self._sandesh_config.ca_cert
                    keyfile=self._sandesh_config.keyfile
                    certfile=self._sandesh_config.certfile
                    self._http_server = WSGIServer(sock, self._http_app,
                        ca_certs=ca_certs, keyfile=keyfile,
                        certfile=certfile, ssl_version=ssl.PROTOCOL_SSLv23,
                        cert_reqs=ssl.CERT_REQUIRED, log=self._std_log)
                else:
                    self._http_server = WSGIServer(sock, self._http_app, log=self._std_log)
            self._http_server.serve_forever()
    # end start_http_server

    def set_socket_options(self, sock):
        if hasattr(socket, 'SO_KEEPALIVE'):
           sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, 'TCP_KEEPIDLE'):
           sock.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,
                self._sandesh_config.tcp_keepalive_idle_time)
        if hasattr(socket, 'TCP_KEEPINTVL'):
           sock.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPINTVL,
                self._sandesh_config.tcp_keepalive_interval)
        if hasattr(socket, 'TCP_KEEPCNT'):
           sock.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPCNT,
                self._sandesh_config.tcp_keepalive_probes)
    #end set_socket_options

    def get_port(self):
        return self._http_port
    #end get_port

    @staticmethod
    def http_error(err_msg):
        return '<h3>%s</h3>' % (err_msg)
    #end http_error

    @staticmethod
    def create_http_response(sandesh_resp, sandesh_init):
        universal_xsl_str = '<?xml-stylesheet type="text/xsl" href="/universal_parse.xsl"?>'
        transport = TTransport.TMemoryBuffer()
        protocol_factory = TXMLProtocol.TXMLProtocolFactory()
        protocol = protocol_factory.getProtocol(transport)
        if sandesh_resp.write(protocol) < 0:
            sandesh_init.logger().error('Http Response: Failed to encode sandesh (%s)', sandesh_resp.__class__.__name__)
            return
        sandesh_resp_xml = transport.getvalue()
        if not SandeshHttp._http_response:
            SandeshHttp._state = 'HXMLNew'
            SandeshHttp._http_response = cStringIO.StringIO()
            SandeshHttp._http_response.write(universal_xsl_str)
            if sandesh_resp._more:
                sandesh_name_end = sandesh_resp_xml.find(' ')
                if sandesh_name_end == -1:
                    sandesh_init.logger().error('Http Response: Failed to get Sandesh name (%s)', sandesh_resp.__class__.__name__)
                    return
                SandeshHttp._http_response_context = sandesh_resp_xml[1:sandesh_name_end]
                SandeshHttp._http_response.write('<__%s_list type="slist">' % (SandeshHttp._http_response_context))
                SandeshHttp._state = 'HXMLIncomplete'        
        SandeshHttp._http_response.write(sandesh_resp_xml)
        if not sandesh_resp._more and SandeshHttp._state != 'HXMLNew':
            SandeshHttp._http_response.write('</__%s_list>' % (SandeshHttp._http_response_context))
    #end create_http_response

    @staticmethod
    def get_http_response():
        if SandeshHttp._http_response:
            bottle.response.headers['Content-Type'] = 'text/xsl'
            resp = SandeshHttp._http_response.getvalue()
            SandeshHttp._http_response.close()
            SandeshHttp._http_response = None
            SandeshHttp._http_response_context = None
            return resp
        return None
    #end get_http_response

    def _get_homepage(self):
        bottle.response.headers['Content-Type'] = 'text/html'
        return self._homepage
    #end _get_homepage

    def _get_indexpage(self, link):
        try:
            path = self._homepage_links[link]
        except KeyError:
            return self.http_error('Invalid Sandesh Request "%s"' % (link))
        else:
            return bottle.static_file(link, root=path)
    #end _get_indexpage

    def _get_webfiles(self):
        terms = bottle.request.url.rsplit('/', 1)
        fname = "/" + terms[1]
        upath = terms[0].split('//',1)[-1]
        pterms = upath.split('/',1)
        if len(pterms) == 1:
            fpath = self._webfiles_path + '/webs'
        else:
            fpath = self._webfiles_path + '/webs/' + pterms[1]
        #import pdb; pdb.set_trace()
        return bottle.static_file(fname, root=fpath)
    #end _get_webfiles

    def _create_homepage(self, pkg_list):
        self._homepage_links = {}
        for pkg_name in pkg_list:
            self._extract_http_requests(pkg_name)
        homepage_str = cStringIO.StringIO()

        homepage_str.write("<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Strict//EN\"" +
            " \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd\">" +
            "<html xmlns=\"http://www.w3.org/1999/xhtml\">" +
            "<head>" + 
            "<link href=\"css/style.css\" rel=\"stylesheet\" type=\"text/css\"/>" +
            ("<title>%s</title></head><body>" % self._module))

        homepage_str.write('<h1>Modules for %s</h1>' % (self._module))
        for link in self._homepage_links.iterkeys():
            http_link = '<a href="%s">%s</a><br/>' % (link, link[:link.find('.')])
            homepage_str.write(http_link)
        self._homepage = homepage_str.getvalue()
        homepage_str.close()
    #end _create_homepage

    def _extract_http_requests(self, package):
        try:
            imp_pkg = __import__(package)
        except ImportError:
            self._logger.error('Failed to import package "%s"' % (package))
        else:
            try:
                pkg_path = imp_pkg.__path__
            except AttributeError:
                self._logger.error('Failed to get package [%s] path' % (package))
                return
            for importer, mod, ispkg in \
                pkgutil.walk_packages(path=pkg_path, prefix=imp_pkg.__name__+'.'):
                if not ispkg:
                    if 'http_request' == mod.rsplit('.', 1)[-1]:
                        self._add_http_request_links(pkg_path[0], mod)
    #end _extract_http_requests

    def _add_http_request_links(self, pkg_path, mod):
        try:
            http_module = importlib.import_module(mod)
        except ImportError:
            self._logger.error('Failed to import Module "%s"' % (mod))
        else:
            try:
                http_req_list = getattr(http_module, '_HTTP_REQUEST_LIST')
            except AttributeError:
                self._logger.error('"%s" module does not have http request list' % (mod))
            else:
                # Add the link to the homepage, only if the request list is non-empty
                if len(http_req_list):
                    pkg = mod.rsplit('.', 1)[0]
                    link = pkg.rsplit('.', 1)[-1]+'.xml'
                    sub_path = pkg.split('.', 1)[-1].replace('.', '/')
                    path = pkg_path + '/' + sub_path
                    self._logger.debug('Add [%s:%s] to home page' % (link, path))
                    # TODO: Check for the existence of the html file
                    self._homepage_links[link] = path
                    self._register_http_requests(http_req_list)
    #end _add_http_request_links

    def _register_http_requests(self, http_req_list):
        for req in http_req_list:
            self._logger.debug('Add http request [%s]' % (req['uri']))
            self._http_request_dict[req['uri']] = req['method']
            self._http_app.route(req['uri'], 'GET', self._http_handle_request)
    #end _register_http_requests

    def _http_handle_request(self):
        # Call the handler
        method = self._http_request_dict[bottle.request.path]
        return method(self._sandesh)
    #end _http_handle_request

#end class SandeshHttp
