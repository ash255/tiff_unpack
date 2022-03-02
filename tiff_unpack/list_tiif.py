"""
Help functions for listing contents of a TIIF file

@author: David Marqvar (DAM)
@copyright: (C) 2011 Thrane & Thrane A/S
"""

import sys
import os
import time
import tt.tiif

def print_debug(debug, text, *a, end='\n'):
    if debug == True:
        print(text, *a, end=end)

tiif_release_headers = dict()

def list_tiif_line(t, debug=False, level=0):
    indent = 24 - level*2
    while level:
        print('  ', end='')
        level -= 1
    print("{0:{1}} {2:24} ".format(t.content_name, indent, t.content_type_text), end='')
    if t.content_size < 1024*1024*9:
        print("{:4}k ".format(int(t.content_size/1024)), end='')
    else:
        print("{:4}M ".format(int(t.content_size/(1024*1024))), end='')
    if t.content_type == tt.tiif.TIIF_TYPE_RELEASE_HEADER:
        version = "%2d.%02d-%d" % (t.content_header_extension['major'], t.content_header_extension['minor'], t.content_header_extension['build_number'])
        if t.products != None:
            products = ', '.join(t.products)
        else:
            products = ''
        date = time.asctime(time.gmtime(t.content_header_extension['date'])) + " UTC"
        print("%-10s %-36s %s    '%s'" % (version, t.content_header_extension['build_id'], date, products))
    elif t.content_type == tt.tiif.TIIF_TYPE_SOFTWARE_BLOB:
        version = "%2d.%02d-%d" % (t.content_header_extension['major'], t.content_header_extension['minor'], t.content_header_extension['build_number'])
        print("%-10s %-36s" % (version, t.content_header_extension['build_id']))
    else:
        print('')

def manifest_write(t, file, str):
    file.write("%d: %s: %s\n" % (t.content_index, t.content_type_text.replace(' ','_'), str))

def unpack_save_manifest(t, unpack_dir, debug=False):
    filename = os.path.join(unpack_dir, 'manifest')
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    print_debug(debug, "Saving manifest for part #%d %s" % (t.content_index, filename))
    if t.content_index == 0:
        file = open(filename, 'w')
    else:
        file = open(filename, 'a')
    if t.content_type == tt.tiif.TIIF_TYPE_RELEASE_HEADER:
        manifest_write(t, file, "name: %s" % t.content_name)
        manifest_write(t, file, "version: %d.%02d-%d" % (t.content_header_extension['major'], t.content_header_extension['minor'], t.content_header_extension['build_number']))
        manifest_write(t, file, "build_id: %s" % t.content_header_extension['build_id'])
        manifest_write(t, file, "date: %s" % time.asctime(time.gmtime(t.content_header_extension['date'])))
        if t.products != None:
            manifest_write(t, file, "products: %s" % t.products)
    elif t.content_type == tt.tiif.TIIF_TYPE_SOFTWARE_BLOB:
        manifest_write(t, file, "version: %d.%02d-%d" % (t.content_header_extension['major'], t.content_header_extension['minor'], t.content_header_extension['build_number']))
        manifest_write(t, file, "build_id: %s" % t.content_header_extension['build_id'])
    manifest_write(t, file, "crc: %s" % t.content_crc)
    file.close()

def unpack_save_file(t, content, unpack_dir, debug=False):
    if (t.content_type == tt.tiif.TIIF_TYPE_RELEASE_HEADER or
        t.content_type == tt.tiif.TIIF_TYPE_EMBEDDED_TIIF):
        print_debug(debug, "Skipping part #%d due to content type: %s" % (t.content_index, t.content_type_text))
    else:
        filename = os.path.join(unpack_dir, t.content_name.replace(' ','_'))
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
        print_debug(debug, "Unpacking part #%d %s, %d" % (t.content_index, filename, len(content)))
        file = open(filename, 'wb')
        file.write(content)
        file.close()

def list_tiif_recursive(t, name, debug=False, level=0, unpack=None, unpack_dir=''):
    while t.next():
        content = t.get_content()
        if t.content_type == tt.tiif.TIIF_TYPE_RELEASE_HEADER:
            t.release_header_body_unpack(content)
        list_tiif_line(t, debug, level)
        if t.content_type == tt.tiif.TIIF_TYPE_RELEASE_HEADER:
            tiif_release_headers[name] = t.content_header_extension
        if t.content_type == tt.tiif.TIIF_TYPE_EMBEDDED_TIIF:
            ts = tt.tiif.tiif_buffer(content)
            ts.debug = debug
            list_tiif_recursive(ts, t.content_name, debug, level+1, unpack, os.path.join(unpack_dir, t.content_name))
        if unpack != None:
            unpack_save_manifest(t, unpack_dir, debug)
            unpack_save_file(t, content, unpack_dir, debug)

def list_tiif(filelist, debug=False, level=0, unpack=None):
    for f in filelist:
        filesize = os.path.getsize(f)
        if unpack:
            unpack_dir = unpack
        else:
            unpack_dir = os.path.basename(f)+'.unpacked'
        print("Listing tiif file: %s, %dkb" % (f, filesize))
        t = tt.tiif.tiif_file(f)
        list_tiif_recursive(t, f, debug=debug, unpack=unpack, unpack_dir=unpack_dir)
        if unpack != None:
            print("Unpacked tiif file to directory: %s" % unpack_dir)
    for e in tiif_release_headers:
        print_debug(debug, e, tiif_release_headers[e])
    return tiif_release_headers

def main(argc, argv):
	if(argc != 5):
		print("%s [-i input file] [-o output directory]" % argv[0])
		return
	
	input_file = ""
	output_dir = ""
	if(argv[1] == "-i"):
		input_file = argv[2]
	else:
		print("%s [-i input file] [-o output directory]")
		return		
	if(argv[3] == "-o"):
		output_dir = argv[4]
	else:
		print("%s [-i input file] [-o output directory]")
		return	
	list_tiif([input_file],False,0,output_dir)

if __name__ == '__main__':
	main(len(sys.argv), sys.argv)

