# testing the cipher tools
import libs.tools.CipherUtils as CipherUtils

import time

text = "Hallo Welt!"
print(" intext: " + text)

crypted_text = CipherUtils.encryptString(text)
print(" crypted text (length: {}): {}".format(len(crypted_text),crypted_text))

decrypted_text = CipherUtils.decryptString(crypted_text)
print(" decrypted text: {}".format(decrypted_text))

testbytes = b'\x23\x24\x25\x26\x27'
print("test-Bytes: {} ".format(testbytes))

crypted_bytes = CipherUtils.encryptBytes(testbytes)
print(" crypted bytes (length: {}): {}".format(len(crypted_bytes), crypted_bytes))

decrypted_bytes = CipherUtils.decryptBytes(crypted_bytes)
print(" decrypted bytes: {}".format(decrypted_bytes))

print(" intext: " + text)

crypted_text = CipherUtils.compressEncryptString(text)
print(" crypted text (length: {}): {}".format(len(crypted_text),crypted_text))

decrypted_text = CipherUtils.decompressEncryptString(crypted_text)
print(" decrypted text: {}".format(decrypted_text))
