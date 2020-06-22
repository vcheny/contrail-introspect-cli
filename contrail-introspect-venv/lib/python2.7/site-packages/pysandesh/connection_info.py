#
# Copyright (c) 2014 Juniper Networks, Inc. All rights reserved.
#

#
# Connection State 
#

import gevent

from gen_py.process_info.constants import ConnectionTypeNames, \
    ConnectionStatusNames, ProcessStateNames
from gen_py.process_info.ttypes import ConnectionInfo, \
    ProcessStatus, ProcessState, ConnectionStatus

class ConnectionState(object):
    _sandesh = None 
    _connection_map = {}
    _hostname = None 
    _module_id = None
    _instance_id = None
    _conn_status_cb = None
    _uve_type_cls = None
    _uve_data_type_cls = None
    _table = None
    _process_status_cb = None

    @staticmethod
    def _send_uve():
        if not ConnectionState._conn_status_cb:
            return
        state_value = ProcessState.FUNCTIONAL
        description = ''
        if ConnectionState._process_status_cb is not None:
            state_value, description = ConnectionState._process_status_cb()
        conn_infos = ConnectionState._connection_map.values()
        (conn_state_value, conn_description) = \
            ConnectionState._conn_status_cb(conn_infos)
        if (conn_state_value == ProcessState.NON_FUNCTIONAL):
            state_value = conn_state_value
        if description != '':
            description += ' '
        description += conn_description

        process_status = ProcessStatus(
            module_id = ConnectionState._module_id,
            instance_id = ConnectionState._instance_id,
            state = ProcessStateNames[state_value],
            connection_infos = conn_infos,
            description = description)
        uve_data = ConnectionState._uve_data_type_cls(
            name = ConnectionState._hostname,
            process_status = [process_status])
        uve = ConnectionState._uve_type_cls(
                table = ConnectionState._table,
                data = uve_data,
                sandesh = ConnectionState._sandesh)
        uve.send(sandesh = ConnectionState._sandesh)
    #end _send_uve

    @staticmethod
    def init(sandesh, hostname, module_id, instance_id, conn_status_cb,
             uve_type_cls, uve_data_type_cls, table = None,
             process_status_cb = None):
        ConnectionState._sandesh = sandesh
        ConnectionState._hostname = hostname
        ConnectionState._module_id = module_id
        ConnectionState._instance_id = instance_id
        ConnectionState._conn_status_cb = conn_status_cb
        ConnectionState._uve_type_cls = uve_type_cls
        ConnectionState._uve_data_type_cls = uve_data_type_cls
        ConnectionState._table = table
        ConnectionState._process_status_cb = process_status_cb
    #end init

    @staticmethod
    def get_conn_state_cb(conn_infos):
        is_cup = True
        message = ''
        for conn_info in conn_infos:
            if conn_info.status != ConnectionStatusNames[ConnectionStatus.UP]:
                if message == '':
                    message = conn_info.type
                else:
                    message += ', ' + conn_info.type
                if conn_info.name is not None and conn_info.name is not '':
                    message += ':' + conn_info.name
                    message += '[' + str(conn_info.description) + ']'
                is_cup = False
        if is_cup:
            return (ProcessState.FUNCTIONAL, '')
        else:
            message += ' connection down'
            return (ProcessState.NON_FUNCTIONAL, message)
    #end get_conn_state_cb

    @staticmethod     
    def update(conn_type, name, status, server_addrs = [], message = None):
        conn_key = (conn_type, name)
        conn_info = ConnectionInfo(type = ConnectionTypeNames[conn_type],
                                   name = name,
                                   status = ConnectionStatusNames[status],
                                   description = message,
                                   server_addrs = server_addrs)
        if ConnectionState._connection_map.has_key(conn_key):
            if ConnectionStatusNames[status] == ConnectionState._connection_map[conn_key].status and \
                    server_addrs == ConnectionState._connection_map[conn_key].server_addrs and \
                    message == ConnectionState._connection_map[conn_key].description:
		return
        ConnectionState._connection_map[conn_key] = conn_info
        ConnectionState._send_uve()
    #end update

    @staticmethod
    def delete(conn_type, name):
        conn_key = (conn_type, name)
        ConnectionState._connection_map.pop(conn_key, 'None')
        ConnectionState._send_uve()
    #end delete

#end class ConnectionState
