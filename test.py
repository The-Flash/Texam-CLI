import hashlib
import zlib
filename = "test/.texam/objects/b1/5a5744a2f54d7ee95abf4a016885721e9e25db"
with open(filename, "rb") as f:
    data = f.read()
    print(zlib.decompress(data).decode())