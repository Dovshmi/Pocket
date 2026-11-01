import tempfile
import unittest
from pathlib import Path

from shortcut_drop import guess_shortcut


class ShortcutDropTests(unittest.TestCase):
    def test_github_repo_url(self):
        result = guess_shortcut('https://github.com/Dovshmi/Pocket')
        self.assertEqual(result, {'kind': 'url', 'url': 'https://github.com/Dovshmi/Pocket',
                                  'title': 'Pocket · GitHub'})

    def test_http_url_with_params(self):
        result = guess_shortcut('https://www.youtube.com/watch?v=AbC')
        self.assertEqual(result['kind'], 'url')
        self.assertEqual(result['title'], 'YouTube')

    def test_browser_uri_list(self):
        result = guess_shortcut('# comment\nhttps://example.com\r\n')
        self.assertEqual(result['kind'], 'url')

    def test_local_file_with_spaces(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'my work notes.txt'
            f.write_text('test')
            result = guess_shortcut(str(f), splitlist=lambda raw: raw.split())
            self.assertEqual(result['kind'], 'file')
            self.assertEqual(result['title'], 'my work notes')
            self.assertEqual(result['url'], str(f.resolve()))

    def test_braced_tcl_file_path(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'my work notes.txt'
            f.write_text('test')
            result = guess_shortcut('{' + str(f) + '}', splitlist=lambda raw: [raw[1:-1]])
            self.assertEqual(result['kind'], 'file')

    def test_folder(self):
        with tempfile.TemporaryDirectory() as d:
            result = guess_shortcut(d)
            self.assertEqual(result['kind'], 'folder')
            self.assertEqual(result['title'], Path(d).name)

    def test_url_shortcut_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'sample.url'
            f.write_text('[InternetShortcut]\nURL=https://example.com\n', encoding='utf-8')
            result = guess_shortcut(str(f))
            self.assertEqual(result['kind'], 'url')
            self.assertEqual(result['url'], 'https://example.com')

    def test_multiple_file_drop_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            a = Path(d) / 'a.txt'
            b = Path(d) / 'b.txt'
            a.touch(); b.touch()
            with self.assertRaisesRegex(ValueError, 'one'):
                guess_shortcut('{' + str(a) + '} {' + str(b) + '}',
                               splitlist=lambda _raw: [str(a), str(b)])

    def test_multiple_urls_rejected(self):
        with self.assertRaisesRegex(ValueError, 'one'):
            guess_shortcut('https://foo.example\nhttps://bar.example')

    def test_invalid_text_rejected(self):
        with self.assertRaises(ValueError):
            guess_shortcut('not a web address')

    def test_unsafe_scheme_rejected(self):
        with self.assertRaises(ValueError):
            guess_shortcut('javascript:alert(1)')

    def test_nonexistent_path_rejected(self):
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            guess_shortcut('/folder/that/does-not-exist/for/sure')

    def test_no_drop_data(self):
        with self.assertRaises(ValueError):
            guess_shortcut('')


if __name__ == '__main__':
    unittest.main()
