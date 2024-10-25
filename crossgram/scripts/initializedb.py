import pathlib
import re
from datetime import date

import cldfcatalog
import cldfzenodo
import git
import sqlalchemy
from clld.cliutil import Data
from clld.db.meta import DBSession
from clld.db.models import common
from clld_glottologfamily_plugin.util import load_families
from clldutils import jsonlib
from clldutils.misc import slug
from csvw import dsv
from markdown import markdown
from pyglottolog import Glottolog

import crossgram
from crossgram import models
from crossgram.lib.cldf import CLDFBenchSubmission
from crossgram.lib.cldf_zenodo import download_from_doi
from crossgram.lib.horrible_denormaliser import BlockEncoder


def download_data(sid, contrib_md, cache_dir):
    if contrib_md.get('doi'):
        doi = contrib_md['doi']
        path = cache_dir / f'{sid}-{slug(doi)}'
        if not path.exists():
            print(' * downloading dataset from Zenodo; doi:', doi)
            download_from_doi(doi, path)
            print('   done.')
        return path

    elif contrib_md.get('repo'):
        repo = contrib_md.get('repo')
        checkout = contrib_md.get('checkout')
        if checkout:
            # specific commit/tag/branch
            path = cache_dir / f'{sid}-{slug(checkout)}'
            if not path.exists():
                print(' * cloning', repo, 'into', path, '...')
                git.Git().clone(repo, path)
                print('   done.')
                print(' * checking out commit', checkout, '...')
                git.Git(str(path)).checkout(checkout)
                print('   done.')
        else:
            # latest commit on the default branch
            path = cache_dir / sid
            if not path.exists():
                print(' * cloning', repo, 'into', path, '...')
                git.Git().clone(repo, path)
                print('   done.')
            else:
                print(' * pulling latest commit')
                git.Git(str(path)).pull()
                print('   done.')
        return path

    else:
        return cache_dir / sid


def maybe_read_file(file_path):
    try:
        with open(file_path, encoding='utf-8') as f:
            return f.read()
    except IOError:
        # if there is no intro just return nothing
        return None


def collect_language_sources():
    existing_sources = set(DBSession.execute(
        sqlalchemy.select(
            models.LanguageReference.language_pk,
            models.LanguageReference.source_pk)
        .distinct()))

    language_sources = set(DBSession.execute(
        sqlalchemy.select(
            common.ValueSet.language_pk,
            common.ValueSetReference.source_pk)
        .join(common.ValueSetReference.valueset)
        .distinct()))
    language_sources.update(DBSession.execute(
        sqlalchemy.select(
            common.Unit.language_pk,
            models.UnitValueReference.source_pk)
        .join(models.UnitValueReference.unitvalue)
        .join(common.UnitValue.unit)
        .distinct()))
    language_sources.update(DBSession.execute(
        sqlalchemy.select(
            common.Unit.language_pk,
            models.UnitReference.source_pk)
        .join(models.UnitReference.unit)
        .distinct()))
    language_sources = sorted(language_sources - existing_sources)

    DBSession.add_all(
        models.LanguageReference(
            language_pk=language_pk,
            source_pk=source_pk)
        for language_pk, source_pk in language_sources)


def main(args):
    internal = input('[i]nternal or [e]xternal data (default: e): ').strip().lower() == 'i'
    which_submission = input("submission id or 'all' for all submissions (default: all): ").strip().lower() or 'all'

    all_languages = {}
    all_contributors = {}

    dataset = common.Dataset(
        id=crossgram.__name__,
        name='CrossGram',
        description='CrossGram',
        published=date(2019, 12, 12),
        contact='martin_haspelmath@eva.mpg.de',
        domain='crossgram.clld.org',
        publisher_name='Max Planck Institute for Evolutionary Anthropology',
        publisher_place='Leipzig',
        publisher_url='https://www.eva.mpg.de',
        license='http://creativecommons.org/licenses/by/4.0',
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'})
    DBSession.add(dataset)

    DBSession.flush()

    raw_editors = [
        ('haspelmathmartin', 'Martin Haspelmath'),
    ]
    all_contributors.update(
        (editor_id, common.Contributor(id=editor_id, name=name))
        for editor_id, name in raw_editors)
    DBSession.add_all(all_contributors.values())

    DBSession.flush()

    DBSession.add_all(
        common.Editor(
            dataset_pk=dataset.pk,
            contributor_pk=contributor.pk,
            ord=ord)
        for ord, contributor in enumerate(all_contributors.values(), 1))

    internal_repo = pathlib.Path('../../crossgram/crossgram-internal')
    cache_dir = internal_repo / 'datasets'
    cache_dir.mkdir(exist_ok=True)

    grammaticon_repo = pathlib.Path('../grammaticon-data/csvw')
    csv_topics = (
        {k: v for k, v in csv_topic.items() if v}
        for csv_topic in dsv.iterrows(
            grammaticon_repo / 'concepts.csv', dicts=True))
    topics = {
        topic.get('Grammacode') or topic['ID']: models.Topic(
            id=topic.get('Grammacode') or topic['ID'],
            name=topic['Name'],
            description=topic.get('Description'),
            grammacode=topic.get('Grammacode'),
            comment=topic.get('Comment'),
            quotation=topic.get('Quotation'),
            croft_counterpart=topic.get('Croft_Counterpart'),
            croft_description=topic.get('Croft_Description'),
            wikipedia_counterpart=topic.get('Wikipedia_Counterpart'),
            wikipedia_url=topic.get('Wikipedia_URL'))
        for topic in csv_topics}
    DBSession.add_all(topics.values())

    if internal:
        submissions_path = internal_repo / 'submissions-internal'
    else:
        submissions_path = internal_repo / 'submissions'

    for contrib_dir in submissions_path.iterdir():
        if not contrib_dir.is_dir():
            continue
        if which_submission != 'all' and which_submission != contrib_dir.name:
            continue
        sid = contrib_dir.name
        print('Loading submission', sid, '...')

        contrib_md = jsonlib.load(contrib_dir / 'md.json')
        if contrib_md.get('hide'):
            print('... but', sid, "doesn't want to be shown")
            continue

        cldfbench_path = download_data(sid, contrib_md, cache_dir)
        if not cldfbench_path.exists():
            print('could not find folder', str(cldfbench_path))
            continue

        doi = contrib_md.get('doi')
        if doi:
            version = cldfzenodo.API.get_record(doi=doi).version
        else:
            version = None

        submission = CLDFBenchSubmission.load(cldfbench_path, contrib_md)

        date_match = re.fullmatch(r'(\d+)-(\d+)-(\d+)', contrib_md['published'])
        assert date_match
        yyyy, mm, dd = date_match.groups()
        published = date(int(yyyy), int(mm), int(dd))

        # strip ssh stuff off of git link
        git_https = re.sub(
            '^git@([^:]*):', r'https://\1/', contrib_md.get('repo') or '')

        intro = (
            maybe_read_file(contrib_dir / 'intro.md')
            or maybe_read_file(cldfbench_path / 'raw' / 'intro.md')
            or submission.readme)

        contrib = models.CrossgramData(
            id=sid,
            number=int(contrib_md['number']),
            published=published,
            original_year=contrib_md.get('original-year') or str(published.year),
            name=contrib_md.get('title') or submission.title,
            doi=doi,
            version=version,
            git_repo=git_https,
            description=intro)
        DBSession.add(contrib)

        DBSession.flush()

        new_languages, new_contributors = submission.add_to_database(
            contrib, all_languages, all_contributors, topics)
        all_languages.update(
            (language.id, language)
            for language in new_languages)
        all_contributors.update(
            (contributor.id, contributor)
            for contributor in new_contributors)

        print('... done')

    DBSession.flush()
    print('Loading language family data...')
    catconf = cldfcatalog.Config.from_file()
    glottolog_path = catconf.get_clone('glottolog')
    languages_in_glottolog = [
        language
        for language_id, language in all_languages.items()
        if re.fullmatch('[a-z]{4}[0-9]{4}', language_id)]
    load_families(
        Data(),
        languages_in_glottolog,
        strict=False,
        glottolog_repos=glottolog_path)
    print('... done')

    print('Collecting language sources...')
    collect_language_sources()
    DBSession.flush()
    print('... done')


def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """

    print('Parsing markdown intros...')
    for contrib in DBSession.query(models.Contribution):
        if contrib.description:
            contrib.markup_description = markdown(contrib.description)
        else:
            contrib.markup_description = None
    print('... done')

    print('Retrieving language data from glottolog...')

    catconf = cldfcatalog.Config.from_file()
    glottolog_path = catconf.get_clone('glottolog')
    glottolog = Glottolog(glottolog_path)

    db_languages = {
        language.id: language
        for language in DBSession.query(common.Language)}
    glottolog_languages = {
        languoid.id: languoid
        for languoid in glottolog.languoids(db_languages)}

    glottocodes = {
        languoid.id: common.Identifier(
            id=languoid.id,
            name=languoid.id,
            type='glottolog')
        for languoid in glottolog_languages.values()}
    isocodes = {
        languoid.id: common.Identifier(
            id=isocode,
            name=isocode,
            type='iso639-3')
        for languoid in glottolog_languages.values()
        if (isocode := languoid.iso)}

    print('...done')
    print('Denormalising language info (glottocodes, macroarea, alt names, etc.)')

    for obj in DBSession.query(common.LanguageIdentifier).all():
        DBSession.delete(obj)
    for obj in DBSession.query(common.Identifier).all():
        DBSession.delete(obj)

    DBSession.flush()

    DBSession.add_all(glottocodes.values())
    DBSession.add_all(isocodes.values())

    DBSession.flush()

    DBSession.add_all(
        common.LanguageIdentifier(
            language_pk=language.pk,
            identifier_pk=identifier.pk)
        for language in db_languages.values()
        if (identifier := glottocodes.get(language.id)))
    DBSession.add_all(
        common.LanguageIdentifier(
            language_pk=language.pk,
            identifier_pk=identifier.pk)
        for language in db_languages.values()
        if (identifier := isocodes.get(language.id)))

    name_encoder = BlockEncoder()
    source_encoder = BlockEncoder()
    contrib_lang_query = DBSession.query(models.ContributionLanguage)\
        .join(models.Language)
    for contrib_lang in contrib_lang_query:
        lang_id = contrib_lang.language.id
        contrib_pk = contrib_lang.contribution_pk
        name_encoder.record_value(
            lang_id, contrib_pk, contrib_lang.custom_language_name)
        source_encoder.record_value(
            lang_id, contrib_pk, contrib_lang.source_comment)

    for language in db_languages.values():
        if (languoid := glottolog_languages.get(language.id)):
            language.glottolog_id = languoid.id
            language.name = languoid.name
            language.latitude = languoid.latitude
            language.longitude = languoid.longitude
            language.macroarea = languoid.macroareas[0].name if languoid.macroareas else ''

        language.source_comments = source_encoder.encode(language.id)
        language.custom_names = name_encoder.encode(
            language.id, language.name)

    DBSession.flush()
    print('... done')

    print('Counting things...')

    # language representation for l-parameters
    DBSession.execute(sqlalchemy.text("""
        UPDATE lparameter
        SET language_count = s.c
        FROM (
            SELECT parameter_pk, count(distinct(language_pk)) AS c
            FROM valueset
            GROUP BY parameter_pk
        ) AS s
        WHERE lparameter.pk = s.parameter_pk
    """))

    # language representation for l-parameter codes
    DBSession.execute(sqlalchemy.text("""
        UPDATE lcode
        SET language_count = s.c
        FROM (
            SELECT domainelement_pk, count(distinct(language_pk)) AS c
            FROM value
            JOIN valueset ON valueset.pk = valueset_pk
            WHERE domainelement_pk IS NOT NULL
            GROUP BY domainelement_pk
        ) AS s
        WHERE lcode.pk = s.domainelement_pk
    """))

    # language representation for c-parameters
    DBSession.execute(sqlalchemy.text("""
        UPDATE cparameter
        SET language_count = s.c
        FROM (
            SELECT unitparameter_pk, count(distinct(language_pk)) AS c
            FROM unitvalue
            JOIN unit ON unit.pk = unitvalue.unit_pk
            GROUP BY unitparameter_pk
        ) AS s
        WHERE cparameter.pk = s.unitparameter_pk
    """))

    # language representation for c-parameter codes
    DBSession.execute(sqlalchemy.text("""
        UPDATE ccode
        SET language_count = s.c
        FROM (
            SELECT unitdomainelement_pk, count(distinct(language_pk)) AS c
            FROM unitvalue
            JOIN unit ON unit.pk = unitvalue.unit_pk
            WHERE unitdomainelement_pk IS NOT NULL
            GROUP BY unitdomainelement_pk
        ) AS s
        WHERE ccode.pk = s.unitdomainelement_pk
    """))

    # examples per language
    DBSession.execute(sqlalchemy.text("""
        UPDATE variety
        SET example_count = s.c
        FROM (
            SELECT language_pk, count(sentence.pk) AS c
            FROM sentence
            GROUP BY language_pk
        ) AS s
        WHERE variety.pk = s.language_pk
    """))

    DBSession.flush()
    print('... done')
