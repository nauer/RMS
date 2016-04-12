#! /usr/bin/env python3
# encoding: utf-8
"""
RMA -- Ressource Management System

@author:     Norbert Auer

@copyright:  Copyright 2016 Acib GmbH. All rights reserved.

@license:    license

@contact:    norbert.auer@boku.ac.at
@deffield    updated: Updated
"""

import sys
import os
import magic
import zlib # gzip gives different checksums repeating compression. Use zlib instead - gzip header is missing see http://unix.stackexchange.com/questions/22834/how-to-uncompress-zlib-data-in-unix
import hashlib
import shutil

from argparse import ArgumentParser
from argparse import Action
from argparse import RawDescriptionHelpFormatter
from argparse import FileType

__all__ = []
__version__ = '0.1'
__date__ = '2016-04-11'
__updated__ = '2016-04-11'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

class EnvDefault(Action):
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if not default and envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required,
                                         **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


class CLIError(Exception):
    """Generic exception to raise and log different fatal errors."""

    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


def main(argv=None): # IGNORE:C0111
    """Command line options."""

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Created by Norbert Auer on %s.
  Copyright 2016 Acib GmbH. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        subparsers = parser.add_subparsers(help='sub-command help')
        parser_init         = subparsers.add_parser('init', help='Create a new repository')
        parser_add          = subparsers.add_parser('add', help='Add a new file to the repository')
        parser_get          = subparsers.add_parser('get', help='Get file from repository')
        parser_checkout     = subparsers.add_parser('checkout', help='checkout help')
        parser_update       = subparsers.add_parser('update', help='update help')
        parser_edit_desc    = subparsers.add_parser('edit-desc', help='edit-desc help')

        parser_init.add_argument("init_path", action=EnvDefault, envvar='HOME', help='Path to the new repository parent. Default = "$HOME"')
        parser_init.set_defaults(func=init)

        parser_add.add_argument('add_file', type=str, help='Add file to the repository')
        parser_add.set_defaults(func=add)

        parser_get.add_argument('get_file', type=str, help='Get file from the repository')
        parser_get.set_defaults(func=get)

        parser_checkout.set_defaults(func=checkout)

        parser_update.set_defaults(func=update)

        parser_edit_desc.set_defaults(func=edit_desc)

        #group = parser.add_mutually_exclusive_group()
        #group2 = parser.add_mutually_exclusive_group()
        #group3 = parser.add_mutually_exclusive_group()
        #group.add_argument('-e', '--pattern', help='Single regular expression pattern to search for', type=str)
        #group.add_argument('-l', '--pattern-list', nargs='?',
        #                   help='Path to file with multiple patterns. One pattern per line', type=FileType('r'))
        # parser.add_argument('-V', '--version', action='version', version=program_version_message)
        # parser.add_argument('-v', '--invert-match', action='store_true',
        #                    help='Invert the sense of matching, to select non-matching lines.')
        #parser.add_argument('-t', '--fixed-strings', action='store_true',
        #                    help='Interpret PATTERN as a list of fixed strings, separated by newlines, any of which is to be matched.')
        #parser.add_argument('file', nargs='+', type=FileType('r'), default='-',
        #                    help="File from type fasta. Leave empty or use '-' to read from Stdin or pipe.")
        #parser.add_argument('-p', '--header-pattern',  default='^>', type=str,
        #                    help='Use this pattern to identify header line.')
        #parser.add_argument('-d', '--rm-duplicates', action='store_true',
        #                    help='Remove sequences with duplicate header lines. Hold only first founded sequence.')
        #group2.add_argument('-s', '--summary', action='store_true',
        #                    help='Returns instead of the normal output only the header and a summary of the sequence.')
        #group2.add_argument('-n', '--summary-no-header', action='store_true',
        #                    help='Same like summary without starting header line.')

        # Process arguments
        args = parser.parse_args()

        if DEBUG:
            print(args)

        args.func(args)

        return 0
    except KeyboardInterrupt:
        # handle keyboard interrupt Easy to use parsing tools.###
        return 0
    except Exception as e:
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2


def _get_repo_path():
    if "RMS" in os.environ:
        return os.environ["RMS"]


def _get_file_sha1(path):
    with open(path, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def _get_string_sha1(string):
    return hashlib.sha1(string).hexdigest()


def _get_repo_hashes(repo):
    return os.listdir(os.path.join(repo, "data"))


def init(args):
    try:
        os.makedirs(os.path.join(args.init_path,".rms", "data"))
        print("Create new repository at {}".format(os.path.join(args.init_path,".rms")))
        print("Add this RMS={} to your .profile file".format(os.path.join(args.init_path, ".rms")))
    except FileExistsError:
        print("Repository {} already exists".format(os.path.join(args.init_path, ".rms")))
        print("Add this RMS={} to your .profile file".format(os.path.join(args.init_path, ".rms")))
    except:
        print("Unexpected error: {}".format(sys.exc_info()[0]))
        raise


def add(args):
    repo = _get_repo_path()

    if repo is None:
        sys.exit("RMS is not set! Run 'rms init' before to create a rms repository.")

    mime = magic.from_file(args.add_file, mime=True)

    repo_hashes = _get_repo_hashes(repo)

    # check mime type if text
    if b"text" in mime:
        print("File is from type '{}' and will be compressed.".format(mime))

        compressed = None

        with open(args.add_file, "rb") as f:
            compressed = zlib.compress(f.read(), 9)

        # get sha1 sum
        sha1 = _get_string_sha1(compressed)

        # check if file is still in the repo
        if sha1 in repo_hashes:
            print("File is already in the repoistory. Add filename as tag.")
        else:
            # write zipped file
            with open(os.path.join(repo, "data", sha1), 'wb') as f:
                f.write(compressed)
    else:
        # get sha1 sum
        sha1 = _get_file_sha1(args.add_file)

        # check if file is still in the repo
        if sha1 in repo_hashes:
            print("File is already in the repoistory. Add filename as tag.")
        else:
            shutil.copy2(args.add_file, os.path.join(repo, "data", sha1))

    # add hardlink
    os.link(os.path.join(repo, "data", sha1), os.path.join(repo, "data", #basename args.add_file))


def get():
    pass

def edit_desc(args):
    pass

def update(args):
    pass

def checkout(args):
    pass

if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("add")
        sys.argv.append("../test/app")

        # sys.argv.append("init")
        # sys.argv.append("-x")
        # sys.argv.append("79")
        # sys.argv.append("-O")
        # sys.argv.append("test.fna")
        # sys.argv.append("../test/pattern_list")
        # sys.argv.append("-l")
        # sys.argv.append("../test/list")
        # sys.argv.append("--")
        # sys.argv.append("tata")
        # sys.argv.append("-z")
        # sys.argv.append("3")
        # sys.argv.append("-m")
        # sys.argv.append("24")
        # sys.argv.append("-F")
        # sys.argv.append("250")
        # sys.argv.append("-L")
        # sys.argv.append("52")
        # sys.argv.append("-e")
        # sys.argv.append(".*")
        # sys.argv.append("([^\t]*)\tgi\|(\d+).*?([^|]+)\|$")
        # sys.argv.append("/home/nauer/Projects/Proteomics/Scripts/snakemake/proto/test/output1.fna")
        # sys.argv.append("/home/nauer/Projects/Proteomics/Scripts/snakemake/proto/test/output2.fna")
        # sys.argv.append("/home/nauer/Projects/Proteomics/Scripts/snakemake/proto/test/output3.fna")
        # sys.argv.append("/home/nauer/Projects/Proteomics/Scripts/snakemake/proto/test/output6.fna")
        # sys.argv.append("../test/test_dup.fa")

    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'linegrep_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())