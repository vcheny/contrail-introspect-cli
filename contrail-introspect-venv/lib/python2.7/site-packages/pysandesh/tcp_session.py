#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Tcp Session
#

from gevent import socket

class TcpSession(object):

    _MAX_READ_SIZE = 4096

    # session events
    SESSION_ESTABLISHED = 1
    SESSION_ERROR = 2
    SESSION_CLOSE = 3

    def __init__(self, server):
        self._server = server
        self._socket = None
        self._connected = False
    #end __init__

    # Public functions

    def connect(self, timeout=None):
        if not self._connected:
            try:
                self._socket = socket.create_connection(self._server, timeout)
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
    #end connect

    def close(self):
        if self._connected:
            self._socket.close()
            self._connected = False
            self._handle_event(self.SESSION_CLOSE)
    #end close

    def read(self):
        while self._connected:
            try:
                data = self._socket.recv(self._MAX_READ_SIZE)
                if data:
                    self._on_read(data)
                else:
                    self.close()
                    break
            except socket.error as err_msg:
                self.close()
                break
    #end read

    def write(self, data):
        if not self._connected:
            return -1
        try:
            self._socket.sendall(data)
        except socket.error as err_msg:
            self.close()
            return -1
        else:
            return len(data)
    #end write

    # Private functions

    def _set_socket_options(self):
        pass
    #end _set_socket_options

    def _handle_event(self, event):
        pass
    #end _handle_event

    def _on_read(self, read_buf):
        pass
    #end _on_read

#end class TcpSession
