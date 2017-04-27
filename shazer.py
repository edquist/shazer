#!/usr/bin/python

import getopt
import sys
import os

dryrun = False
minsize = 1024

def usage():
    print "usage: %s [-n] [-s minsize] shasfile" % os.path.basename(__file__)
    sys.exit(0)

try:
    opts, args = getopt.getopt(sys.argv[1:], 'ns:')
except getopt.GetoptError:
    usage()

for k,v in opts:
    if   k == '-n':
        dryrun = True
    elif k == '-s':
        minsize = int(v)

if len(args) != 1:
    usage()

infile = args[0]

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

for mtime,fn,sha,size,ino in sorted(map(hashline, open(infile))):
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

