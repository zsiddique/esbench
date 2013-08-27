# -*- coding: UTF-8 -*-

import datetime
import zipfile
import os.path
import logging
import argparse
import sys
import collections
# import json
from xml.etree import ElementTree

import requests


__version__ = (0,0,1)

logger = logging.getLogger(__name__)

def urls(count=1):
    d = datetime.datetime.utcnow()
    day = datetime.timedelta(days=1)
    for _ in range(count):
        s = d.strftime(r'ad%Y%m%d.zip')
        yield ("http://storage.googleapis.com/patents/assignments/2013/%s" % s, s)
        d -= day


def download(url, fn):
    response = requests.get(url)
    if response.status_code == 200:
        with open(fn, "w") as f:
            f.write(response.content)
        return os.path.abspath(fn)
    else:
        return False


def extract(zfn):

    if not zfn or not zfn.endswith(".zip"):
        return

    else: 
        try: 
            archive = zipfile.ZipFile(zfn)
            for fn in archive.namelist():
                archive.extract(fn)
                yield os.path.abspath(fn)
    
        finally:
            archive.close()
            os.remove(zfn)


def get_assignments(days=1): 
    for url, fn in urls(days):
        for xfn in extract(download(url, fn)):
            try: 
                with open(xfn, "rU") as f:
                    for line in f:
                        if line.startswith("<patent-assignment>"):
                            yield line.strip()
                        else:
                            continue
            finally:
                os.remove(xfn)


def parse(s):
    root = ElementTree.fromstring(s)
    for node in root.iterfind('.//patent-property'):
        p = PatentProperty(node)
        yield p
        
    
class PatentProperty(collections.Mapping): 

    def __init__(self, root):
        self.data = {
            'invention-title': '',
            'invention-title-language': '', 
            'document-ids': []
        }
        self.from_xml(root)
        return

    def __getitem__(self, key): 
        return self.data[key]
    
    def __iter__(self):
        for k in self.data:
            yield k
    
    def __len__(self):
        return 3
    
    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return str(self.data)

    def from_xml(self, root):
        i = root.find('invention-title')
        try:
            self.data['invention-title'] = i.text
            self.data['invention-title-language'] = i.attrib['lang']
        except AttributeError:
            self.data['invention-title'] = ''
            self.data['invention-title-language'] = ''

        ids = list(root.iterfind('.//document-id'))
        if len(ids) == 3: 
            self.data['document-ids'].append(ApplicationNumber(ids[0]))
            self.data['document-ids'].append(PatentNumber(ids[1]))
            self.data['document-ids'].append(PublicationNumber(ids[2]))
        elif len(ids) == 2:
            self.data['document-ids'].append(ApplicationNumber(ids[0]))
            self.data['document-ids'].append(PublicationNumber(ids[1]))
        else:
            for docid in ids:
                self.data['document-ids'].append(DocumentID(docid))


class DocumentID(collections.Mapping):

    APPLICATION = 'app'
    PATENT = 'pat'
    PUBLICATION = 'pub'

    def __init__(self, root): 
        self.data = {
            'country': '', 
            'doc-number': '', 
            'kind': '', 
            'date': '', 
            '_type_stated': None, 
            '_type_inferred': None, 
        }
        self.from_xml(root)
        self.guess_type()
        return

    def __getitem__(self, key): 
        return self.data[key]
    
    def __iter__(self):
        for k in self.data:
            yield k
    
    def __len__(self):
        return 4

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return str(self.data)
    
    def guess_type(self):
        idstr = self.data['doc-number']
        if len(idstr) == 7: 
            try: int(idstr, 10)
            except ValueError: return False
            self.data['_type_inferred'] = DocumentID.PATENT
            return True
        elif len(idstr) == 8: 
            try: int(idstr, 10)
            except ValueError: return False
            self.data['_type_inferred'] = DocumentID.APPLICATION
            return True
        elif len(idstr) in [10, 11]: 
            try: int(idstr, 10)
            except ValueError: return False
            self.data['_type_inferred'] = DocumentID.PUBLICATION
            return True
        else:
            self.data['_type_inferred'] = ''
            return False

    
    def from_xml(self, root):
        for k in self.data:
            try: 
                self.data[k] = root.findtext(k).strip()
            except AttributeError:
                pass


class ApplicationNumber(DocumentID):

    def __init__(self, root):
        super(ApplicationNumber, self).__init__(root)
        self.data['_type_stated'] = DocumentID.APPLICATION


class PatentNumber(DocumentID):

    def __init__(self, root):
        super(PatentNumber, self).__init__(root)
        self.data['_type_stated'] = DocumentID.PATENT


class PublicationNumber(DocumentID):

    def __init__(self, root):
        super(PublicationNumber, self).__init__(root)
        self.data['_type_stated'] = DocumentID.PUBLICATION


def get_args_parser():
    parser = argparse.ArgumentParser(description="esbench USPTO patent assignment downloader.")
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-d', '--days', type=int, default=3, help="fetch records for how many days? (default: %(default)s)")
    return parser


import copy

def main():
    logging.basicConfig(level=logging.WARNING)
    args = get_args_parser().parse_args()

    try: 
        for a in get_assignments(args.days):
            for p in parse(a):
                print(p)

    except IOError:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
