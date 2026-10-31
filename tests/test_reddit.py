import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as E

from test_discover import module as d
import importlib.util
spec = importlib.util.spec_from_file_location('build', Path(__file__).resolve().parents[1] / 'scripts/build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)


def feed(*records):
    root = E.Element('{http://www.w3.org/2005/Atom}feed')
    for record in records:
        entry = E.SubElement(root, '{http://www.w3.org/2005/Atom}entry')
        values = dict(title='SSRI changed my identity', published='2026-10-30T12:00:00Z', content='', **{})
        values.update(record)
        url = values.pop('url', 'https://www.reddit.com/r/Buddhism/comments/abc123/title/')
        E.SubElement(entry, '{http://www.w3.org/2005/Atom}link', rel='self', href='https://example.org/api')
        E.SubElement(entry, '{http://www.w3.org/2005/Atom}link', rel='alternate', href=url)
        for key, value in values.items():
            if value is not None:
                E.SubElement(entry, '{http://www.w3.org/2005/Atom}' + key).text = value
    return root


class RedditTests(unittest.TestCase):
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)

    def collect(self, records, existing=None):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return d.discover_reddit(existing or [], self.now, lambda sub, q: feed(*records))

    def test_body_and_word_boundaries(self):
        self.assertEqual(len(self.collect([dict(title='I feel like myself again', content='<p>Escitalopram changed everything &amp; more</p>')])), 1)
        for title in ('Selfish medication', 'SSRI dosage', 'Buddhist no-self', 'SSRI egocentric thoughts'):
            with self.subTest(title=title):
                self.assertEqual(self.collect([dict(title=title)]), [])

    def test_duplicate_hosts_queries_slugs(self):
        records = [dict(url='https://old.reddit.com/r/Buddhism/comments/abc123/other/?utm_source=x#top'), dict()]
        self.assertEqual(len(self.collect(records)), 1)
        self.assertEqual(self.collect(records, [dict(url='https://redd.it/abc123')]), [])
        self.assertEqual(self.collect(records, [dict(url='https://www.reddit.com/r/Buddhism/comments/abc123/title/')]), [])

    def test_dates(self):
        for date in ('', None, 'invalid', '2026-10-30T12:00:00', '2026-11-01T00:00:00Z', '2026-10-01T00:00:00Z'):
            with self.subTest(date=date):
                self.assertEqual(self.collect([dict(published=date)]), [])
        self.assertEqual(self.collect([dict(published='2026-10-01T00:00:00Z', updated='2026-10-30T00:00:00Z')]), [])
        self.assertEqual(len(self.collect([dict(published=None, updated='2026-10-30T12:00:00+09:00')])), 1)

    def test_invalid_links(self):
        for url in ('javascript:alert(1)', 'https://evil.org/r/Buddhism/comments/abc123/title/', 'https://www.reddit.com/r/other/comments/abc123/title/', 'https://www.reddit.com/r/Buddhism/comments/abc123/title/commentid/'):
            self.assertEqual(self.collect([dict(url=url)]), [])

    def test_limit_newest_and_all_subreddits(self):
        calls = []
        def fetch(sub, query):
            calls.append(sub)
            return feed(*[dict(url=f'https://www.reddit.com/r/{sub}/comments/id{i}/title/', published=f'2026-10-{24+i:02}T12:00:00Z') for i in range(7)])
        added = d.discover_reddit([], self.now, fetch)
        self.assertEqual(len(added), 5)
        self.assertEqual(set(calls), {'Buddhism', 'secularbuddhism', 'lexapro'})
        self.assertTrue(added[0]['published'] > added[-1]['published'])

    def test_partial_and_total_failure_preserve_existing(self):
        existing = [dict(url='https://example.org/old')]
        before = copy.deepcopy(existing)
        def partial(sub, query):
            if sub == 'Buddhism':
                return feed(dict())
            raise OSError('403')
        self.assertEqual(len(d.discover_reddit(existing, self.now, partial)), 1)
        with self.assertRaises(RuntimeError):
            d.discover_reddit(existing, self.now, lambda *a: E.Element('html'))
        self.assertEqual(existing, before)

    def test_http_errors_and_invalid_xml(self):
        from urllib.error import HTTPError
        for error in (HTTPError('https://reddit.com', 403, 'Forbidden', {}, None), HTTPError('https://reddit.com', 429, 'Rate limited', {}, None), TimeoutError()):
            with patch.object(d, 'urlopen', side_effect=error), self.assertRaises(type(error)):
                d.fetch_reddit('Buddhism', 'SSRI')
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'<html>blocked</html>'
        with patch.object(d, 'urlopen', return_value=response), self.assertRaises(ValueError):
            d.fetch_reddit('Buddhism', 'SSRI')
        response.__enter__.return_value.read.return_value = b'broken xml'
        with patch.object(d, 'urlopen', return_value=response), self.assertRaises(E.ParseError):
            d.fetch_reddit('Buddhism', 'SSRI')

    def test_hn_failure_does_not_skip_reddit(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'articles.json'
            data.write_text('[]')
            article = dict(url='https://example.org/new')
            with patch.object(d, 'DATA', data), patch.object(d, 'discover', side_effect=RuntimeError('HN down')), patch.object(d, 'discover_reddit', return_value=[article]):
                self.assertEqual(d.main(), 1)
                self.assertEqual(json.loads(data.read_text()), [article])

    def test_all_sources_fail_no_write(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder) / 'articles.json'
            data.write_text('[]\n')
            with patch.object(d, 'DATA', data), patch.object(d, 'discover', side_effect=RuntimeError('HN down')), patch.object(d, 'discover_reddit', side_effect=RuntimeError('Reddit down')), self.assertRaises(RuntimeError):
                d.main()
            self.assertEqual(data.read_text(), '[]\n')


class FeedCompatibilityTests(unittest.TestCase):
    def test_build_preserves_old_feeds_and_opml(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            (target / 'data').mkdir()
            (target / 'data/articles.json').write_bytes((root / 'data/articles.json').read_bytes())
            with patch.object(b, 'ROOT', target):
                b.main()
            for key in ('magnolia', 'rustj', 'lexical', 'array-compilers'):
                self.assertEqual((target / f'docs/{key}.xml').read_bytes(), (root / f'docs/{key}.xml').read_bytes())
            for path in (target / 'docs').glob('*.xml'):
                self.assertEqual(E.parse(path).getroot().tag, 'rss')
            opml = E.parse(root / 'subscriptions.opml')
            urls = [x.get('xmlUrl') for x in opml.findall('.//outline[@type="rss"]')]
            self.assertEqual(len(urls), len(set(urls)))
            for key in (*b.PROJECTS, 'all'):
                self.assertIn(b.BASE + '/' + key + '.xml', urls)

    def test_pubdate_uses_original_instant_and_escapes_xml(self):
        article = dict(title='Self & SSRI <discussion>', url='https://example.org/a', summary='A & B', insight='<review>', added='2026-10-31', published='2026-10-30T12:00:00+09:00')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'feed.xml'
            b.write_feed(path, 'Test', [article])
            item = E.parse(path).find('channel/item')
            self.assertEqual(item.findtext('title'), article['title'])
            self.assertEqual(item.findtext('pubDate'), 'Fri, 30 Oct 2026 03:00:00 +0000')
