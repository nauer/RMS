# RMS - Ressource Managment System for Linux

RSM should be a simple application which stores any kind of source files and its description on one place.

TODO
For example a typical fasta file including sequence data is simple text file with no ...

## Specifications
It should be easy to add new files while avoiding duplicate copies.

Version controlling (git) should be possible however it makes not much sense for big never changing data.
Such data should be stored in a zipped format. (-g -z options)

It should be possible to add several names to each file. The file itself is stored read-only under its
md5sum name only reachable over its assigned names.

It should be able to update files to a newer version. Simply within a git commit process or if not under
version control with th -f option to force the overwrite.

TODO

## Function Calls
rsm add <file-name> [<link-name> <g>]     link name is obligate if filename is unique under all link names
rsm checkout <link-name>
rsm update <link-name> <file-name> <commit> [<f>]
rsm edit-desc <link-name> <description>
rsm get-desc <link-name> <description>
rsm delete <link-name>
rsm get-path <link_name>
rsm clone <link-name>                               clone the git bare repository for this link. git pull and push possible (only for files under version control)
rsm cp <link-name> <path>                           copy file and file description file

TODO

## Misc
rsm repository pathname is simply exported in the environment

when adding a file automatically a description file is added which logs dates, commits and changes. (md5sum.desc)

TODO
