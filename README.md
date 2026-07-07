# CBscripts

Comic Book Scripts is my personal comic book management system.

The idea is that CBscripts `scan` reads all your commic and stores the data in a sqlite db.
Subsequent scans append to that DB and make library management easier.

The intent is to set this up on my HomeLab to manage my collection of files stored as CBZ, CBR and in the future PDF (mainly because thats how Kickstarter projects are distributed).

Currently it:
- scans a library and stores available metadata in an SQLite db
- uses a user given json file for mapping publishers to given values, see `publisher_mapping.json`
- OPTIONALLY hashes all pages, compared against a json of known scanner pages and labels them deleted (does not actually delete) and fills out the `Scanner` field of the xml for propper attribution.

In the future, other commands in the package would:
- re/generate ComicInfo.xml
- force the CBZ/CBR formating across the library
- reorganise the library based on user specified directory structure layout

Far Future goals
- comicvine api access to identify missing issues in series
- comicvine api access to identify new issues in series
