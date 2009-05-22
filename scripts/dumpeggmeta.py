#!/usr/bin/env python

import sys
import os
import os.path
import rfc822
import StringIO
import fnmatch
import pprint

from pkg_resources import get_entry_map, find_distributions
import zipfile
import tarfile

def _match(name, inlist):
    """Return True if the given name matches any of the
    contents of the list of glob patterns inlist.
    """
    for pat in inlist:
        if fnmatch.fnmatchcase(name, pat):
            return True
    return False
    

def get_resource_files(dist, exList=None, incList=None, dirname=''):
    """A generator that retrieves resource file pathnames from 
    within a distribution.
    """
    
    exlist = exList or []
    inclist = incList or ['*']
    
    for res in dist.resource_listdir(dirname):
        if dirname != '':
            respath = '/'.join([dirname, res])
        else:
            respath = res
        if dist.resource_isdir(respath):
            for r in get_resource_files(dist, exlist, inclist, respath):
                if _match(r, inclist) and not _match(r, exlist):
                    yield r
        else:
            if _match(respath, inclist) and not _match(respath, exlist):
                yield respath


def _getdist_metadata(dist, dirname=''):
    """Retrieve metadata from within a distribution.
    Returns a dict.
    """
    metadata = {}
    for name in dist.metadata_listdir(dirname):
        if dirname != '':
            path = '/'.join([dirname, name])
        else:
            path = name
        if dist.metadata_isdir(path):
            for md in _getdist_metadata(dist, path):
                metadata[md[0]] = md[1]
        elif name.endswith('.txt'):
            metadata[path[:-4]] = [x.strip() for x in 
                     dist.get_metadata(path).splitlines() if x.strip() != '']
        elif name == 'PKG-INFO':
            instr = StringIO.StringIO(dist.get_metadata(name))
            message = rfc822.Message(instr)
            for k,v in message.items():
                metadata[k] = v
        elif name == 'not-zip-safe':
            metadata['zip-safe'] = False
        elif name == 'zip-safe':
            metadata['zip-safe'] = True
        else:
            metadata[path] = dist.get_metadata(path)
    return metadata
    
                
def _meta_from_tarfile(path):
    """Retrieve metadata from a tar file of a python source distribution.
    Returns a dict.
    """
    metadata = {}
    oldpkginfo = None
    tf = tarfile.open(path, mode='r')
    for name in tf.getnames():
        if '.egg-info/' in name and not name.endswith('.egg-info/'):
            metaname = os.path.splitext(os.path.basename(name))[0]
            meta = tf.extractfile(name).read().strip()
            if name.endswith('/PKG-INFO'):
                instr = StringIO.StringIO(meta)
                message = rfc822.Message(instr)
                for k,v in message.items():
                    metadata[k] = v                
            elif name.endswith('.txt'):
                metadata[metaname] = [x.strip() for x in 
                                     meta.splitlines() if x.strip() != '']
            elif name.endswith('/not-zip-safe'):
                metadata['zip-safe'] = False
            elif name.endswith('/zip-safe'):
                metadata['zip-safe'] = True
            else:
                continue
        elif name.endswith('/PKG-INFO'):
            oldpkginfo = name

        # if there's no egg-info, use old PKG-INFO if found     
        if len(metadata) == 0 and oldpkginfo:  
            message = rfc822.Message(tf.extractfile(oldpkginfo))
            for k,v in message.items():
                metadata[k] = v  

    return metadata              

def _meta_from_zipped_egg(path):
    """Retrieve metadata from a zipped egg file.
    Returns a dict.
    """
    metadata = {}
    zf = zipfile.ZipFile(path, 'r')
    for name in zf.namelist():
        if name.startswith('EGG-INFO/'):
            metaname = os.path.splitext(os.path.basename(name))[0]
            meta = zf.read(name).strip()
            if name.endswith('/PKG-INFO'):
                instr = StringIO.StringIO(meta)
                message = rfc822.Message(instr)
                for k,v in message.items():
                    metadata[k] = v
            elif name.endswith('.txt'):
                metadata[metaname] = [x.strip() for x in 
                                     meta.splitlines() if x.strip() != '']
            elif name.endswith('/not-zip-safe'):
                metadata['zip-safe'] = False
            elif name.endswith('/zip-safe'):
                metadata['zip-safe'] = True
            else:
                continue
    return metadata


def get_metadata(path):
    """Retrieve metadata from the file or directory specified by path.
    path can be an installed egg, a zipped egg file, or a 
    zipped or unzipped tar file of a python distutils or setuptools
    source distribution.
    Returns a dict.
    """

    if path.lower().endswith('.tar') or '.tar.gz' in path.lower():
        # it's a tar file or gzipped tar file
        return _meta_from_tarfile(path)

    dists = [x for x in find_distributions(path,only=True)]
    if len(dists) == 0:
        raise RuntimeError('%s is not a zipped egg or an installed distribution'%self.path)

    dist = dists[0]

    if os.path.abspath(path).lower() != os.path.abspath(dist.location).lower():
        raise RuntimeError('%s is not a valid distribution (dist.location=%s)'%
                (os.path.abspath(path),dist.location))

    # getting access to metadata in a zipped egg doesn't seem to work
    # right, so just use a ZipFile to access files under the EGG-INFO
    # directory to retrieve the metadata.   
    if os.path.isfile(path):
        if path.lower().endswith('.egg'):
            # it's a zip file
            metadata = _meta_from_zipped_egg(path)
        else:
            raise RuntimeError('cannot process file %s: unknown file type' %
                                path)
    else:
        metadata = _getdist_metadata(dist)


    metadata['py_version'] = dist.py_version
    if 'platform' not in metadata or metadata['platform']=='UNKNOWN':
        metadata['platform'] = dist.platform

    metadata['entry_points'] = {}
    for gname,group in get_entry_map(dist, group=None).items():
        metadata['entry_points'][gname] = [ep for ep in group]
    
    return metadata    

    
if __name__ == '__main__':
    if len(sys.argv) > 2:
        print get_metadata(sys.argv[1])[sys.argv[2]]
    else:
        print pprint.pprint(get_metadata(sys.argv[1]))
        

