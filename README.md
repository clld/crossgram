Source code of the Crossgram Webapp
===================================

TODO: add link when webapp is public

Rebuilding the database(s)
--------------------------

### Prerequisite: Concepticon

Crossgram relies on data from the [Glottolog][glottlog] reference catalogue.  It
will find it using [cldfcatalog][cldfcatalog].

[glottolog]: https://github.com/glottolog/glottolog
[cldfcatalog]: https://github.com/cldf/cldfcatalog

### Internal vs external datasets

There are two sets of datasets for Crossgram:  The internal datasets and the
external datasets.  *External datasets* are the ones that have been released to
the public.  *Internal datasets* are the ones that are still being worked on and
that get served to a separate instance of the webapp, so the editors can give
the authors a preview on what their datasets will look like.

The metadata for both internal and external datasets is contained in the private
`crossgram/crossgram-intern` repository.  The `clld initdb` script will look for
a clone of this repository in `../../crossgram/crossgram-intern`.  The
`crossgram-intern` repo also contains documentaion on how to curate the
datasets.

### Database initialisation

Thie `clld initdb` script will ask two questions:

 1. Do you want to load the internal or external datasets into the database?
    (`e` for external, `i` for internal)
 2. Do you want to add *all* or just one specific dataset to the database?
    This is useful for quick testing during development – repopulating the
    entire database can take a minute or two.

We usually load the internal and external datasets into separate databases:

    $ clld initdb development.ini
    ...
    [i]nternal or [e]xternal data (default: e): e
    submission id or 'all' for all submissions (default: all): all

    $ clld initdb development-intern.ini
    ...
    [i]nternal or [e]xternal data (default: e): i
    submission id or 'all' for all submissions (default: all): all
