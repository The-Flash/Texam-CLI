import hashlib
import zlib
filename = "test/.texam/objects/e4/e86e73c9dd140c3b3e77715af34204b61d15a6"
with open(filename, "rb") as f:
    data = f.read()
    print(zlib.decompress(data).decode())