import sys
import os
import argparse
import configparser
import pathlib
import hashlib
import zlib

REPO_NAME = ".texam"
OBJECTS_DIR = pathlib.Path(".texam/objects")
HEAD_FILE = pathlib.Path(".texam/HEAD")
CONFIG_FILE = pathlib.Path(".texam/config")

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
        conf.set("test-details", "test-id", str(self.test_id))
        with open(self.repo_file("config"), "w") as f:
            conf.write(f)
        return conf

    def head_create(self):
        with open(self.repo_file("HEAD"), "w") as f:
            f.write("{}".format(self.head_name))

    def repo_file(self, *path):
        return str(self.repo_dir.joinpath(*path))

def read_config(path=CONFIG_FILE):
    config = {}
    conf = configparser.ConfigParser()
    conf.read(path)
    config["username"] = conf["user"]["username"]
    config["test_id"] = conf["test-details"]["test-id"]
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
        i = full_data.find(b"\x00")
        header = full_data[:i]
        if header != b"blob":
            raise Exception("Not a blob")
        data = full_data[i+1:]
        return data

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
                entry = "blob\x00{} {}".format(sha1, v)
                tree_entry.append(entry)
            elif p.is_dir():
                sha1 = write_tree(reversed_graph[str(p)])
                entry = "tree\x00{} {}".format(sha1, v)
                tree_entry.append(entry)
        data = "\n".join(tree_entry).encode()
        return hash_object(data, "")
        
    for _, v in reversed_graph.items():
        last_tree = write_tree(v)
    return last_tree

def commit(path="."):
    if not OBJECTS_DIR.exists():
        raise Exception("Invalid Texam Repo")
    last_tree = write_trees(pathlib.Path(path))
    with open(HEAD_FILE, "w") as f:
        f.write(last_tree)
    print("Committed to repo")
        

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
argsp = argsubparsers.add_parser("ls-tree")

def cmd_init(args):
    repo = TexamRepo(path=args.path, username=args.username, password=args.password)
    repo.initialize()
    print("Initialized empty Git repository in {}".format(repo.path.absolute()))

def cmd_commit(args):
    print("Committing")
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
    pass
    
def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    if args.command == "init":
        cmd_init(args)
    elif args.command == "commit":
        cmd_commit(args)
    elif args.command == "cat-file":
        cmd_cat_file(args)
    elif args.command == "push":
        print("Pushing to a remote server")
        cmd_push(args)
    elif args.command == "ls-tree":
        cmd_ls_tree()
