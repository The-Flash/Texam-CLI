import hashlib
import zlib
filename = "test/.texam/objects/a7/64a240fa75b22de51b7a6003a20b5988118f7a"
with open(filename, "rb") as f:
    data = f.read()
    print(zlib.decompress(data).decode())