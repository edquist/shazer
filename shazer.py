#!/usr/bin/python

import getopt
import glob
import sys
import os
import re

dryrun  = True
minsize = None
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
    return ("%.1f%s" % (n, sufs[sufidx])).rstrip(' 0.')

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
    size = st.st_size
    ino = st.st_ino
    return mtime, fn, sha, size, ino

def sizeok(size):
    return (minsize is None or size >= minsize) \
       and (maxsize is None or size <= maxsize)

firstmap = {}
shrinkage = 0

for mtime,fn,sha,size,ino in sorted(filter(None, map(hashline, open(infile)))):
    if sha in firstmap:
        firstfn, firstino = firstmap[sha]
        if firstino != ino and sizeok(size):
            if verbose:
                print "%d : %s -> %s" % (size, fn, firstfn)
            shrinkage += size
            if not dryrun:
                os.unlink(fn)
                os.link(firstfn, fn)
    else:
        firstmap[sha] = (fn,ino)

print "%d : total (%s)" % (shrinkage, kmg(shrinkage))

