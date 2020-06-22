#
# Copyright (c) 2013 Juniper Networks, Inc. All rights reserved.
#

import ctypes
import re
import uuid
import netaddr
from TProtocol import *
from  pysandesh.sandesh_logger import SandeshLogger

class TXMLProtocol(TProtocolBase):

  """XML implementation of the Thrift protocol driver."""

  _XML_TAG_OPEN = '<'
  _XML_TAG_CLOSE = '>'
  _XML_END_TAG = '</'
  _XML_TYPE = 'type'
  _XML_IDENTIFIER = 'identifier'
  _XML_ELEMENT = 'element'
  _XML_KEY = 'key'
  _XML_VALUE = 'value'
  _XML_SIZE = 'size'
  _XML_BOOL_TRUE = 'true'
  _XML_BOOL_FALSE = 'false'
  _XML_CDATA_OPEN = '<![CDATA['
  _XML_CDATA_CLOSE = ']]>'

  _XML_TYPENAME_BOOL = 'bool'
  _XML_TYPENAME_BYTE = 'byte'
  _XML_TYPENAME_I16 = 'i16'
  _XML_TYPENAME_I32 = 'i32'
  _XML_TYPENAME_I64 = 'i64'
  _XML_TYPENAME_U16 = 'u16'
  _XML_TYPENAME_U32 = 'u32'
  _XML_TYPENAME_U64 = 'u64'
  _XML_TYPENAME_IPV4 = 'ipv4'
  _XML_TYPENAME_IPADDR = 'ipaddr'
  _XML_TYPENAME_DOUBLE = 'double'
  _XML_TYPENAME_UUID = 'uuid_t'
  _XML_TYPENAME_STRING = 'string'
  _XML_TYPENAME_XML = 'xml'
  _XML_TYPENAME_STRUCT = 'struct'
  _XML_TYPENAME_MAP = 'map'
  _XML_TYPENAME_SET = 'set'
  _XML_TYPENAME_LIST = 'list'
  _XML_TYPENAME_SANDESH = 'sandesh'
  _XML_TYPENAME_UNKNOWN = 'unknown'

  def __init__(self, trans, strictRead=False, strictWrite=True):
    TProtocolBase.__init__(self, trans)
    sandesh_logger = SandeshLogger('TXMLProtocol')
    self._logger = sandesh_logger.logger()
    self._field_typename_dict = {
      TType.BOOL : self._XML_TYPENAME_BOOL,
      TType.BYTE : self._XML_TYPENAME_BYTE,
      TType.I16 : self._XML_TYPENAME_I16,
      TType.I32 : self._XML_TYPENAME_I32,
      TType.I64 : self._XML_TYPENAME_I64,
      TType.U16 : self._XML_TYPENAME_U16,
      TType.U32 : self._XML_TYPENAME_U32,
      TType.U64 : self._XML_TYPENAME_U64,
      TType.IPV4 : self._XML_TYPENAME_IPV4,
      TType.IPADDR : self._XML_TYPENAME_IPADDR,
      TType.DOUBLE : self._XML_TYPENAME_DOUBLE,
      TType.STRING : self._XML_TYPENAME_STRING,
      TType.STRUCT : self._XML_TYPENAME_STRUCT,
      TType.MAP : self._XML_TYPENAME_MAP,
      TType.SET : self._XML_TYPENAME_SET,
      TType.LIST : self._XML_TYPENAME_LIST,
      TType.SANDESH : self._XML_TYPENAME_SANDESH,
      TType.XML : self._XML_TYPENAME_XML,
      TType.UUID : self._XML_TYPENAME_UUID,
    }

    self._field_type_dict = {}
    # Now, interchange key and value
    for key, value in self._field_typename_dict.iteritems():
      self._field_type_dict[value] = key

    self._xml_tag = []

  def fieldTypeName(self, type):
    try:
      type_name = self._field_typename_dict[type]
    except KeyError:
      type_name = self._XML_TYPENAME_UNKNOWN
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
    self._logger.error('TXML Protocol: writeMessageBegin not implemented.')
    return -1

  def writeMessageEnd(self):
    self._logger.error('TXML Protocol: writeMessageEnd not implemented.')
    return -1

  def writeSandeshBegin(self, name):
    sandesh_begin = '<%s %s>' %(name, self.formXMLAttr(self._XML_TYPE,
        self._XML_TYPENAME_SANDESH))
    self.writeBuffer(sandesh_begin)
    self._xml_tag.append(name)
    return 0

  def writeSandeshEnd(self):
    name = self._xml_tag.pop()
    sandesh_end = '</%s>' %(name)
    self.writeBuffer(sandesh_end)
    return 0

  def writeStructBegin(self, name):
    struct_begin = '<%s>' %(name)
    self._xml_tag.append(name)
    self.writeBuffer(struct_begin)
    return 0

  def writeStructEnd(self):
    name = self._xml_tag.pop()
    struct_end = '</%s>' %(name)
    self.writeBuffer(struct_end)
    return 0

  def writeContainerElementBegin(self):
    elt_begin = '<%s>' %(self._XML_ELEMENT)
    self.writeBuffer(elt_begin)
    return 0

  def writeContainerElementEnd(self):
    elt_end = '</%s>' %(self._XML_ELEMENT)
    self.writeBuffer(elt_end)
    return 0

  def writeFieldBegin(self, name, ftype, iden, annotations):
    field_begin = '<%s %s %s' %(name,
        self.formXMLAttr(self._XML_TYPE, self.fieldTypeName(ftype)),
        self.formXMLAttr(self._XML_IDENTIFIER, str(iden)))
    for akey, avalue in annotations.iteritems():
      field_begin += ' %s' %(self.formXMLAttr(akey, avalue))
    field_begin += '>'
    self.writeBuffer(field_begin)
    self._xml_tag.append(name)
    return 0

  def writeFieldEnd(self):
    name = self._xml_tag.pop()
    field_end = '</%s>' %(name)
    self.writeBuffer(field_end)
    return 0

  def writeFieldStop(self):
    return 0

  def writeMapBegin(self, ktype, vtype, size):
    map_begin = '<%s %s %s %s>' %(self._XML_TYPENAME_MAP,
        self.formXMLAttr(self._XML_KEY, self.fieldTypeName(ktype)),
        self.formXMLAttr(self._XML_VALUE, self.fieldTypeName(vtype)),
        self.formXMLAttr(self._XML_SIZE, str(size)))
    self.writeBuffer(map_begin)
    return 0

  def writeMapEnd(self):
    map_end = '</%s>' %(self._XML_TYPENAME_MAP)
    self.writeBuffer(map_end)
    return 0

  def writeListBegin(self, etype, size):
    list_begin = '<%s %s %s>' %(self._XML_TYPENAME_LIST,
        self.formXMLAttr(self._XML_TYPE, self.fieldTypeName(etype)),
        self.formXMLAttr(self._XML_SIZE, str(size)))
    self.writeBuffer(list_begin)
    return 0

  def writeListEnd(self):
    list_end = '</%s>' %(self._XML_TYPENAME_LIST)
    self.writeBuffer(list_end)
    return 0

  def writeSetBegin(self, etype, size):
    set_begin = '<%s %s %s>' %(self._XML_TYPENAME_SET,
        self.formXMLAttr(self._XML_TYPE, self.fieldTypeName(etype)),
        self.formXMLAttr(self._XML_SIZE, str(size)))
    self.writeBuffer(set_begin)
    return 0

  def writeSetEnd(self):
    set_end = '</%s>' %(self._XML_TYPENAME_SET)
    self.writeBuffer(set_end)
    return 0

  def writeBool(self, boolean):
    if boolean:
      self.writeBuffer(self._XML_BOOL_TRUE)
    else:
      self.writeBuffer(self._XML_BOOL_FALSE)
    return 0

  def writeByte(self, byte):
    try:
      self.writeBuffer(str(ctypes.c_byte(byte).value))
    except TypeError:
      self._logger.error('TXML Protocol: Invalid byte value %s' % str(byte))
      return -1
    return 0

  def writeI16(self, i16):
    try:
      self.writeBuffer(str(ctypes.c_short(i16).value))
    except TypeError:
      self._logger.error('TXML Protocol: Invalid i16 value %s' % str(i16))
      return -1
    return 0

  def writeI32(self, i32):
    try:
      self.writeBuffer(str(ctypes.c_int(i32).value))
    except TypeError:
      self._logger.error('TXML Protocol: Invalid i32 value %s' % str(i32))
      return -1
    return 0

  def writeI64(self, i64):
    try:
      self.writeBuffer(str(ctypes.c_longlong(i64).value))
    except TypeError:
      self._logger.error('TXML Protocol: Invalid i64 value %s' % str(i64))
      return -1
    return 0

  def writeU16(self, u16):
    try:
      self.writeBuffer(str(ctypes.c_ushort(u16).value))
    except TypeError:
      self._logger.error('TXML Protocol: Invalid u16 value %s' % str(u16))
      return -1
    return 0

  def writeU32(self, u32):
    try:
      self.writeBuffer(str(ctypes.c_uint(u32).value))
    except TypeError:
      self._logger.error('TXML Protocol: Invalid u32 value %s' % str(u32))
      return -1
    return 0

  def writeU64(self, u64):
    try:
      self.writeBuffer(str(ctypes.c_ulonglong(u64).value))
    except TypeError:
      self._logger.error('TXML Protocol: Invalid u64 value %s' % str(u64))
      return -1
    return 0

  def writeIPV4(self, ipv4):
    try:
      self.writeBuffer(str(ctypes.c_uint(ipv4).value))
    except TypeError:
      self._logger.error('TXML Protocol: Invalid ipv4 value %s' % str(ipv4))
      return -1
    return 0

  def writeIPADDR(self, ipaddr):
    if isinstance(ipaddr, netaddr.IPAddress):
      self.writeBuffer(str(ipaddr))
      return 0
    self._logger.error('TXML Protocol: Invalid ipaddr value %s' % str(ipaddr))
    return -1

  def writeDouble(self, dub):
    self.writeBuffer(str(dub))
    return 0

  def writeString(self, string):
    try:
        match = re.search('<|>|&|\'|\"', string)
    except TypeError:
        self._logger.error('TXML Protocol: Invalid string value %s' % str(string))
        return -1
    if match is not None:
      string = string.replace('&', '&amp;')
      string = string.replace("'", '&apos;')
      string = string.replace('<', '&lt;')
      string = string.replace('>', '&gt;')
    self.writeBuffer(string)
    return 0

  def writeBinary(self, binary):
    self.writeBuffer(binary)
    return 0

  def writeXML(self, xml):
    self.writeBuffer(self._XML_CDATA_OPEN)
    self.writeBuffer(xml)
    self.writeBuffer(self._XML_CDATA_CLOSE)
    return 0

  def writeUUID(self, uuid):
    try:
      self.writeBuffer(str(uuid))
    except TypeError:
      self._logger.error('TXML Protocol: Invalid uuid_t value %s' % str(uuid))
      return -1
    return 0
    
  class XMLReader:

    """XML Reader implementation."""

    def __init__(self, trans):
      self._trans = trans
      sandesh_logger = SandeshLogger('XMLReader')
      self._logger = sandesh_logger.logger()
      self._read_buf = self._trans.getvalue()
      assert self._read_buf, 'XMLReader: No data to read'

    def readXMLTag(self, end_tag):
      if end_tag:
        tag_start = TXMLProtocol._XML_END_TAG
      else:
        tag_start = TXMLProtocol._XML_TAG_OPEN
      if tag_start != self._read_buf[:len(tag_start)]:
        self._logger.error('XMLReader: XML open tag not found.')
        return (None, None)
      # find the position of _XML_TAG_CLOSE
      tag_end_pos = self._read_buf.find(TXMLProtocol._XML_TAG_CLOSE)
      if -1 == tag_end_pos:
        self._logger.error('XMLReader: XML close tag not found.')
        return (None, None)
      # extract the tag - exclude _XML_TAG_OPEN and _XML_TAG_CLOSE
      tag = self._read_buf[len(tag_start):tag_end_pos]
      # move the position of _read_buf - account for '>'
      offset = tag_end_pos + 1
      self._read_buf = self._read_buf[offset:]
      return (tag, offset)

    def readXMLValue(self):
      val_end_pos = self._read_buf.find(TXMLProtocol._XML_TAG_OPEN)
      if -1 == val_end_pos:
        self._logger.error('XMLReader: XML open tag not found. \
            Failed to read XML Value.')
        return (None, None)
      val = self._read_buf[:val_end_pos]
      # move the position of _read_buf
      self._read_buf = self._read_buf[val_end_pos:]
      return (val, val_end_pos)

    def peekXMLTag(self, num_bytes):
      if len(self._read_buf) < num_bytes:
        self._logger.error('XMLReader: Not enough data to peek.')
        return None
      return self._read_buf[:num_bytes]
  
    def readXMLCDATA(self):
      if TXMLProtocol._XML_CDATA_OPEN != self._read_buf[:len(TXMLProtocol._XML_CDATA_OPEN)]:
        self._logger.error('XMLReader: XML CDATA open tag not found.')
        return (None, None)
      # find the position of _XML_CDATA_CLOSE
      end_pos = self._read_buf.find(TXMLProtocol._XML_CDATA_CLOSE)
      if -1 == end_pos:
        self._logger.error('XMLReader: XML CDATA close tag not found.')
        return (None, None)
      # extract the data - exclude the _XML_CDATA_OPEN
      data = self._read_buf[len(TXMLProtocol._XML_CDATA_OPEN):end_pos]
      # move the position of _read_buf - account for '_XML_CDATA_CLOSE'
      offset = end_pos + len(TXMLProtocol._XML_CDATA_CLOSE)
      self._read_buf = self._read_buf[offset:]
      return (data, offset)  

  #end class XMLReader

  def extractXMLTagName(self, tag):
    tag_name_end_pos = tag.find(' ')
    if -1 == tag_name_end_pos:
      self._logger.error('TXML Protocol: Failed to extract XML tag name.')
      return (None, None)
    return (tag[:tag_name_end_pos], tag_name_end_pos)

  def extractXMLAttr(self, tag):
    name_end_pos = tag.find('=')
    if -1 == name_end_pos:
      self._logger.error('TXML Protocol: Failed to extract XML attribute.')
      return (None, None, None)
    name = tag[:name_end_pos]
    # account for '="'
    offset = name_end_pos + 2
    val_end_pos = tag[offset:].find('"')
    if -1 == val_end_pos:
      self._logger.error('TXML Protocol: Failed to extract XML attribute.')
      return (None, None, None)
    val = tag[offset:offset+val_end_pos]
    # account for '"'
    offset = offset + val_end_pos + 1
    return (name, val, offset)

  def validateXMLAttr(self, exp_name, exp_val, act_name, act_val):
    if exp_name != act_name:
      self._logger.error('TXML Protocol: XML attribute validation failed. \
          Expected attribute name "%s"; Actual attribute name "%s".' %(exp_name, act_name))
      return False
    if exp_val != act_val:
      self._logger.error('TXML Protocol: XML attribute validation failed. \
          Expected attribute value "%s"; Actual attribute value "%s".' %(exp_val, act_val))
      return False
    return True

  # functions to read data

  def readMessageBegin(self):
    self._logger.error('TXML Protocol: readMessageBegin not implemented.')
    return -1

  def readMessageEnd(self):
    self._logger.error('TXML Protocol: readMessageEnd not implemented.')
    return -1

  def readSandeshBegin(self):
    try:
      (tag, length) = self._xml_reader.readXMLTag(False)
    except:
      self._xml_reader = self.XMLReader(self.trans)
      (tag, length) = self._xml_reader.readXMLTag(False)
    if tag is None:
      return (-1, None)

    (sandesh_name, offset) = self.extractXMLTagName(tag)
    if sandesh_name is None:
      return (-1, None)
    # append sandesh name to the _xml_tag list for verification @
    # readSandeshEnd()
    self._xml_tag.append(sandesh_name)
    # account for ' '
    tag = tag[offset+1:]
    (name, value, offset) = self.extractXMLAttr(tag)
    ret = self.validateXMLAttr(self._XML_TYPE, self._XML_TYPENAME_SANDESH,
        name, value)
    if False == ret:
      return (-1, None)
    return (length, sandesh_name)

  def readSandeshEnd(self):
    (sandesh_name_end, length) = self._xml_reader.readXMLTag(True)
    sandesh_name_begin = self._xml_tag.pop()
    if sandesh_name_begin != sandesh_name_end:
      self._logger.error('TXML Protocol: Sandesh name "<%s> </%s>" mismatch.' \
          %(sandesh_name_begin, sandesh_name_end))
      return -1
    return length

  def readStructBegin(self):
    try:
      (struct_begin, length) = self._xml_reader.readXMLTag(False)
    except:
      self._xml_reader = self.XMLReader(self.trans)
      (struct_begin, length) = self._xml_reader.readXMLTag(False)
      if struct_begin is None:
        return -1
    self._xml_tag.append(struct_begin)
    return length

  def readStructEnd(self):
    (struct_end, length) = self._xml_reader.readXMLTag(True)
    struct_begin = self._xml_tag.pop()
    if struct_begin != struct_end:
      self._logger.error('TXML Protocol: struct name "<%s> </%s>" mismatch.' \
          %(struct_begin, struct_end))
      return -1
    return length

  def readContainerElementBegin(self):
    (elt_begin, length) = self._xml_reader.readXMLTag(False)
    if elt_begin is None:
      return -1
    return length

  def readContainerElementEnd(self):
    (elt_end, length) = self._xml_reader.readXMLTag(True)
    if elt_end is None:
      return -1
    return length

  def readFieldBegin(self):
    field_stop = self._xml_reader.peekXMLTag(len(self._XML_END_TAG))
    if field_stop is None:
      return (-1, None, None, None)
    if field_stop == self._XML_END_TAG:
      return (0, None, TType.STOP, None)
    (tag, length) = self._xml_reader.readXMLTag(False)
    if tag is None:
      return (-1, None, None, None)
    (field_name, offset) = self.extractXMLTagName(tag)
    if field_name is None:
      return (-1, None, None, None)
    self._xml_tag.append(field_name)
    # account for ' '
    tag = tag[offset+1:]
    (fname, ftype_str, offset) = self.extractXMLAttr(tag)
    if fname is None:
      return (-1, field_name, None, None)
    if self._XML_TYPE != fname:
      self._logger.error('TXML Protocol: Expected field name "%s"; Actual field name "%s".' \
          %(self._XML_TYPE, fname))
      return (-1, field_name, None, None)
    ftype = self.fieldType(ftype_str)
    # account for ' '
    tag = tag[offset+1:]
    (fname, fid_str, offset) = self.extractXMLAttr(tag)
    if fname is None:
      return (-1, field_name, ftype, None)
    if self._XML_IDENTIFIER != fname:
      self._logger.error('TXML Protocol: Expected field name "%s"; Actual field name "%s".' \
          %(self._XML_IDENTIFIER, fname))
      return (-1, field_name, ftype, None)
    try:
      fid = int(fid_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid field id "%s".' %(fid_str))
      return (-1, field_name, ftype, None)
    return (length, field_name, ftype, fid)

  def readFieldEnd(self):
    (field_end, length) = self._xml_reader.readXMLTag(True)
    if field_end is None:
      return -1
    field_begin = self._xml_tag.pop()
    if field_begin != field_end:
      self._logger.error('TXML Protocol: field name "<%s> </%s>" mismatch' \
          %(field_begin, field_end))
      return -1
    return length

  def readMapBegin(self):
    (tag, length) = self._xml_reader.readXMLTag(False)
    if tag is None:
      return (-1, None, None, None)
    (map_name, offset) = self.extractXMLTagName(tag)
    if map_name is None:
      return (-1, None, None, None)
    if self._XML_TYPENAME_MAP != map_name:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s"' \
          %(self._XML_TYPENAME_MAP, map_name))
      return (-1, None, None, None)
    # account for ' '
    tag = tag[offset+1:]
    (kname, ktype_str, offset) = self.extractXMLAttr(tag)
    if kname is None:
      return (-1, None, None, None)
    if self._XML_KEY != kname:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s"' \
          %(self._XML_KEY, kname))
      return (-1, None, None, None)
    ktype = self.fieldType(ktype_str)
    # account for ' '
    tag = tag[offset+1:]
    (vname, vtype_str, offset) = self.extractXMLAttr(tag)
    if vname is None:
      return (-1, ktype, None, None)
    if self._XML_VALUE != vname:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s"' \
          %(self._XML_VALUE, vname))
      return (-1, ktype, None, None)
    vtype = self.fieldType(vtype_str)
    # account for ' '
    tag = tag[offset+1:]
    (sname, size_str, offset) = self.extractXMLAttr(tag)
    if sname is None:
      return (-1, ktype, vtype, None)
    if self._XML_SIZE != sname:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s"' \
          %(self._XML_SIZE, sname))
      return (-1, ktype, vtype, None)
    try:
      size = int(size_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid map size "%s"' %(size_str))
      return (-1, ktype, vtype, None)
    return (length, ktype, vtype, size)

  def readMapEnd(self):
    (map_end, length) = self._xml_reader.readXMLTag(True)
    if map_end is None:
      return -1
    if (self._XML_TYPENAME_MAP != map_end):
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s"' \
          %(self._XML_TYPENAME_MAP, map_end))
      return -1
    return length

  def readListBegin(self):
    (tag, length) = self._xml_reader.readXMLTag(False)
    if tag is None:
      return (-1, None, None)
    (list_name, offset) = self.extractXMLTagName(tag)
    if list_name is None:
      return (-1, None, None)
    if self._XML_TYPENAME_LIST != list_name:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s".' \
          %(self._XML_TYPENAME_LIST, list_name))
      return (-1, None, None)
    # account for ' '
    tag = tag[offset+1:]
    (kname, etype_str, offset) = self.extractXMLAttr(tag)
    if kname is None:
      return (-1, None, None)
    if self._XML_TYPE != kname:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s".' \
          %(self._XML_TYPE, kname))
      return (-1, None, None)
    etype = self.fieldType(etype_str)
    # account for ' '
    tag = tag[offset+1:]
    (sname, size_str, offset) = self.extractXMLAttr(tag)
    if sname is None:
      return (-1, etype, None)
    if self._XML_SIZE != sname:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s".' \
          %(self._XML_SIZE, sname))
      return (-1, etype, None)
    try:
      size = int(size_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid list size "%s".' %(size_str))
      return (-1, etype, None)
    return (length, etype, size)

  def readListEnd(self):
    (list_end, length) = self._xml_reader.readXMLTag(True)
    if list_end is None:
      return -1
    if self._XML_TYPENAME_LIST != list_end:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s".' \
          %(self._XML_TYPENAME_LIST, list_end))
      return -1
    return length

  def readSetBegin(self):
    (tag, length) = self._xml_reader.readXMLTag(False)
    if tag is None:
      return (-1, None, None)
    (set_name, offset) = self.extractXMLTagName(tag)
    if set_name is None:
      return (-1, None, None)
    if self._XML_TYPENAME_SET != set_name:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s".' \
          %(self._XML_TYPENAME_SET, set_name))
      return (-1, None, None)
    # account for ' '
    tag = tag[offset+1:]
    (kname, etype_str, offset) = self.extractXMLAttr(tag)
    if kname is None:
      return (-1, None, None)
    if self._XML_TYPE != kname:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s".' \
          %(self._XML_TYPE, kname))
      return (-1, None, None)
    etype = self.fieldType(etype_str)
    # account for ' '
    tag = tag[offset+1:]
    (sname, size_str, offset) = self.extractXMLAttr(tag)
    if sname is None:
      return (-1, etype, None)
    if self._XML_SIZE != sname:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s".' \
          %(self._XML_SIZE, sname))
      return (-1, etype, None)
    try:
      size = int(size_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid set size "%s".' %(size_str))
      return (-1, etype, None)
    return (length, etype, size)

  def readSetEnd(self):
    (set_end, length) = self._xml_reader.readXMLTag(True)
    if set_end is None:
      return -1
    if self._XML_TYPENAME_SET != set_end:
      self._logger.error('TXML Protocol: Expected "%s"; Actual "%s".' \
          %(self._XML_TYPENAME_SET, set_end))
      return -1
    return length

  def readBool(self):
    (bool_str, length) = self._xml_reader.readXMLValue()
    if bool_str is None:
      return (-1, None)
    if self._XML_BOOL_TRUE == bool_str:
      return (length, True)
    elif self._XML_BOOL_FALSE == bool_str:
      return (length, False)
    else:
      self._logger.error('TXML Protocol: Invalid boolean value "%s"' %(bool_str))
      return (-1, None)

  def readByte(self):
    (byte_str, length) = self._xml_reader.readXMLValue()
    if byte_str is None:
      return (-1, None)
    try:
      byte = int(byte_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid byte value "%s"' %(byte_str))
      return (-1, None)
    return (length, byte)

  def readI16(self):
    (i16_str, length) = self._xml_reader.readXMLValue()
    if i16_str is None:
      return (-1, None)
    try:
      i16 = int(i16_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid i16 value "%s".' %(i16_str))
      return (-1, None)
    return (length, i16)

  def readI32(self):
    (i32_str, length) = self._xml_reader.readXMLValue()
    if i32_str is None:
      return (-1, None)
    try:
      i32 = int(i32_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid i32 value "%s".' %(i32_str))
      return (-1, None)
    return (length, i32)

  def readI64(self):
    (i64_str, length) = self._xml_reader.readXMLValue()
    if i64_str is None:
      return (-1, None)
    try:
      i64 = int(i64_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid i64 value "%s".' %(i64_str))
      return (-1, None)
    return (length, i64)

  def readU16(self):
    (u16_str, length) = self._xml_reader.readXMLValue()
    if u16_str is None:
      return (-1, None)
    try:
      u16 = int(u16_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid u16 value "%s".' %(u16_str))
      return (-1, None)
    return (length, u16)

  def readU32(self):
    (u32_str, length) = self._xml_reader.readXMLValue()
    if u32_str is None:
      return (-1, None)
    try:
      u32 = int(u32_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid u32 value "%s".' %(u32_str))
      return (-1, None)
    return (length, u32)

  def readU64(self):
    (u64_str, length) = self._xml_reader.readXMLValue()
    if u64_str is None:
      return (-1, None)
    try:
      u64 = int(u64_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid u64 value %s' %(u64_str))
      return (-1, None)
    return (length, u64)

  def readIPV4(self):
    (ipv4_str, length) = self._xml_reader.readXMLValue()
    if ipv4_str is None:
      return (-1, None)
    try:
      ipv4 = int(ipv4_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid ipv4 value %s' %(ipv4_str))
      return (-1, None)
    return (length, ipv4)

  def readIPADDR(self):
    (ipaddr_str, length) = self._xml_reader.readXMLValue()
    if ipaddr_str is None:
      return (-1, None)
    try:
      ipaddr = netaddr.IPAddress(ipaddr_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid ipaddr value %s' \
                         % (ipaddr_str))
      return (-1, None)
    return (length, ipaddr)

  def readDouble(self):
    (doub_str, length) = self._xml_reader.readXMLValue()
    if doub_str is None:
      return (-1, None)
    try:
      doub = float(doub_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid double value "%s".' %(doub_str))
      return (-1, None)
    return (length, doub)

  def readString(self):
    (string, length) = self._xml_reader.readXMLValue()
    if string is None:
      return (-1, None)
    string = string.replace('&amp;', '&')
    string = string.replace('&apos;', "'")
    string = string.replace('&lt;', '<')
    string = string.replace('&gt;', '>')
    return (len(string), string)

  def readBinary(self):
    (binary, length) = self._xml_reader.readXMLValue()
    if binary is None:
      return (-1, None)
    return (length, binary)

  def readXML(self):
    (xml, length) = self._xml_reader.readXMLCDATA()
    if xml is None:
      return (-1, None)
    return (len(xml), xml)      

  def readUUID(self):
    (uuid_str, length) = self._xml_reader.readXMLValue()
    if uuid_str is None:
      return (-1, None)
    try:
      uuid_temp = uuid.UUID(uuid_str)
    except ValueError:
      self._logger.error('TXML Protocol: Invalid uuid_t value "%s".' %(uuid_str))
      return (-1, None)
    return (length, uuid_temp)

class TXMLProtocolFactory:
  def __init__(self, strictRead=False, strictWrite=True):
    self.strictRead = strictRead
    self.strictWrite = strictWrite

  def getProtocol(self, trans):
    prot = TXMLProtocol(trans, self.strictRead, self.strictWrite)
    return prot
