import sys
import os
import argparse
import configparser
import pathlib
import hashlib
import zlib
import glob

OBJECTS_DIR = pathlib.Path(".texam/objects")

class TexamRepo:
    repo_name = ".texam"
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

    def write_tree(self, path):
        tree_entries = []
        pattern = pathlib.Path(path) / "**" / "*.*"
        # for file in gl
        for file in glob.iglob(str(pattern), recursive=True):
            print(file)

def hash_object(data, obj_type, write=True):
        """
        Compute hash of object
        """
        header = "{} {}".format(obj_type, len(data)).encode()
        full_data = header + b'\x00' + data
        sha1 = hashlib.sha1(full_data).hexdigest()
        if write:
            dir = OBJECTS_DIR / sha1[:2]
            path = dir / sha1[2:]
            if not path.exists():
                dir.mkdir(exist_ok=True)
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

def write_blobs(path):
    path = pathlib.Path(path)
    if not path.is_dir():
        raise Exception("Path must be a directory")
    pattern = path / "**" / "*.*"
    for file in glob.iglob(str(pattern), recursive=True):
            write_blob(file)

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
argsp = argsubparsers.add_parser("push")
argsp = argsubparsers.add_parser("ls-tree")

def cmd_init(args):
    repo = TexamRepo(path=args.path, username=args.username, password=args.password)
    repo.initialize()
    print("Initialized empty Git repository in {}".format(repo.path.absolute()))

def cmd_add(args):
    path = pathlib.Path(args.path)
    if path.is_dir():
        write_blobs(path)
    elif path.is_file():
        write_blob(path)
    else:
        raise Exception("Not supported")
    

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    if args.command == "init":
        cmd_init(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "commit":
        print("Creating a commit object")
    elif args.command == "push":
        print("Pushing to a remote server")
    elif args.command == "ls-tree":
        print("Listing tree of a commit")