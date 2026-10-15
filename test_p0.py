import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import app
import parser
import test_audit


class ReadOnlyHTTPTests(unittest.TestCase):
    setUpClass=classmethod(test_audit.HTTPRegressionTests.setUpClass.__func__)
    tearDownClass=classmethod(test_audit.HTTPRegressionTests.tearDownClass.__func__)
    request=test_audit.HTTPRegressionTests.request

    def test_post_never_writes_and_has_no_cors(self):
        for path in ['/api/teacher/meta', '/api/groups', '/anything']:
            with patch.object(parser, 'save_teacher_meta_entry') as write:
                status, headers, body = self.request(path, method='POST', body='{"teacher_key":"A","photo":"https://evil.invalid/p.png"}', headers={'Origin':'https://evil.invalid'})
                self.assertEqual(status, 405)
                self.assertNotIn('Access-Control-Allow-Origin', headers)
                self.assertNotIn('POST', headers.get('Allow',''))
                write.assert_not_called()

    def test_invalid_lengths_and_transfer_encoding(self):
        for length in ['-1','8193','nope','+1']:
            status, headers, _ = self.request('/api/teacher/meta', method='POST', body='', headers={'Content-Length':length})
            self.assertEqual(status, 400)
            self.assertNotIn('Access-Control-Allow-Origin',headers)
        self.assertEqual(self.request('/api/teacher/meta', method='POST', body='', headers={'Transfer-Encoding':'chunked'})[0],400)

    def test_preflight_cannot_enable_post(self):
        status, headers, _ = self.request('/api/teacher/meta', method='OPTIONS', headers={'Origin':'https://evil.invalid','Access-Control-Request-Method':'POST'})
        self.assertEqual(status,405)
        self.assertNotIn('Access-Control-Allow-Origin',headers)
        self.assertNotIn('POST',headers.get('Access-Control-Allow-Methods',''))
        self.assertNotIn('Access-Control-Allow-Headers',headers)


class LocalAvatarTests(unittest.TestCase):
    def test_only_existing_local_raster_avatar_is_allowed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root=Path(directory);(root/'avatars').mkdir();(root/'avatars/photo.webp').write_bytes(b'fixture')
            with patch.object(parser,'AVATAR_ROOT',root):
                self.assertEqual(parser.local_teacher_photo('avatars/photo.webp'),'avatars/photo.webp')
                for value in ['https://esstu.ru/photo.png','http://evil.invalid/p.png','//evil.invalid/p.png','data:image/svg+xml,hi','javascript:alert(1)','avatars/../photo.webp','avatars/not-found.png','avatars/photo.svg','avatars/p.png" onerror="x',None]:
                    self.assertEqual(parser.local_teacher_photo(value),'',str(value))

    def test_legacy_remote_photo_is_ignored_and_writes_reject_it(self):
        with patch.object(parser,'load_teachers_meta',return_value={'иванов и.и.':{'photo':'https://ui-avatars.com/api/?name=A'}}):
            profile=parser.build_teacher_profile('Иванов И.И.')
            self.assertEqual(profile['photo'],'')
            self.assertTrue(profile['initials'])
        with self.assertRaises(ValueError):
            parser.save_teacher_meta_entry('Иванов И.И.',{'photo':'https://evil.invalid/p.png'})

    def test_tls_chain_and_hostname_checks_stay_enabled(self):
        context=app.create_esstu_ssl_context()
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        if hasattr(ssl,'OP_LEGACY_SERVER_CONNECT'):
            self.assertTrue(context.options & ssl.OP_LEGACY_SERVER_CONNECT)


if __name__=='__main__':
    unittest.main()
