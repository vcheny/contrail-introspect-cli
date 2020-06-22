#
# Copyright (c) 2017 Juniper Networks, Inc. All rights reserved.
#

#
# Ssl Session
#

from gevent import socket
from gevent import ssl

from tcp_session import TcpSession


class SslSession(TcpSession):

    def __init__(self, server, ssl_enable=False, keyfile=None, certfile=None,
                 ca_cert=None):
        super(SslSession, self).__init__(server)
        self._ssl_enable = ssl_enable
        self._keyfile = keyfile
        self._certfile = certfile
        self._ca_cert = ca_cert
    # end __init__

    def connect(self, timeout=None):
        if not self._connected:
            try:
                sock = socket.create_connection(self._server, timeout)
                if not self._ssl_enable:
                    self._socket = sock
                else:
                    self._socket = ssl.wrap_socket(sock, keyfile=self._keyfile,
                        certfile=self._certfile, ca_certs=self._ca_cert,
                        cert_reqs=ssl.CERT_REQUIRED,
                        ssl_version=ssl.PROTOCOL_SSLv23)
            except socket.error as err_msg:
                self._socket = None
                self._handle_event(self.SESSION_ERROR)
                return -1
            else:
                self._connected = True
                self._socket.settimeout(None)
                self._set_socket_options()
                self._handle_event(self.SESSION_ESTABLISHED)
                return 0
        return 0
    # end connect


# end class SslSession
