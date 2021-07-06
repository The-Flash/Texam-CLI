import sys
import os
import argparse
import configparser
import pathlib

class TexamRepo:
    repo_name = ".texam"
    head_name = "master"
    def __init__(self, path=".", username=None, password=None):
        self.path = pathlib.Path(path) # represents the worktree
        self.username = username
        self.password = password
        self.repo_dir = self.path / self.repo_name # represents the repository
        self.objects_dir = self.repo_dir / "objects"

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

    def config_create(self):
        conf = configparser.ConfigParser()
        conf.add_section("user")
        conf.set("user", "username", str(self.username))
        conf.set("user", "password", str(self.password))
        with open(self.repo_file("config"), "w") as f:
            conf.write(f)
        return conf

    def head_create(self):
        with open(self.repo_file("HEAD"), "w") as f:
            f.write("{}".format(self.head_name))

    def repo_file(self, *path):
        return str(self.repo_dir.joinpath(*path))

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
argsp = argsubparsers.add_parser("commit")
argsp = argsubparsers.add_parser("push")
argsp = argsubparsers.add_parser("ls-tree")

def cmd_init(args):
    repo = TexamRepo(path=args.path, username=args.username, password=args.password)
    repo.initialize()
    print("Initialized empty Git repository in {}".format(repo.path.absolute()))


def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    if args.command == "init":
        cmd_init(args)
    elif args.command == "add":
        print("Creating a tree object")
    elif args.command == "commit":
        print("Creating a commit object")
    elif args.command == "push":
        print("Pushing to a remote server")
    elif args.command == "ls-tree":
        print("Listing tree of a commit")