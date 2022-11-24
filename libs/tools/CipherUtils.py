from Crypto.Cipher import AES
from Crypto.Hash import MD5, SHA256
from Crypto import Random
from Crypto.Random import random
import string
import binascii
from base64 import b64encode, b64decode
import logging
import zlib
import libs.tools.ByteHelpers
import libs.userinteract as userinteract
import libs.app as app
import libs.tools.ByteHelpers as ByteHelpers

log = logging.getLogger(__name__)

hexArray = b"0123456789ABCDEF"

errorbyte = b""

key = "ebe5c0df162a50ba232d2d721ea8e3e1c5423bb0-12bd-48c3-8932-c93883dfcf1f"


BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(s[-1])]

def encrypt(ivBytes, keyBytes, textBytes):
    textBytes = pad(textBytes)

    #iv = Random.new().read(AES.block_size)
    cipher = AES.new(keyBytes, AES.MODE_CBC, ivBytes)
    encrypted = cipher.encrypt(textBytes)

    return ( ivBytes.encode('ascii') + encrypted )

def decrypt( ivBytes, keyBytes, textBytes ):
    
    cipher = AES.new(keyBytes, AES.MODE_CBC, ivBytes)

    decrypted = cipher.decrypt(textBytes)

    unp = unpad(decrypted.decode("UTF-8"))

    return unp


def getKeyBytes(mykey):
    try:
        md5 = MD5.new()
        md5.update(mykey.encode("UTF-8"))

        return md5.digest()
    except AssertionError as e:
        log.error("Password creation exception: {}".format(e))
        return b""


def bytesToHex(mybytes):
    return binascii.hexlify(bytes(mybytes))

def hexToBytes(myhex):
    return binascii.unhexlify(myhex)

def getSHA256(mydata):
    try:
        sha = SHA256.new()
        sha.update(mydata)
        
        return sha.hexdigest()
    except AssertionError as e:
        log.error("SHA hash exception: {}".format(e))
        return None


def getMD5(mykey):
    try:
        md5 = MD5.new()
        md5.update(mykey)

        return md5.hexdigest()

    except AssertionError as e:
        log.error("MD5 hash exception: {}".format(e))
        return None

def getCustomSyncKey():
    if "pref" in dir(app):
        if app.pref.getValue("custom_sync_key", "") == "":
            app.pref.setValue("custom_sync_key", getRandomHexKey())

        mykey = app.pref.getValue("custom_sync_key", "")
    else:
        mykey = getRandomHexKey()

    if len(mykey) > 16:
        return mykey
    else:
        userinteract.error("Sync key is too short. Please create one with minimum lenght of 16 chars!")

    return None


def getKeyString():

        # we should cache and detect preference change and invalidate a flag for optimization
        customkey = getCustomSyncKey()
        if customkey is not None:
            sync_key = getMD5(customkey)
            return sync_key

        log.error("Could not get encryption key!")
        return None


def encryptBytes(plainBytes, keyBytes=None):
    if keyBytes is None:
        keyBytes = getKeyBytes(key)

    if keyBytes is None or len(keyBytes) != 16:
        log.error("Invalid Keybytes length!")
        return b""
    
    ivBytes = ''.join(random.choice(string.ascii_letters) for _ in range(16))
    
    encrypted_text = encrypt(ivBytes, keyBytes, b64encode(plainBytes).decode("ascii"))

    return encrypted_text


def decryptBytes(cipherData, keyBytes=None):
    if keyBytes == None:
        keyBytes = getKeyBytes(key)


    if (keyBytes is None) or (len(keyBytes) != 16):
        log.error("Invalid Keybytes length!")
        return b""

    ivBytes = cipherData[:16]
    dest = cipherData[16:]

    if len(cipherData) < len(ivBytes):
        return b""

    decrypted = b64decode(decrypt(ivBytes, keyBytes, dest))
    return decrypted


def decryptString(cipherData, keyBytes = None):
    try:
        if keyBytes == None:
            keyBytes = getKeyBytes(key)

        inbytes = b64decode(cipherData)
        ivBytes = inbytes[:16]
        dest = inbytes[16:]

        if len(cipherData) < len(ivBytes):
            return ""

        decrypted = decrypt(ivBytes, keyBytes, dest)

        return decrypted
        
    except AssertionError as e:
        log.error("Got error decoding data: {}".format(e))
        return ""


def decryptStringToBytes(cipherData):
    decryptedBytes = decryptString(cipherData).decode("UTF-8")

    if len(decryptedBytes) > 8 and decryptedBytes.startswith("1F8B0800"):
        decryptedBytes = ByteHelpers.decompressBytesToBytes(decryptedBytes)

    return decryptedBytes


def encryptString(plainText, keyBytes=None):
    if keyBytes is None:
        keyBytes = getKeyBytes(key)

    if keyBytes is None or len(keyBytes) != 16:
        log.error("Invalid Keybytes length!")
        return ""

    ivBytes = ''.join(random.choice(string.ascii_letters) for _ in range(16))
    encrypted = encrypt(ivBytes, keyBytes, plainText)

    return b64encode(encrypted)


def encryptBytesToString(inbytes):
    return encryptBytes(inbytes)


def compressString(source):
    try:
        buf = zlib.compress(source)

        return b64encode(buf)
    except AssertionError as e:
        log.error("Error compressing string: {}".format(e))
        return None


def decompressString(compressed):
    try:
        buf = b64decode(compressed)
        deflated = zlib.decompress(buf)

        return deflated
    except AssertionError as e:
        log.error("Error decompressing the string: {}".format(e))


def compressStringToBytes(string):
    return compressString(string)

def compressBytesToBytes(string):
    return compressString(string)


def compressEncryptString(plainText):
    encrypted = encryptString(plainText)
    compressed = compressString(encrypted)

    return compressed

def decompressEncryptString(compressed):
    deflate = decompressString(compressed)
    decrypted = decryptString(deflate)

    return decrypted

def compressEncryptBytes(plainText):
    return b64encode(encryptBytes(compressBytesToBytes(plainText)))


def getRandomKey():
    keybytes = [random.randint(0,255) for x in range(16)]
    return keybytes


def getRandomHexKey():
    return bytesToHex(getRandomKey())

