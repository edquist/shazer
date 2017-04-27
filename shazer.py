#!/usr/bin/python

import sys
import os

dryrun = True
minsize = 1024

def hashline(line):
    line = line.rstrip('\n')
    sha = line[:40]
    fn = line[42:]
    st = os.stat(fn)
    mtime = st.st_mtime
    size = st.st_size
    ino = st.st_ino
    return mtime, fn, sha, size, ino

firstmap = {}
firstino = {}
shrinkage = 0

for mtime,fn,sha,size,ino in sorted(map(hashline, open(sys.argv[1]))):
    if sha in firstmap:
        if firstino[sha] != ino and size > minsize:
            first = firstmap[sha]
            print "%d : %s -> %s" % (size, fn, first)
            shrinkage += size
            if not dryrun:
                os.unlink(fn)
                os.link(first, fn)
    else:
        firstmap[sha] = fn
        firstino[sha] = ino

print "%d : total" % shrinkage

