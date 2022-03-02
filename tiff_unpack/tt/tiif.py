"""
TIIF file parser

@author: David Marqvar (DAM)
@copyright: (C) 2011 Thrane & Thrane A/S
"""

import os
import sys
import struct
from zlib import crc32


TIIF_TYPE_RELEASE_HEADER = 1
TIIF_TYPE_VHEADER = 2
TIIF_TYPE_BINARY_BLOB = 3
TIIF_TYPE_SOFTWARE_BLOB = 4
TIIF_TYPE_VHEADER_BLOB = 5
TIIF_TYPE_EMBEDDED_TIIF = 6
TIIF_TYPE_SIGNATURE = 7
TIIF_TYPE_SERIALIZED_DATA = 8
TIIF_TYPE_RELEASE_NOTES = 9

_tiif_type_names = {
    TIIF_TYPE_RELEASE_HEADER :  "TIIF Release Header",
    TIIF_TYPE_VHEADER :         "TIIF VHeader",
    TIIF_TYPE_BINARY_BLOB :     "Binary Blob",
    TIIF_TYPE_SOFTWARE_BLOB :   "Software Blob",
    TIIF_TYPE_VHEADER_BLOB :    "VHeader Blob",
    TIIF_TYPE_EMBEDDED_TIIF :   "Embedded TIIF",
    TIIF_TYPE_SIGNATURE :       "TIIF Signature",
    TIIF_TYPE_SERIALIZED_DATA : "Serialized Data",
    TIIF_TYPE_RELEASE_NOTES :   "Release Notes",
}

class tiif():
    # see http://wiki.ttnet/bin/view/Technology/ThraneInstallImageFormat#TIIF_Header

    def __init__(self, complete_len):
        tiif_identification_def = b'FIITTIIF' # 8 bytes
        tiif_identification_size = 8
        tiif_header_fields_def = '<IBBHII' # 16 bytes
        tiif_header_fields = ('hdrcrc', 'ver', 'res', 'hdrlen', 'bodylen', 'bodycrc')
        tiif_header_size = 16
        self.debug = None
        self.products = None
        self.content_type = None
        self.content_name = None
        self.content_left = 0
        self.content_crc = 0
        self.content_index = None
        buf = self.eat(tiif_identification_size + tiif_header_size)
        if buf[:8] != tiif_identification_def or len(buf) < tiif_identification_size + tiif_header_size:
            raise Exception('Not a TIIF file [%s]', id)
        self._debug("TIIF IDENTIFICATION detected")
        hdr = buf[8:8 + tiif_header_size]
        self.tiif_header = dict(zip(tiif_header_fields, struct.unpack(tiif_header_fields_def, hdr)))
        self._debug("TIIF Header: ", self.tiif_header)
        if crc32(hdr[4:]) != self.tiif_header['hdrcrc']:
            raise Exception('TIIF HEADER CRC ERRROR: ' + str(self.tiif_header))
        expected_len = self.tiif_header['bodylen'] + tiif_identification_size + tiif_header_size
        if expected_len != complete_len:
            raise Exception('TIIF LENGTH MISMATCH: ' + str(self.tiif_header))

    def _debug(self, text, *a):
        if self.debug == True:
            print(text, *a)

    @property
    def content_type_text(self):
        if self.content_type > 0 and self.content_type <= 9:
            return _tiif_type_names[self.content_type]
        return "UNKNOWN CONTENT TYPE"

    @property
    def content_size(self):
        return self.content_header['bodylen']

    def content_type_unpack(self, buf):
        self._debug("TIIF UNPACKING CONTENT HEADER TYPE %d" % self.content_type)
        if self.content_type == TIIF_TYPE_RELEASE_HEADER:
            release_header_fields_def = '<BBHi36s'  # 44 bytes
            release_header_fields = ('major', 'minor', 'build_number', 'date', 'build_id')
            release_header_size = 44
            if len(buf) != release_header_size:
                raise Exception('TIIF RELEASE HEADER LENGTH MISMATCH: ' + str(self.tiif_header))
            self.content_header_extension = dict(zip(release_header_fields, struct.unpack(release_header_fields_def, buf)))
            self.content_header_extension['build_id'] = self.content_header_extension['build_id'].decode().strip('\0')
        elif self.content_type == TIIF_TYPE_VHEADER:
            # TODO: U8 Format
            pass
        elif self.content_type == TIIF_TYPE_SOFTWARE_BLOB:
            sw_blob_header_fields_def = '<BBH28s'  # 32 bytes
            sw_blob_header_fields = ('major', 'minor', 'build_number', 'build_id')
            sw_blob_header_size = 32
            if len(buf) != sw_blob_header_size:
                raise Exception('TIIF SOFTWARE BLOB HEADER LENGTH MISMATCH: ' + str(self.tiif_header))
            self.content_header_extension = dict(zip(sw_blob_header_fields, struct.unpack(sw_blob_header_fields_def, buf)))
            self.content_header_extension['build_id'] = self.content_header_extension['build_id'].decode().strip('\0')
        elif self.content_type == TIIF_TYPE_VHEADER_BLOB:
            # TODO: Huh?
            pass
        elif self.content_type == TIIF_TYPE_SIGNATURE:
            # TODO: U32 Algorithm ID
            pass
        elif self.content_type == TIIF_TYPE_SERIALIZED_DATA:
            # TODO: U8 Format
            pass

    def next(self):
        content_header_fields_def = '<IHHI16sI'  # 32 bytes
        content_header_fields = ('hdrcrc', 'type', 'hdrlen', 'bodylen', 'name', 'bodycrc')
        content_header_size = 32
        self._debug("TIIF NEXT CONTENT [%d]" % self.content_left)
        if self.content_left != 0:
            raise Exception('CONTENT DATA STILL PRESENT')
        buf = self.eat(content_header_size)
        if len(buf) == 0:
            return None
        if len(buf) < content_header_size:
            raise Exception('TIIF CONTENT HEADER TOO SHORT')
        self.content_header = dict(zip(content_header_fields, struct.unpack(content_header_fields_def, buf)))
        self.content_header_extension = None
        self._debug("TIIF Content Header: ", self.content_header)
        extra = self.content_header['hdrlen'] - content_header_size
        buf += self.eat(extra)
        if len(buf) < self.content_header['hdrlen']:
            raise Exception('TIIF CONTENT HEADER SHORTER THAN SPECIFIED')
        if crc32(buf[4:self.content_header['hdrlen']]) != self.content_header['hdrcrc']:
            raise Exception('TIIF CONTENT HEADER CRC ERRROR: ' + str(self.content_header))
        self.content_type = self.content_header['type']
        self.content_name = self.content_header['name'].decode().strip('\0')
        self.content_left = self.content_header['bodylen']
        self.content_crc = 0
        self.content_type_unpack(buf[content_header_size:]) # unpack the tiif contect header based on the content type
        if self.content_index != None:
            self.content_index += 1
        else:
            self.content_index = 0
        return self.content_type

    def get_content(self, max_read_len=None):
        self._debug("TIIF GET CONTENT [%d, %d]" % (self.content_size, self.content_left))
        if max_read_len == None:
            max_read_len = self.content_left
        buf = self.eat(max_read_len)
        self.content_crc = crc32(buf, self.content_crc)
        self.content_left -= len(buf)
        if self.content_left == 0:
            if self.content_crc != self.content_header['bodycrc']:
                raise Exception('TIIF CONTENT BODY CRC ERRROR: ' + str(self.content_header))
            align = self.content_header['bodylen'] % 4
            if align != 0:
                align = 4 - align
                self.eat(align)
                self._debug('EATING TO ALIGN: ', align)
        return buf

    def release_header_body_unpack(self, buf):
        if self.content_type != TIIF_TYPE_RELEASE_HEADER:
            raise Exception("CONTENT TYPE NOT RELEASE HEADER: " + str(self.content_type))
        self.products = ''
        for line in buf.decode().strip('\0').split("\n"):
            if len(line) == 0:
                return ''
            key, val = line.split('=')
            if key == 'products':
                self.products = val.split(',')

class tiif_file(tiif):
    def __init__(self, filename):
        self.filename = filename
        self.file = None
        self.file = open(self.filename, 'rb')
        tiif.__init__(self, os.path.getsize(self.filename)) # Init base class

    def eat(self, read_len):
        return self.file.read(read_len)

class tiif_buffer(tiif):
    def __init__(self, buffer):
        self.buffer = buffer
        self.buffer_len = len(buffer)
        self.buffer_idx = 0
        tiif.__init__(self, self.buffer_len) # Init base class

    def eat(self, read_len):
        if self.buffer_idx + read_len > self.buffer_len:
            read_len = self.buffer_len - self.buffer_idx
        buf = self.buffer[self.buffer_idx:self.buffer_idx + read_len]
        self.buffer_idx += read_len
        return buf
