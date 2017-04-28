#!/usr/bin/python

import getopt
import glob
import sys
import os
import re

dryrun  = True
minsize = 1
maxsize = None
verbose = False
globpat = None
nocase  = False

def usage():
    print "usage: %s [-x] [-v] [-s minsize[:maxsize]] [-g globpat] shasums" \
                  % os.path.basename(__file__)
    print
    print "Options:"
    print "  -x           execute (default is dry-run)"
    print "  -v           verbose; show each file pair to be linked"
    print "  -g globpat   only consider files matching globpat ('%'->'*')"
    print "  -i           globpat is case-insensitive"
    print "  -s min[:max] ignore files outside of size range"
    print
    print "Generate shasums with:"
    print "  find dir/ [...] -type f -exec sha1sum {} + > shasums"
    sys.exit(0)

try:
    opts, args = getopt.getopt(sys.argv[1:], 'xvig:s:')
except getopt.GetoptError:
    usage()

def un_kmg(sizestr):
    sufs = 'ckmgtpezy'
    if not sizestr:
        return
    idx = sufs.find(sizestr[-1].lower())
    if idx >= 0:
        return int(sizestr[:-1]) * 1024 ** idx
    else:
        return int(sizestr)

for k,v in opts:
    if   k == '-x':
        dryrun = False
    elif k == '-s':
        minsize,maxsize = map(un_kmg, (v.split(':') + [None])[:2])
        if minsize == None:
            minsize = 1
    elif k == '-v':
        verbose = True
    elif k == '-g':
        globpat = v.replace('%', '*')
    elif k == '-i':
        nocase = True

if globpat and nocase:
    globpat = globpat.lower()

if len(args) != 1:
    usage()

infile = args[0]

def kmg(n):
    sufidx = 0
    sufs = ' KMGTPEZY'
    while n > 1126:
        sufidx += 1
        n /= 1024.0
    return ("%.1f%s" % (n, sufs[sufidx])).rstrip(' 0').rstrip('.')

def globmatch(fn):
    fn = os.path.basename(fn)
    if nocase:
        fn = fn.lower()
    return glob.fnmatch.fnmatch(fn, globpat)

def hashline(line):
    line = line.rstrip('\n')
    if not re.match(r'[0-9a-f]{40}  .', line):
        print >>sys.stderr, "skipping malformed line: '%s'" % line
    sha = line[:40]
    fn = line[42:]
    if globpat is not None and not globmatch(fn):
        return
    st = os.stat(fn)
    mtime = st.st_mtime
    return sha, mtime, fn, st

def sizeok(size):
    return size >= minsize and (maxsize is None or size <= maxsize)

lastsha = ''
shrinkage = 0
shrinkage_blocks = 0
relinks = 0

for sha,mtime,fn,st in sorted(filter(None, map(hashline, open(infile)))):
    if sha == lastsha:
        if firstino != st.st_ino and sizeok(st.st_size):
            if verbose:
                print "%d : %s -> %s" % (st.st_size, fn, firstfn)
            shrinkage += st.st_size
            shrinkage_blocks += st.st_blocks
            relinks += 1
            if not dryrun:
                os.unlink(fn)
                os.link(firstfn, fn)
    else:
        lastsha  = sha
        firstfn  = fn
        firstino = st.st_ino

print "%d : total (%s, %s used; %d relinks)" % (shrinkage, kmg(shrinkage),
                                                kmg(shrinkage_blocks * 512),
                                                relinks)

