#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# sandesh_trace.py 
#

class SandeshTraceRequestRunner(object):
    def __init__(self, sandesh, request_buffer_name, request_context, read_context, request_count):
        self._sandesh = sandesh
        self._req_buf_name = request_buffer_name
        self._req_context = request_context
        self._read_context = read_context
        self._req_count = request_count
        self._read_count = 0
        if self._req_count is None or self._req_count == 0:
            self._req_count = self._sandesh.trace_buffer_size_get(self._req_buf_name)    
        from pysandesh.gen_py.sandesh_trace.ttypes import SandeshTraceTextResponse
        self._sttr = SandeshTraceTextResponse(traces=[])    
    #end __init__         

    # Public functions              
    def Run(self):
        self._sandesh.trace_buffer_read(name = self._req_buf_name, 
                                        read_context = self._read_context,
                                        count = self._req_count,
                                        read_cb = self._TraceRead)
        if self._read_context != "Collector":
            self._sttr.response(context = self._req_context,
                                more = False,
                                sandesh = self._sandesh)
            self._sandesh.trace_buffer_read_done(self._req_buf_name, self._read_context)
    #end Run

    # Private functions
    def _TraceRead(self, trace_sandesh, more):
        self._read_count += 1
        if self._read_context != "Collector":
            self._sttr.traces.append(trace_sandesh.log(trace=True))
            return
        if more == False or self._read_count == self._req_count:
            trace_sandesh.send_trace(context = self._req_context,
                                     more = False,
                                     sandesh = self._sandesh)
        else:
            trace_sandesh.send_trace(context = self._req_context,
                                     more = True,
                                     sandesh = self._sandesh)
    #end _TraceRead

#end class SandeshTraceRequestRunner
