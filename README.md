# RMS - Ressource Managment System for Linux
RMS should be a simple application storing any kind of source files and its description on one place.
For example a typical fasta file including sequence data is simple text file with no ...

## Features
It should be easy to add new files while avoiding duplicate copies.

Version controlling (git) should be possible however it makes not much sense for big never changing data.
Such data should be stored in a zipped format. (-g -z options)

It should be possible to add several names to each file. The file itself is stored read-only under its
md5sum name only reachable over its assigned names.

It should be able to update files to a newer version. Simply within a git commit process or if not under
version control with th -f option to force the overwrite.


## Function Calls
rms add <file-name> [<link-name> <g>]               link name is obligate if filename is unique under all link names
rms checkout <link-name> [link-name, ...]
rms update <link-name> <file-name> <commit> [<f>]
rms edit-desc <link-name> <description>
rms get-desc <link-name> <description>
rms delete <link-name>
rms get-path <link_name>
rms clone <link-name>                               clone the git bare repository for this link. git pull and push possible (only for files under version control)
rms cp <link-name> <path>                           copy file and file description file
rms rm <link-name>                                  only possible if all other link-names were removed before
rms list [link-name]                                list all files with its linked names. If link-name is specified only list link-names of this file
rms share <path> [<link-name>, ...]                 create a copy of the repository or if link-names are given create a new repository with given files
rms get-md5 <link-name> [<link-name, ...]           return md5sum hash values of the files

## Misc
rms repository pathname is simply exported in the environment.

<rms-path>
|_<.rms>
  |_<git-bare>
  | |_521ae885a8ecfe35c07e1cc7cba92adf.git
  | |_521ae885a8ecfe35c07e1cc7cba92adf.git.desc
  | |_941708b9bdeff4e4b69c5a55d9a71c91.git
  | |_941708b9bdeff4e4b69c5a55d9a71c91.git.desc
  |_<local>
  | |_0236ac5524512693aa8c1ef5c27954be
  | |_0236ac5524512693aa8c1ef5c27954be.desc
  | |_ecb6d3479ac3823f1da7f314d871989b
  | |_ecb6d3479ac3823f1da7f314d871989b.desc
  |_<git>
  | |_<521ae885a8ecfe35c07e1cc7cba92adf>
  |   |_521ae885a8ecfe35c07e1cc7cba92adf
  |_config
  |_<links>
    |_File_A -> <local>/0236ac5524512693aa8c1ef5c27954be*
    |_File_B -> <local>/ecb6d3479ac3823f1da7f314d871989b*
    |_B -> <local>/ecb6d3479ac3823f1da7f314d871989b*
    |_git_File_C -> <git>/<521ae885a8ecfe35c07e1cc7cba92adf>/521ae885a8ecfe35c07e1cc7cba92adf*

when adding a file automatically a description file is added which logs dates, commits and changes. (md5sum.desc)

perl, python and R APIs possible.

web interface with user management would be practicable over RESTFUL API (Laravel 5.1)

description files should be in markdown to create simply html or pdfs out of it

## Files
rms -> <bin>/rms.py   pythons awesome argparse module parse the rms options and runs all the other bash, python scripts
<bin>/add.sh
