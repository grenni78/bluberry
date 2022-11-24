import libs.app as app
import logging
import hashlib as hash
import zlib
import struct
import binascii

log = logging.getLogger(__name__)

def differentBytes(name, value):
    id = "differentBytes-" + name
    last_hash = app.ppref.getValue(id,"")
    this_hash = hash.sha256(value)
    if this_hash == last_hash:
        return False
    app.ppref.setValue(id, this_hash)
    return True


def bchecksum(value):
    c = zlib.crc32(bytes)
    buf = struct.pack("<b",c)
    return buf


def compressBytesforPayload(value):
    return compressBytesToBytes(b"".join([value, bchecksum(value)]))


def compressBytesToBytes(value):
    try:
        gzipped_data = zlib.compress(value)
        return gzipped_data
    except AssertionError as e:
        log.error("Exception in compress: {}".format(e))
        return b"00"

def decompressBytesToBytes(value):
    try:
        log.debug("Decompressing  bytes size: {}".format(len(value)))

        output = zlib.decompress(value, bufsize=8192)

        return binascii.hexlify(output)

    except AssertionError as e:
        log.error("Exception in decompress: {}".format(e))
        return b""
