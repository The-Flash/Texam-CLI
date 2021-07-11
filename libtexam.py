import sys
import os
import argparse
import configparser
import pathlib
import hashlib
import zlib
import getpass
import requests

REPO_NAME = ".texam"
OBJECTS_DIR = pathlib.Path(".texam/objects")
HEAD_FILE = pathlib.Path(".texam/HEAD")
CONFIG_FILE = pathlib.Path(".texam/config")
PUSH_URL = "http://127.0.0.1:8000/test/upload/"

class TexamRepo:
    repo_name = REPO_NAME
    head_name = "master"
    def __init__(self, path=".", username=None, password=None, test_id=None):
        self.path = pathlib.Path(path) # represents the worktree
        self.username = username
        self.password = password
        self.repo_dir = self.path / self.repo_name # represents the repository
        self.objects_dir = self.repo_dir / "objects"
        self.test_id = test_id

    def initialize(self, exist_ok=True):
        """
        Initialize a new, empty texam repository.
        Create directories:
            1. objects
        Create files: 
            1. config
            2. HEAD
        """
        if not self.path.exists():
            raise Exception("Cannot initialize Texam repository. {} does not exist".format(self.path.absolute()))
        if self.username is None:
            raise Exception("Username must be specified")
        if self.password is None:
            raise Exception("Password must be specified")
        self.repo_dir.mkdir(exist_ok=exist_ok) # Create repository
        os.system("attrib +H {}".format(self.repo_dir)) # Hide repo directory
        self.objects_dir.mkdir(exist_ok=exist_ok) # Create objects directory
        self.conf = self.config_create()
        self.head_create()

    def add(self, path="."):
        self.write_tree(path)

    def config_create(self):
        conf = configparser.ConfigParser()
        conf.add_section("user")
        conf.set("user", "username", str(self.username))
        conf.set("user", "password", str(self.password))
        conf.add_section("test-details")
        if self.test_id is not None:
            conf.set("test-details", "test-id", str(self.test_id))
        with open(self.repo_file("config"), "w") as f:
            conf.write(f)
        return conf

    def head_create(self):
        if pathlib.Path(self.repo_file("HEAD")).exists:
            return
        with open(self.repo_file("HEAD"), "w") as f:
            f.write("{}".format(self.head_name))

    def repo_file(self, *path):
        return str(self.repo_dir.joinpath(*path))

def read_config(path=CONFIG_FILE):
    config = {}
    conf = configparser.ConfigParser()
    conf.read(path)
    config["username"] = conf["user"]["username"]
    config["password"] = conf["user"]["password"]
    config["test_id"] = conf["test-details"].get("test-id", None)
    return config

def hash_object(data, obj_type, write=True):
        """
        Compute hash of object
        """
        if len(obj_type) == 0:
            full_data = data
        else:
            header = "{}".format(obj_type).encode()
            full_data = header + b'\x00' + data
        sha1 = hashlib.sha1(full_data).hexdigest()
        if write:
            dir = OBJECTS_DIR / sha1[:2]
            path = dir / sha1[2:]
            if not path.exists():
                os.makedirs(os.path.dirname(str(path)), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(zlib.compress(full_data))
        return sha1

def write_blob(path):
    file = pathlib.Path(path)
    if not file.is_file():
        raise Exception("Item is not a path")
    with open(path, "rb") as f:
        data = f.read()
        return hash_object(data, "blob")

def find_blob(hash):
    if not OBJECTS_DIR.exists():
        raise Exception("Invalid Texam Repo")
    parent = OBJECTS_DIR /hash[:2]
    input_path = parent / hash[2:]
    if len(hash) < 5:
        return None
    if not parent.exists():
        return None
    for file in parent.iterdir():
        if str(file).startswith(str(input_path)):
            return file
    return None

def read_blob(hash):
    blob = find_blob(hash)
    if blob is None:
        raise Exception("Blob not found")
    with open(blob, "rb") as f:
        data = f.read()
        full_data = zlib.decompress(data)
        # i = full_data.find(b"\x00")
        # header = full_data[:i]
        # if header != b"blob":
        #     raise Exception("Not a blob")
        # data = full_data[i+1:]
        return full_data

graph = {}
def build_graph(directory="."):
    path = pathlib.Path(directory)
    graph[str(path)] = []
    def inner():
        for p in path.iterdir():
            if str(p).startswith(".texam"):
                continue
            elif p.is_file():
                graph[str(directory)].append(str(p))
            elif p.is_dir():
                graph[str(directory)].append(str(p))
                build_graph(str(p))
    inner()
    return graph
  
def write_trees(path: pathlib.Path):
    if not OBJECTS_DIR.exists():
        raise Exception("Invalid Texam Repo")
    tree_graph = build_graph(str(path))
    reversed_graph = dict(reversed(tree_graph.items()))
    last_tree = ""

    def write_tree(values):
        tree_entry = []
        for v in values:
            p = pathlib.Path(v)
            if p.is_file():
                sha1 = write_blob(v)
                c_path = pathlib.Path(v).name
                entry = "blob {} {}".format(sha1, c_path)
                tree_entry.append(entry)
            elif p.is_dir():
                sha1 = write_tree(reversed_graph[str(p)])
                c_path = pathlib.Path(v).name
                entry = "tree {} {}".format(sha1, c_path)
                tree_entry.append(entry)
        data = "\n".join(tree_entry).encode()
        return hash_object(data, "tree")
        
    for _, v in reversed_graph.items():
        last_tree = write_tree(v)
    return last_tree

def get_object_parts(path):
    with open(path, "rb") as f:
        data = zlib.decompress(f.read())
        header, body = data.split(b"\x00")
    return header, body

def is_blob(path):
    header, _ = get_object_parts(path)
    return header.startswith(b"blob")

def is_tree(path):
    header, _ = get_object_parts(path)
    return header.startswith(b"tree")

def is_commit(path):
    header, _ = get_object_parts(path)
    return header.startswith(b"commit")

def commit(path="."):
    if not OBJECTS_DIR.exists():
        raise Exception("Invalid Texam Repo")
    last_tree = write_trees(pathlib.Path(path))
    conf = read_config()
    header_entries = []
    AUTHOR = "AUTHOR {}".format(conf["username"])
    header_entries.append(AUTHOR)
    TEST_ID = "TEST_ID {}".format(conf["test_id"])
    header_entries.append(TEST_ID)
    HOST = "HOST {}".format(getpass.getuser())
    header_entries.append(HOST)
    header = "\n".join(header_entries)
    commit_hash = hash_object(last_tree.encode(), "commit {}".format(header))
    print("Last commit", commit_hash)
    with open(HEAD_FILE, "w") as f:
        f.write(commit_hash)
    print("Committed to repo")

def get_tree_descendants(tree_hash):
    descendants = []

    def parse_tree(tree_hash):
        path = OBJECTS_DIR / tree_hash[:2] / tree_hash[2:]
        _, body = get_object_parts(path)
        for v in body.decode().split("\n"):
            if v.startswith("blob"):
                hash = v.split()[1]
                p = OBJECTS_DIR / hash[:2] / hash[2:]
                descendants.append(str(p))
            elif v.startswith("tree"):
                hash = v.split()[1]
                p = OBJECTS_DIR / hash[:2] / hash[2:]
                descendants.append(str(p))
                parse_tree(hash)
    parse_tree(tree_hash)
    return descendants

def get_commit_objects(commit_hash):
    commit_path = OBJECTS_DIR / commit_hash[:2] / commit_hash[2:]
    if not is_commit(commit_path):
        raise Exception("Not a commit object")
    objects = []
    _, commit_tree_b = get_object_parts(commit_path)
    commit_tree = commit_tree_b.decode()
    commit_tree_path = OBJECTS_DIR / commit_tree[:2] / commit_tree[2:]
    objects.extend([str(HEAD_FILE), str(commit_path), str(commit_tree_path)])
    descendants = get_tree_descendants(commit_tree)
    objects.extend(descendants)
    return objects

def push(commit_hash=None):
    """
    1. IF NOT HASH IS PASSED, USE MASTER HASH
    2. IF THE COMMIT DOES NOT EXIST, RAISE EXCEPTION
    3. GET ALL OBJECTS FROM THE COMMIT TREE TO THE LAST RECURSIVELY
    """
    if commit_hash is None:
        with open(HEAD_FILE) as f:
            commit_hash = f.read() 
    commit_path = OBJECTS_DIR / commit_hash[:2] / commit_hash[2:]
    if not commit_path.exists():
        raise Exception("Commit object does not exist")
    conf = read_config()
    if conf["test_id"] is None:
        raise Exception("Test ID is not set. Run texam init")
    request_data = {
        "index_no": conf["username"],
        "password": conf["password"],
        "test_id": conf["test_id"]
    }
    objects = get_commit_objects(commit_hash)
    request_files = [(str(obj), open(obj, "rb")) for obj in objects]
    # print(request_files)
    URL = PUSH_URL
    r = requests.post(URL, data=request_data, files=request_files)
    print(r.text)

argparser = argparse.ArgumentParser(description="CLI for Texam Software")
argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True
argsp = argsubparsers.add_parser("init", help="Initialize a new, empty texam repository")
argsp.add_argument("path", 
    metavar="directory", 
    default=".", 
    nargs="?"
)
argsp.add_argument("--username", "-u", metavar="Index Number", dest="username", nargs="?", required=True, help="Your Index Number")
argsp.add_argument("--password", "-p", metavar="Password", dest="password", nargs="?", required=True, help="Your Password")
argsp.add_argument("--test-id", "-t", metavar="Test ID", dest="test_id", help="ID of Test you are taking")
argsp = argsubparsers.add_parser("add")
argsp.add_argument("path", 
    metavar="directory", 
    default=".", 
    nargs="?"
)
# argsp.add_argument("add-path", metavar="file", default=".")
argsp = argsubparsers.add_parser("commit")
argsp.add_argument("path", 
    metavar="directory", 
    default=".", 
    nargs="?"
)
argsp = argsubparsers.add_parser("cat-file")
argsp.add_argument("hash", 
    metavar="hash", 
    nargs="?"
)
argsp = argsubparsers.add_parser("push")
argsp.add_argument("hash", 
    metavar="hash", 
    nargs="?"
)
argsp = argsubparsers.add_parser("cat-file")
argsp.add_argument("hash", 
    metavar="hash", 
    nargs="?"
)
argsp = argsubparsers.add_parser("ls-tree")

def cmd_init(args):
    repo = TexamRepo(path=args.path, username=args.username, password=args.password, test_id=args.test_id)
    repo.initialize()
    print("Initialized empty Git repository in {}".format(repo.path.absolute()))

def cmd_commit(args):
    commit(args.path)

def cmd_ls_tree():
    if not HEAD_FILE.exists():
        raise Exception("Invalid Texam Repo")
    with open(HEAD_FILE, "r") as f:
        current_tree = f.read()
    tree_path = OBJECTS_DIR / current_tree[:2] / current_tree[2:]
    with open(tree_path, "rb") as f:
        tree = zlib.decompress(f.read()).decode()
        sys.stdout.write(tree)

def cmd_cat_file(args):
    print(read_blob(args.hash))
        
def cmd_push(args):
    push(args.hash)
    
def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    if args.command == "init":
        cmd_init(args)
    elif args.command == "commit":
        cmd_commit(args)
    elif args.command == "cat-file":
        cmd_cat_file(args)
    elif args.command == "push":
        cmd_push(args)
    elif args.command == "ls-tree":
        cmd_ls_tree()
