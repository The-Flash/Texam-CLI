from pathlib import Path
import glob
def ls_tree(path="."):
    for f in glob.iglob("{}/**/*.*".format(path), recursive=True):
        print(f)

def main():
    ls_tree("test")
    
main()