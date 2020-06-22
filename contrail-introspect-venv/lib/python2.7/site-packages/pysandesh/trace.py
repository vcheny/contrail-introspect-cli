#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

#
# Trace
#

import collections
import itertools
    
class TraceBuffer(object):
    def __init__(self, name, size, enable=True): 
        self._name = name 
        self._size = size
        self._enable = enable
        self._seqno = 0
        self._buf = collections.deque(maxlen=self._size)
        # Reserve 0 and max(uint32_t)
        self._kMaxSeqno = ((2 ** 32) - 1) - 1;
        self._kMinSeqno = 1; 
        self._read_context_map = {}
        self._wrap = False
        self._read_index = 0
        self._write_index = 0
    #end __init__
   
    # Public functions
    def TraceOn(self):
        self._enable = True
    #end TraceOn
    
    def TraceOff(self):
        self._enable = False
    #end TraceOff

    def IsTraceOn(self):
        return self._enable
    #end IsTraceOn

    def TraceBufSizeGet(self):
        return self._size 
    #end TraceBufSizeGet

    def TraceWrite(self, entry):     
        # Add the trace to the right
        self._buf.append(entry);
        # Once the trace buffer is wrapped, increment the read index
        if self._wrap:
            self._read_index += 1
            if self._read_index == self._size:
                self._read_index = 0
        # Increment the write_index_ and reset upon reaching trace_buf_size_
        self._write_index += 1
        if self._write_index == self._size:
            self._write_index = 0
            self._wrap = True
        
        # Trace messages could be read in batches instead of reading 
        # the entire trace buffer in one shot. Therefore, trace messages
        # could be added between subsequent read requests. If the 
        # read_index_ [points to the oldest message in the trace buffer] 
        # becomes same as the read index [points to the position in the 
        # trace buffer from where the next trace message should be read] 
        # stored in the read context, then there is no need to remember the
        # read context. 
        for key, value in self._read_context_map.items():
            if value == self._read_index:
                self._read_context_map.pop(key, None)
        # Reset seqno_ if it reaches max value
        self._seqno += 1
        if self._seqno  > self._kMaxSeqno:
            self._seqno = self._kMinSeqno;
        return self._seqno 
    #end TraceWrite

    def TraceRead(self, context, count, read_cb):
        if len(self._buf) == 0:
            return
        # if count = 0, then set equal to the size of _buf
        if count == 0:
            count = len(self._buf)
      
        if context in self._read_context_map:
            # If the read context is present, manipulate the position
            # from where we wanna start
            offset = self._read_context_map[context] - self._read_index
            if not offset > 0:
                offset = self._size + offset
            read_slice_list = list(itertools.islice(self._buf, offset, len(self._buf)))       
            entry_count = 0
            for entry in read_slice_list:
                if entry_count < count:
                    entry_count += 1
                    read_cb(entry, entry != self._buf[-1])
                else:
                    break
        else:
            # Create read context
            self._read_context_map[context] = self._read_index
            entry_count = 0
            for entry in self._buf:
                if entry_count < count:
                    entry_count += 1
                    read_cb(entry, entry != self._buf[-1])
                else:
                    break
         
        # Update the read index in the read context
        offset = self._read_context_map[context] + entry_count;
        if offset >= self._size:
            self._read_context_map[context] = offset - self._size
        else:
            self._read_context_map[context] = offset  
    #end TraceRead 

    def TraceReadDone(self, context):
        self._read_context_map.pop(context, None)
#end class TraceBuffer

class Trace(object):
    def __init__(self):
        self._buffer_map = {}
        self._enable = True
    #end __init__  
   
    # Public functions
    def TraceOn(self):
        self._enable = True 
    #end TraceOn
    
    def TraceOff(self): 
        self._enable = False 
    #end TraceOff
    
    def IsTraceOn(self): 
        return self._enable; 
    #end IsTraceOn
        
    def TraceBufAdd(self, name, size, enable=True):
        # Should we have a default size for the buffer?
        if size == 0:
            return
        if name not in self._buffer_map:
            buffer = TraceBuffer(name, size, enable)
            self._buffer_map[name] = buffer
    #end TraceBufAdd
    
    def TraceBufDelete(self, name):
        self._buffer_map.pop(name, None)
    #end TraceBufDelete

    def TraceBufListGet(self):
        return self._buffer_map.keys()
    #end TraceBufListGet

    def TraceBufOn(self, name):
        if name in self._buffer_map:
            self._buffer_map[name].TraceOn()
    #end TraceBufOn

    def TraceBufOff(self, name):
        if name in self._buffer_map:
            self._buffer_map[name].TraceOff()
    #end TraceBufOff

    def IsTraceBufOn(self, name):
        if name in self._buffer_map:
            return self._buffer_map[name].IsTraceOn()
        else:
            return False
    #end IsTraceBufOn

    def TraceBufSizeGet(self, name):
        if name in self._buffer_map:
            return self._buffer_map[name].TraceBufSizeGet()
        else:
            return 0
    #end TraceBufSizeGet
    
    def TraceWrite(self, name, entry):
        if name in self._buffer_map:
            return self._buffer_map[name].TraceWrite(entry)
    #end TraceWrite    

    def TraceRead(self, name, context, count, read_cb):
        if name in self._buffer_map:
            self._buffer_map[name].TraceRead(context, count, read_cb)
    #end TraceRead

    def TraceReadDone(self, name, context):
        if name in self._buffer_map:
            self._buffer_map[name].TraceReadDone(context) 
    #end TraceReadDone
    
#end class Trace
