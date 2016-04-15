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
import json
import pdfkit
import collections

from datetime import date
from argparse import ArgumentParser
from argparse import Action
from argparse import RawDescriptionHelpFormatter
from enum import Enum
from markdown import markdown
from argparse import FileType

__all__ = []
__version__ = '0.3'
__date__ = '2016-04-11'
__updated__ = '2016-04-15'

DEBUG = 0
TESTRUN = 0
PROFILE = 0


class Format(Enum):
    markdown = 1
    html5 = 2
    pdf = 3
    json = 4


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
        parser_rm           = subparsers.add_parser('rm', help='Remove a tags or files from the repository')
        parser_get          = subparsers.add_parser('get', help='Get file from repository')
        parser_tag          = subparsers.add_parser('tag', help='Get or set tags')
        parser_desc         = subparsers.add_parser('desc', help='Set and get description')
        parser_desc_group   = parser_desc.add_mutually_exclusive_group()

        parser_init.add_argument("path",action=EnvDefault, envvar='HOME',
                                 help='Path to the new repository parent. Default = "$HOME"')
        parser_init.set_defaults(func=init)

        parser_add.add_argument('file', type=str, help='Add file to the repository')
        parser_add.add_argument('description', type=str, help='File description')
        parser_add.set_defaults(func=add)

        parser_rm.add_argument('file', type=str, help='Remove tag from the repository. If the last tag of a file was removed also the file itself with its description file will be removed.')
        parser_rm.set_defaults(func=rm)

        parser_get.add_argument('file', type=str, help='Get file from the repository')
        parser_get.add_argument('target', type=str, help='The target directory where the file should be copied to')
        parser_get.set_defaults(func=get)

        parser_tag.add_argument('file', type=str, help='File of interest.')
        parser_tag.add_argument('-n', '--new-tag', type=str, required=False, help='Add new tag for file')
        parser_tag.set_defaults(func=tag)

        parser_desc.add_argument('file', type=str, help='File of interest')
        parser_desc.add_argument('-f', '--format', choices=[f.name for f in Format], type=str, default=Format(3).name,
                                 help="Set the output format. Default is 'pdf'")
        parser_desc.add_argument('-o', '--output', type=FileType('wb'),
                                 help="Set the output format. Default is 'pdf'")
        parser_desc_group.add_argument('-g', '--get', type=str, help='Get description by keys')
        parser_desc_group.add_argument('-s', '--set', type=str, help='Set description by keys ("key:desc")')
        parser_desc_group.add_argument('-k', '--keys', action='store_true', help='Set description by keys ("key:desc")')
        parser_desc_group.add_argument('-c', '--clear', action='store_true',
                                       help='Delete all sections from description file')
        parser_desc.set_defaults(func=desc)

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


# Solution for nested dict update
# http://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth/3233356#3233356
def _dict_update(d, u):
    """
    Update a dictionary and it nested dictionaries
    :param d: dict
    :param u: dict
    :return: dict
    """
    for k, v in u.items():
        if isinstance(d, collections.Mapping):
            if isinstance(v, collections.Mapping):
                r = _dict_update(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
        else:
            d = {k: u[k]}
    return d


def _get_repo_path():
    """
    Read out and return the RMS environment variable
    :return: str
    """
    if "RMS" in os.environ:
        return os.environ["RMS"]


def _get_file_sha1(file):
    """
    Calculates and return the sha1sum from a file
    :param file: str
    :return: str
    """
    with open(file, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()


def _get_string_sha1(string):
    """
    Calculates and return the sha1sum from a string
    :param string: str
    :return: str
    """
    return hashlib.sha1(string).hexdigest()


def _get_repo_hashes():
    """
    Returns a list of all hashed unique files in the repository
    :return: list
    """
    return os.listdir(os.path.join(_get_repo_path(), "data"))


def _get_repo_tags():
    """
    Returns a list of all tag files in the repository
    :return: list
    """
    return os.listdir(os.path.join(_get_repo_path(), "tags"))


def _get_markdown(data_json, tagname):
    """
    Create markdown string from json object
    :param data_json: dict
    :param tagname: str
    :return: str
    """
    aliases = ''

    if len(data_json['tags']) > 1:
        aliases = '## Aliases:\n'

        for alias in data_json['tags']:
            if alias != tagname:
                aliases += "+ {}\n".format(alias)

    markd = '''# Description File for *{tag}*

## In repository since *{date}*

{aliases}
'''.format(tag=tagname, date=data_json['repo_date'], aliases=aliases, description=data_json['Description'])

    for key in data_json:
        if key == 'tags' or key == 'repo_date':
            continue
        if isinstance(data_json[key], list):
            section = "##{key}\n\n".format(key=key)

            for l in data_json[key]:
                section += "+ {val}\n".format(val=l)

            markd += section + "\n"
        elif isinstance(data_json[key], dict):
            pass
        else:
           markd += "##{key}\n{val}\n\n".format(key=key, val=data_json[key])

    return markd


def _get_tags_inodes():
    """
    Creates a dictionary with inode ids associated with their tag file names
    :return: dict
    """
    repo = _get_repo_path()
    tags = _get_repo_tags()
    inodes = dict()

    for tag in tags:
        if os.lstat(os.path.join(repo, "tags", tag)).st_ino in inodes.keys():
            inodes[os.lstat(os.path.join(repo, "tags", tag)).st_ino].append(tag)
        else:
            inodes[os.lstat(os.path.join(repo, "tags", tag)).st_ino] = [tag]

    return inodes


def _get_data_tag(tagname):
    """
    Returns the associated hash file name of the tag file
    :param tagname: str
    :return: str
    """
    repo = _get_repo_path()
    try:
        # Get inode from tag file
        inode = os.lstat(os.path.join(repo, "tags", tagname)).st_ino
    except:
        exit("Tag name '{}' does not exist".format(tagname))

    data = _get_repo_hashes()

    #inodes = dict()

    for d in data:
        if os.lstat(os.path.join(repo, "data", d)).st_ino == inode:
            return d


def _get_json_by_tag(tagname):
    """
    Return existing description file or create it and return the json object
    :param tagname: str
    :return: dict
    """
    repo = _get_repo_path()
    sha1 = _get_data_tag(tagname)
    json_data = ''
    try:
        f_r = open(os.path.join(repo, "desc", sha1), 'r+')

        json_data = json.loads(f_r.read())
    except:
        json_data = {"repo_date": str(date.today()), "tags": []}

    return json_data


def _get_json_by_sha1(sha1):
    """
    Return existing description file or create it and return the json object
    :param tagname: str
    :return: dict
    """
    repo = _get_repo_path()
    json_data = ''
    try:
        f_r = open(os.path.join(repo, "desc", sha1), 'r+')

        json_data = json.loads(f_r.read())
    except:
        print("Unexpected error: {}".format(sys.exc_info()[0]), file=sys.stderr)
        raise

    return json_data


def init(args):
    """
    Initiate a new repository
    :param args: dict
    :return: None
    """
    try:
        os.makedirs(os.path.join(args.init_path, ".rms", "data"))
        os.makedirs(os.path.join(args.init_path, ".rms", "tags"))
        os.makedirs(os.path.join(args.init_path, ".rms", "desc"))
        print("Create new repository at {}".format(os.path.join(args.init_path,".rms")))
        print("Add this RMS={} to your .profile file".format(os.path.join(args.init_path, ".rms")))
    except FileExistsError:
        print("Repository {} already exists".format(os.path.join(args.init_path, ".rms")), file=sys.stderr)
        print("Add this RMS={} to your .profile file".format(os.path.join(args.init_path, ".rms")), file=sys.stderr)
    except:
        print("Unexpected error: {}".format(sys.exc_info()[0]), file=sys.stderr)
        raise


def add(args):
    """
    Add new files or tag names
    :param args: dict
    :return: None
    """
    repo = _get_repo_path()
    args.file = os.path.expanduser(args.file)

    if repo is None:
        sys.exit("RMS is not set! Run 'rms init' before to create a rms repository.")

    try:
        mime = magic.from_file(args.file, mime=True)
    except FileNotFoundError:
        sys.exit("No such File: '{}'".format(args.file))
    except:
        print("Unexpected error: {}".format(sys.exc_info()[0]), file=sys.stderr)
        raise

    repo_hashes = _get_repo_hashes()

    filename = os.path.basename(args.file)

    # check mime type if text
    if b"text" in mime:
        print("File is from type '{}' and will be compressed.".format(mime))

        compressed = None

        with open(args.file, "rb") as f:
            compressed = zlib.compress(f.read(), 9)

        # get sha1 sum
        sha1 = _get_string_sha1(compressed)

        # check if file is still in the repo
        if sha1 in repo_hashes:
            print("File is already in the repository. Add file name as tag. Description is discarded. Use 'rms set {\"Description\":\"Message\"}' to update the description section.")
        else:
            # write zipped file
            with open(os.path.join(repo, "data", sha1), 'wb') as f:
                f.write(compressed)
    else:
        # get sha1 sum
        sha1 = _get_file_sha1(args.file)

        # check if file is still in the repo
        if sha1 in repo_hashes:
            print("File is already in the repository. Add file name as tag. Description is discarded. Use 'rms set {\"Description\":\"Message\"}' to update the description section.")
        else:
            shutil.copy2(args.file, os.path.join(repo, "data", sha1))

    # add hardlink
    try:
        os.link(os.path.join(repo, "data", sha1), os.path.join(repo, "tags", os.path.basename(args.file)))

        # update json_desc
        json_data = _get_json_by_tag(filename)
        json_data['tags'].append(filename)
        json_data['Description'] = args.description

        # Create json object
        with open(os.path.join(repo, "desc", sha1), 'w') as f_w:
            json.dump(json_data, f_w)

    except FileExistsError:
        pass # This error is okay
    except:
        print("Unexpected error: {}".format(sys.exc_info()[0]), file=sys.stderr)
        raise


def rm(args):
    """
    Remove tag names or files from repository
    :param args: dict
    :return: None
    """
    repo = _get_repo_path()

    filename = args.file # No path allowed only filename

    sha1 = _get_data_tag(filename)

    try:
        # Remove the tag
        os.remove(os.path.join(repo, "tags", filename))
    except FileExistsError:
        sys.exit("Tag name '{}' does not exist".format(filename))
    except:
        print("Unexpected error: {}".format(sys.exc_info()[0]), file=sys.stderr)
        raise

    # Get inode count
    if os.lstat(os.path.join(repo, "data", sha1)).st_nlink == 1:
        print("No tags for '{}' do exist. Remove file and its description file from the repository".format(filename))
        # Remove also the data file
        os.remove(os.path.join(repo, "data", sha1))
        os.remove(os.path.join(repo, "desc", sha1))
    else:
        json_data = _get_json_by_sha1(sha1)
        json_data['tags'].remove(filename)

        # Save json object
        with open(os.path.join(repo, "desc", sha1), 'w') as f_w:
            json.dump(json_data, f_w)

        print("Following tags are still existing")
        for tag in json_data['tags']:
            print(tag)


def get(args):
    """
    Copy file from the repository
    :param args: dict
    :return: None
    """
    repo = _get_repo_path()

    tags = _get_repo_tags()

    filename = os.path.basename(args.file)

    if os.path.isfile(os.path.expanduser(args.target)):
        sys.exit("File already exists at {}".format(os.path.join(os.path.expanduser(args.target))))

    if filename in tags:
        src = os.path.join(repo, "tags", filename)
        dst = os.path.expanduser(args.target)
        try:
            # if compressed decompress it
            if magic.from_file(src, mime=True) == b'application/octet-stream':
                with open(src, 'rb') as f_r:
                    with open(dst, 'wb') as f_w:
                        f_w.write(zlib.decompress(f_r.read()))
            else:
                shutil.copy2(src, dst)
        except PermissionError:
            print("You have no write permissions at {}".format(os.path.expanduser(args.target)), file=sys.stderr)
        except:
            print("Unexpected error: {}".format(sys.exc_info()[0]), file=sys.stderr)
            raise


def tag(args):
    """
    Add new tag names for files in repository
    :param args: dict
    :return: None
    """
    repo = _get_repo_path()

    tags = _get_repo_tags()

    filename = os.path.basename(args.file)

    sha1 = _get_data_tag(filename)

    if filename in tags:
        if args.new_tag:
            try:
                os.link(os.path.join(repo, "tags", filename),
                        os.path.join(repo, "tags", os.path.basename(args.new_tag)))

                json_data = _get_json_by_tag(filename)
                json_data['tags'].append(args.new_tag)

                with open(os.path.join(repo, "desc", sha1), 'w') as f_w:
                    json.dump(json_data, f_w)

            except FileExistsError:
                print("Tag is already set")  # This error is okay
            except:
                sys.exit("Unexpected error: {}".format(sys.exc_info()[0]))

        inodes = _get_tags_inodes()

        print("Available tag names for file {}".format(filename))
        for tag in inodes[os.lstat(os.path.join(repo, "tags", filename)).st_ino]:
            print(tag)


def desc(args):
    """
    Output the description file for a tag or file
    :param args: dict
    :return: None
    """
    repo = _get_repo_path()

    filename = os.path.basename(args.file)

    sha1 = _get_data_tag(filename)

    if args.output:
        f = args.output
    else:
        f = sys.stdout.buffer

    json_data = _get_json_by_tag(filename)
    #with open(os.path.join(repo, "desc", _get_data_tag(filename)), 'r') as f_r:
    #    json_data = json.loads(f_r.read())

    if args.keys:
        for key in json_data:
            print(key)
    elif args.clear:
        json_data_new = {'tags':[],'repo_date':json_data['repo_date']}
        with open(os.path.join(repo, "desc", sha1), 'w') as f_w:
            json.dump(json_data_new, f_w)
    elif args.get is None and args.set is None:
        if args.format == Format(1).name: # markdown
            f.write(_get_markdown(json_data, filename).encode('utf-8'))
        elif args.format == Format(2).name: # html5
            header = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{}</title></head><body>'.format(filename)
            footer = '</body></html>'
            f.write((header + markdown(_get_markdown(json_data, filename), output_format='html5') + footer).encode('utf-8'))
        elif args.format == Format(3).name: # pdf
            options = {
                'page-size': 'A4',
                'encoding': "UTF-8"
            }
            f.write(pdfkit.from_string(markdown(_get_markdown(json_data, filename), output_format='html4'), False, options=options))
        elif args.format == Format(4).name: # json
            f.write(json.dumps(json_data,sort_keys=True, indent=2).encode('utf-8'))
        else:
            print("Unknown output format: {}".format(args.format), file=sys.stderr)
    elif args.get:
        if args.get in json_data:
            if isinstance(json_data[args.get], list):
                for item in json_data[args.get]:
                    print(item)
            else:
                print(json_data[args.get])
        else:
            print("'{}' is not defined yet. Use 'rms get --keys {}' to see all available keys".format(args.get, args.file))
    elif args.set:
        try:
            with open(args.set, "r") as f_r:
                json_new = json.loads(f_r.read())
        except:
            try:
                json_new = json.loads(args.set)
            except:
                sys.exit("{} is not a json file nor a json string".format(args.set))


        _dict_update(json_data, json_new)

        with open(os.path.join(repo, "desc", sha1), 'w') as f_w:
            json.dump(json_data, f_w)


if __name__ == "__main__":
    if DEBUG:
        # sys.argv.append("init")

        #sys.argv.append("add")
        #sys.argv.append("../test/app")
        #sys.argv.append("~/targets.ods")
        #sys.argv.append("This file is a simple test file from the file text. It is only here to test rms functionality.")

        sys.argv.append("rm")
        sys.argv.append(".bashrc")


        #sys.argv.append("get")
        #sys.argv.append("text")
        #sys.argv.append("~/test2")

        #sys.argv.append("tag")
        #sys.argv.append("app")
        #sys.argv.append("-n")
        #sys.argv.append("cp4")

        #sys.argv.append("desc")
        #sys.argv.append("app")
        #sys.argv.append("-g")
        #sys.argv.append("Description")
        #sys.argv.append("-f")
        #sys.argv.append("markdown")
        #sys.argv.append("-o")
        #sys.argv.append("/home/nauer/test.pdf")
        # sys.argv.append("-k")

       # sys.argv.append("--set")
        #sys.argv.append('../test/test.json')

        # sys.argv.append("-h")

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