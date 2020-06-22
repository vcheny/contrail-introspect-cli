#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

import ctypes
import re
import uuid
import netaddr
from TProtocol import *
from  pysandesh.sandesh_logger import SandeshLogger
from pysandesh.util import UTCTimestampUsec
from pysandesh.util import UTCTimestampUsecToString

class TJSONProtocol(TProtocolBase):

  """XML implementation of the Thrift protocol driver."""
  _JSON_BOOL_TRUE = 'true'
  _JSON_BOOL_FALSE = 'false'

  _JSON_TYPENAME_BOOL = 'bool'
  _JSON_TYPENAME_BYTE = 'byte'
  _JSON_TYPENAME_I16 = 'i16'
  _JSON_TYPENAME_I32 = 'i32'
  _JSON_TYPENAME_I64 = 'i64'
  _JSON_TYPENAME_U16 = 'u16'
  _JSON_TYPENAME_U32 = 'u32'
  _JSON_TYPENAME_U64 = 'u64'
  _JSON_TYPENAME_IPV4 = 'ipv4'
  _JSON_TYPENAME_IPADDR = 'ipaddr'
  _JSON_TYPENAME_DOUBLE = 'double'
  _JSON_TYPENAME_UUID = 'uuid_t'
  _JSON_TYPENAME_STRING = 'string'
  _JSON_TYPENAME_XML = 'xml'
  _JSON_TYPENAME_STRUCT = 'struct'
  _JSON_TYPENAME_MAP = 'map'
  _JSON_TYPENAME_SET = 'set'
  _JSON_TYPENAME_LIST = 'list'
  _JSON_TYPENAME_SANDESH = 'sandesh'
  _JSON_TYPENAME_UNKNOWN = 'unknown'

  def __init__(self, trans, strictRead=False, strictWrite=True):
    TProtocolBase.__init__(self, trans)
    sandesh_logger = SandeshLogger('TJSONProtocol')
    self._logger = sandesh_logger.logger()
    self._field_typename_dict = {
      TType.BOOL : self._JSON_TYPENAME_BOOL,
      TType.BYTE : self._JSON_TYPENAME_BYTE,
      TType.I16 : self._JSON_TYPENAME_I16,
      TType.I32 : self._JSON_TYPENAME_I32,
      TType.I64 : self._JSON_TYPENAME_I64,
      TType.U16 : self._JSON_TYPENAME_U16,
      TType.U32 : self._JSON_TYPENAME_U32,
      TType.U64 : self._JSON_TYPENAME_U64,
      TType.IPV4 : self._JSON_TYPENAME_IPV4,
      TType.IPADDR : self._JSON_TYPENAME_IPADDR,
      TType.DOUBLE : self._JSON_TYPENAME_DOUBLE,
      TType.STRING : self._JSON_TYPENAME_STRING,
      TType.STRUCT : self._JSON_TYPENAME_STRUCT,
      TType.MAP : self._JSON_TYPENAME_MAP,
      TType.SET : self._JSON_TYPENAME_SET,
      TType.LIST : self._JSON_TYPENAME_LIST,
      TType.SANDESH : self._JSON_TYPENAME_SANDESH,
      TType.XML : self._JSON_TYPENAME_XML,
      TType.UUID : self._JSON_TYPENAME_UUID,
    }

    self._field_type_dict = {}
    # Now, interchange key and value
    for key, value in self._field_typename_dict.iteritems():
      self._field_type_dict[value] = key

    self._xml_tag = []

    self.field_type_ = []

    self.is_string_begin_ = False

    self.is_list_elem_string_ = False

    # could be one of list(0), struct(1), map(2)
    self.current_sandesh_context_ = []

    # This field will be similar to the above,
    # but holds whether we are processing
    # first element or not
    self.is_first_element_list_ = []

    # Holds whether container is primitive or not
    # For map we concern ourselves only with keys
    # This is relevant only for maps and list
    # For struct we create an entry with None
    self.is_primitive_element_list_ = []

    self.in_map_val_context_ = []

    self.is_map_val_primitive_ = []

  def fieldTypeName(self, type):
    try:
      type_name = self._field_typename_dict[type]
    except KeyError:
      type_name = self._JSON_TYPENAME_UNKNOWN
    return type_name

  def fieldType(self, field_name):
    return self._field_type_dict[field_name]

  def formXMLAttr(self, name, value):
    return '%s="%s"' %(name, value)

  # functions to write data

  # private functions
  def writeBuffer(self, data):
    self.trans.write(data)

  # public functions
  def writeMessageBegin(self, name, type, seqid):
    self._logger.error('TJSON Protocol: writeMessageBegin not implemented.')
    return -1

  def writeMessageEnd(self):
    self._logger.error('TJSON Protocol: writeMessageEnd not implemented.')
    return -1

  def writeSandeshBegin(self, name):
    self.current_sandesh_context_.append('SANDESH')
    self.is_first_element_list_.append(True)
    sandesh_begin = '{\"'+name+'\":{'
    self.sandesh_begin_ = True
    self.sandesh_end_ = False
    self.writeBuffer(sandesh_begin)
    self.is_struct_begin_ = True
    self._xml_tag.append(name)
    self.is_primitive_element_list_.append(False)
    return 0

  def writeSandeshEnd(self):
    sandesh_end = '}'
    sandesh_end += ','
    sandesh_end += '\"TIMESTAMP\":'
    sandesh_end += str(UTCTimestampUsec())
    sandesh_end += '}'
    self.writeBuffer(sandesh_end)
    self.current_sandesh_context_.pop()
    self.is_first_element_list_.pop()
    self.is_primitive_element_list_.pop()
    return 0

  def writeStructBegin(self, name):
    struct_begin = ''
    if (len(self.is_first_element_list_) > 0) and \
       (not self.is_first_element_list_[-1]) and \
       (self.current_sandesh_context_[-1] == "LIST"):
        struct_begin += ','
    else:
        self.is_first_element_list_[-1] = False


    struct_begin += '{'
    if(self.current_sandesh_context_[-1] == "SANDESH"):
        struct_begin += '\"STAT_TYPE\":'
        struct_begin += '\"'+name+'\"'
        struct_begin += ','
    self.current_sandesh_context_.append('STRUCT')
    self.is_first_element_list_.append(True)
    self.is_primitive_element_list_.append(None)

    struct_begin += '\"VAL\":'
    struct_begin += '{'
    self._xml_tag.append(name)
    self.writeBuffer(struct_begin)
    return 0

  def writeStructEnd(self):
    name = self._xml_tag.pop()
    struct_end = '}}'
    self.writeBuffer(struct_end)
    # pop the elements from sandesh_context and
    # set the previous context is_first_elemnt t False
    self.current_sandesh_context_.pop()
    self.is_first_element_list_.pop()
    if len(self.is_first_element_list_) > 0:
        self.is_first_element_list_[-1] = False
    self.is_primitive_element_list_.pop()
    return 0

  def writeContainerElementBegin(self):
    elt_begin = ''
    if not self.is_first_element_list_[-1]:
        if self.current_sandesh_context_[-1] == "MAP":
            if not self.in_map_val_context_[-1]:
                elt_begin += ','
        else:
            elt_begin += ','
    else:
        self.is_first_element_list_[-1] = False

    if self.current_sandesh_context_[-1] == "LIST" and self.is_primitive_element_list_[-1]:
        if self.is_list_elem_string_:
            elt_begin += '\"'

    if self.current_sandesh_context_[-1] == "MAP":
        if self.is_primitive_element_list_[-1]:
            elt_begin += '\"'

    self.writeBuffer(elt_begin)
    return 0

  def writeContainerElementEnd(self):
    elt_end = ''
    if self.current_sandesh_context_[-1] == "MAP":
        if self.is_primitive_element_list_[-1]:
            elt_end += '\"'
        if self.in_map_val_context_[-1]:
            self.in_map_val_context_[-1] = False
        else:
            elt_end += ':'
            if self.is_map_val_primitive_[-1]:
                self.in_map_val_context_[-1] = True

    if self.current_sandesh_context_[-1] == "LIST" and self.is_primitive_element_list_[-1]:
        if self.is_list_elem_string_:
            elt_end += '\"'
    self.is_data_map_key_ = False
    self.writeBuffer(elt_end)
    return 0

  def writeFieldBegin(self, name, ftype, iden, annotations):
    field_begin = ''
    if not self.is_first_element_list_[-1]:
        field_begin += ','
    else:
        self.is_first_element_list_[-1] = False
    field_begin += '\"'+name+'\"'
    field_begin += ':{'
    field_begin += '\"TYPE\":\"'
    field_begin += self.fieldTypeName(ftype)
    field_begin += '\"'
    field_begin += ','
    self.field_type_.append(ftype)
    if len(annotations) > 0:
        field_begin += "\"ANNOTATION\":{"
        for k,v in annotations.items():
            field_begin += '\"'+k+'\"'
            field_begin += ':'
            field_begin += '\"'+v+'\"'
            field_begin += ','
        field_begin = field_begin[:-1]
        field_begin += '}'
        field_begin += ','
    field_begin += '\"VAL\":'
    if self.fieldTypeName(ftype) in [self._JSON_TYPENAME_STRING, self._JSON_TYPENAME_IPADDR, self._JSON_TYPENAME_UUID, self._JSON_TYPENAME_XML]:
        self.is_string_begin_ = True
        field_begin += '\"'
    self.writeBuffer(field_begin)
    self._xml_tag.append(name)
    return 0

  def writeFieldEnd(self):
    name = self._xml_tag.pop()
    field_end = ''
    if self.is_string_begin_:
        self.is_string_begin_ = False
        field_end += '\"'
    field_end += '}'
    self.writeBuffer(field_end)
    self.field_type_.pop()
    return 0

  def writeFieldStop(self):
    return 0

  def writeMapBegin(self, ktype, vtype, size):
    self.current_sandesh_context_.append('MAP')
    self.is_first_element_list_.append(True)
    map_begin = ''
    map_begin += '{'
    map_begin += '\"VALUE\":'
    map_begin += '\"'
    map_begin += self.fieldTypeName(vtype)
    map_begin += '\"'
    map_begin += ','
    map_begin += '\"VAL\":'
    map_begin += '{'
    self.writeBuffer(map_begin)

    if self.fieldTypeName(ktype) in [ self._JSON_TYPENAME_MAP, self._JSON_TYPENAME_STRUCT, self._JSON_TYPENAME_LIST]:
        self.is_primitive_element_list_.append(False)
    else:
        self.is_primitive_element_list_.append(True)

    if self.fieldTypeName(vtype) in [ self._JSON_TYPENAME_MAP, self._JSON_TYPENAME_STRUCT, self._JSON_TYPENAME_LIST]:
        self.in_non_primitive_map_context_ = True
        self.in_map_val_context_.append(False)
        self.is_map_val_primitive_.append(False)
    else:
        self.is_map_primitive_ = True
        self.in_map_val_context_.append(False)
        self.is_map_val_primitive_.append(True)
        if self.fieldTypeName(vtype) is self._JSON_TYPENAME_STRING:
            self.is_map_val_string_ = True

    self.is_beginning_of_map = True
    self.is_map_begin_ = True
    self.is_map_context_ = True
    return 0

  def writeMapEnd(self):
    map_end = ''
    map_end += '}'
    map_end += '}'
    self.in_map_context_ = True
    self.is_map_primitive_ = False
    self.is_map_val_string_ = False
    self.writeBuffer(map_end)
    self.current_sandesh_context_.pop()
    self.is_first_element_list_.pop()
    if len(self.is_first_element_list_) > 0:
        self.is_first_element_list_[-1] = False
    self.is_primitive_element_list_.pop()
    return 0

  def writeListBegin(self, etype, size):
    list_begin = ''
    if len(self.is_first_element_list_) > 0 and \
       not self.is_first_element_list_[-1] and \
       self.current_sandesh_context_[-1] == "LIST":
        list_begin += ','
    else:
        self.is_first_element_list_[-1] = False
    list_begin += '{'
    self.current_sandesh_context_.append('LIST')
    self.is_first_element_list_.append(True)
    list_begin += '\"VAL\":'
    list_begin += '['
    self.writeBuffer(list_begin)
    if self.fieldTypeName(etype) not in [self._JSON_TYPENAME_STRUCT, self._JSON_TYPENAME_MAP]:
        self.is_primitive_list_begin_ = True
        self.is_first_primitive_list_elem_ = True
        self.is_primitive_element_list_.append(True)
        if self.fieldTypeName(etype) in [self._JSON_TYPENAME_STRING, self._JSON_TYPENAME_IPADDR, self._JSON_TYPENAME_UUID, self._JSON_TYPENAME_XML]:
            self.is_list_elem_string_ = True
        self.in_primitive_list_context_ = True
    else:
        self.in_non_primitive_list_context_ = True
        self.is_primitive_element_list_.append(False)

    return 0

  def writeListEnd(self):
    list_end =''
    list_end += ']'
    list_end += '}'
    self.writeBuffer(list_end)
    self.is_first_primitive_list_elem_ = False
    self.in_non_primitive_list_context_ = False
    self.in_primitive_list_context_ = False
    self.is_list_elem_string_ = False
    self.current_sandesh_context_.pop()
    self.is_first_element_list_.pop()
    if len(self.is_first_element_list_) > 0:
        self.is_first_element_list_[-1] = False
    self.is_primitive_element_list_.pop()
    return 0

  def writeSetBegin(self, etype, size):
    list_begin = ''
    if len(self.is_first_element_list_) > 0 and \
       not self.is_first_element_list_[-1] and \
       self.current_sandesh_context_[-1] == "SET":
        list_begin += ','
    else:
        self.is_first_element_list_[-1] = False
    list_begin += '{'
    self.current_sandesh_context_.append('SET')
    self.is_first_element_list_.append(True)
    list_begin += '\"VAL\":'
    list_begin += '['
    self.writeBuffer(list_begin)
    #self.is_list_begin_list_.append(True)
    if self.fieldTypeName(etype) not in [self._JSON_TYPENAME_STRUCT, self._JSON_TYPENAME_MAP]:
        self.is_primitive_list_begin_ = True
        self.is_first_primitive_list_elem_ = True
        self.is_primitive_element_list_.append(True)
        if self.fieldTypeName(etype) in [self._JSON_TYPENAME_STRING, self._JSON_TYPENAME_IPADDR, self._JSON_TYPENAME_UUID, self._JSON_TYPENAME_XML]:
            self.is_list_elem_string_ = True
        self.in_primitive_list_context_ = True
    else:
        self.in_non_primitive_list_context_ = True
        self.is_primitive_element_list_.append(False)
    return 0

  def writeSetEnd(self):
    set_end =''
    set_end += ']'
    set_end += '}'
    self.writeBuffer(set_end)
    self.is_first_primitive_list_elem_ = False
    self.in_non_primitive_list_context_ = False
    self.in_primitive_list_context_ = False
    self.is_list_elem_string_ = False
    self.current_sandesh_context_.pop()
    self.is_first_element_list_.pop()
    if len(self.is_first_element_list_) > 0:
        self.is_first_element_list_[-1] = False
    self.is_primitive_element_list_.pop()
    return 0

  def writeBool(self, boolean):
    if boolean:
      self.writeBuffer(self._JSON_BOOL_TRUE)
    else:
      self.writeBuffer(self._JSON_BOOL_FALSE)
    return 0

  def writeByte(self, byte):
    try:
      self.writeBuffer(str(ctypes.c_byte(byte).value))
    except TypeError:
      self._logger.error('TJSON Protocol: Invalid byte value %s' % str(byte))
      return -1
    return 0

  def writeI16(self, i16):
    try:
      self.writeBuffer(str(ctypes.c_short(i16).value))
    except TypeError:
      self._logger.error('TJSON Protocol: Invalid i16 value %s' % str(i16))
      return -1
    return 0

  def writeI32(self, i32):
    try:
      self.writeBuffer(str(ctypes.c_int(i32).value))
    except TypeError:
      self._logger.error('TJSON Protocol: Invalid i32 value %s' % str(i32))
      return -1
    return 0

  def writeI64(self, i64):
    try:
      self.writeBuffer(str(ctypes.c_longlong(i64).value))
    except TypeError:
      self._logger.error('TJSON Protocol: Invalid i64 value %s' % str(i64))
      return -1
    return 0

  def writeU16(self, u16):
    try:
      self.writeBuffer(str(ctypes.c_ushort(u16).value))
    except TypeError:
      self._logger.error('TJSON Protocol: Invalid u16 value %s' % str(u16))
      return -1
    return 0

  def writeU32(self, u32):
    try:
      self.writeBuffer(str(ctypes.c_uint(u32).value))
    except TypeError:
      self._logger.error('TJSON Protocol: Invalid u32 value %s' % str(u32))
      return -1
    return 0

  def writeU64(self, u64):
    try:
      self.writeBuffer(str(ctypes.c_ulonglong(u64).value))
    except TypeError:
      self._logger.error('TJSON Protocol: Invalid u64 value %s' % str(u64))
      return -1
    return 0

  def writeIPV4(self, ipv4):
    try:
      self.writeBuffer(str(ctypes.c_uint(ipv4).value))
    except TypeError:
      self._logger.error('TJSON Protocol: Invalid ipv4 value %s' % str(ipv4))
      return -1
    return 0

  def writeIPADDR(self, ipaddr):
    if isinstance(ipaddr, netaddr.IPAddress):
      self.writeBuffer(str(ipaddr))
      return 0
    self._logger.error('TJSON Protocol: Invalid ipaddr value %s' % str(ipaddr))
    return -1

  def writeDouble(self, dub):
    self.writeBuffer(str(dub))
    return 0

  def writeString(self, string):
    try:
        match = re.search('<|>|&|\'|\"', string)
    except TypeError:
        self._logger.error('TJSON Protocol: Invalid string value %s' % str(string))
        return -1
    if match is not None:
      string = string.replace('&', '&amp;')
      string = string.replace("'", '&apos;')
      string = string.replace('<', '&lt;')
      string = string.replace('>', '&gt;')
      string = string.replace('"', '\\"')
    self.writeBuffer(string)
    return 0

  def writeBinary(self, binary):
    self.writeBuffer(binary)
    return 0

  def writeUUID(self, uuid):
    try:
      self.writeBuffer(str(uuid))
    except TypeError:
      self._logger.error('TJSON Protocol: Invalid uuid_t value %s' % str(uuid))
      return -1
    return 0

class TJSONProtocolFactory:
  def __init__(self, strictRead=False, strictWrite=True):
    self.strictRead = strictRead
    self.strictWrite = strictWrite

  def getProtocol(self, trans):
    prot = TJSONProtocol(trans, self.strictRead, self.strictWrite)
    return prot
