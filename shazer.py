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
redoall = False

def usage():
    print "usage: %s [-xvai] [-s minsize[:maxsize]] [-g globpat] shasums" \
                  % os.path.basename(__file__)
    print
    print "Options:"
    print "  -x           execute (default is dry-run)"
    print "  -v           verbose; show each file pair to be linked"
    print "  -a           process already linked files too"
    print "  -g globpat   only consider files matching globpat ('%'->'*')"
    print "  -i           globpat is case-insensitive"
    print "  -s min[:max] ignore files outside of size range"
    print
    print "Generate shasums with:"
    print "  find dir/ [...] -type f -exec sha1sum {} + > shasums"
    sys.exit(0)

try:
    opts, args = getopt.getopt(sys.argv[1:], 'xvaig:s:')
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
    elif k == '-a':
        redoall = True
    elif k == '-g':
        globpat = v.replace('%', '*')
    elif k == '-i':
        nocase = True

if globpat and nocase:
    globpat = globpat.lower()

if len(args) != 1:
    usage()

infile = args[0]

class LazyStat(object):
   def __get__(self, obj, objtype):
#      print "getting stat info for '%s'" % obj.fn
       st = os.stat(obj.fn)
       obj.st = st
       return st

class FInfo(object):
    st = LazyStat()

    def __init__(self, sha, fn):
        self.sha = sha
        self.fn  = fn

    # NB: {a,b}.st are not accessed unless {a,b}.sha match
    def __cmp__(self, other):
        return cmp(self.sha, other.sha) \
            or cmp(self.st.st_mtime, other.st.st_mtime) \
            or cmp(self.fn, other.fn)

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

def unescape(fn):
    helper = lambda m: {'\\': '\\', 'n': '\n'}[m.group(1)]
    return re.sub(r'\\([\\n])', helper, fn)

def hashline(line):
    line = line.rstrip('\n')
    m = line.startswith('\\') and re.match(r'\\([0-9a-f]{40})  (.+)', line)
    if m:
        sha, efn = m.groups()
        fn = unescape(efn)
    elif re.match(r'[0-9a-f]{40}  .', line):
        sha = line[:40]
        fn = line[42:]
    else:
        print >>sys.stderr, "skipping malformed line: '%s'" % line
        return
    if globpat is not None and not globmatch(fn):
        return
    return FInfo(sha, fn)

def sizeok(size):
    return size >= minsize and (maxsize is None or size <= maxsize)

last = FInfo(None, None)
shrinkage = 0
shrinkage_blocks = 0
relinks = 0

for fi in sorted(filter(None, map(hashline, open(infile)))):
    if fi.sha == last.sha:
        if (redoall or last.st.st_ino != fi.st.st_ino) \
                             and sizeok(fi.st.st_size):
            if verbose:
                print "%d : %s -> %s" % (fi.st.st_size, fi.fn, last.fn)
            shrinkage += fi.st.st_size
            shrinkage_blocks += fi.st.st_blocks
            relinks += 1
            if not dryrun:
                os.unlink(fi.fn)
                os.link(last.fn, fi.fn)
    else:
        last = fi

print "%d : total (%s, %s used; %d relinks)" % (shrinkage, kmg(shrinkage),
                                                kmg(shrinkage_blocks * 512),
                                                relinks)

