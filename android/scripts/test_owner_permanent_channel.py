import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import owner_permanent_channel as ch

class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'persistent-owner-key'
    def test_actual_keytool_initializes_local_identity_and_rejects_rekey(self):
        ch.init(self.folder,'keytool')
        meta=json.loads((self.folder/ch.CHANNEL).read_text())
        self.assertEqual(meta['application_id'],'org.unovyra.uno')
        self.assertTrue((self.folder/ch.KEYFILE).stat().st_size>1000)
        self.assertEqual(ch.key_digest(self.folder,ch.signing_env(self.folder),'keytool'),meta['signer_sha256'])
        self.assertEqual(len(meta['signer_sha256']),64)
        with self.assertRaisesRegex(ValueError,'ALREADY_EXISTS'):
            ch.init(self.folder,'keytool')
        self.assertEqual(meta,json.loads((self.folder/ch.CHANNEL).read_text()))
        return meta
    def test_owner_dir_must_not_be_inside_repo(self):
        with self.assertRaisesRegex(ValueError,'OUTSIDE_GIT_REPOSITORY'):
            ch.owner_path(ch.ANDROID / 'dist' / 'secrets')
        with self.assertRaisesRegex(ValueError,'ABSOLUTE'):
            ch.owner_path(Path('owner-key'))
    def test_never_run_on_github_actions(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS':'true'}):
            with self.assertRaisesRegex(ValueError,'GITHUB_ACTIONS'):
                ch.init(self.folder,'keytool')
        self.assertFalse(self.folder.exists())
    def test_single_identity_first_and_second_versions_with_mock_gradle(self):
        ch.init(self.folder,'keytool')
        fingerprint = json.loads((self.folder/ch.CHANNEL).read_text())['signer_sha256']
        old_android=ch.ANDROID
        build_dir=self.root/'android'
        (build_dir/'app/build/outputs/apk/debug').mkdir(parents=True)
        ch.ANDROID=build_dir
        self.addCleanup(lambda: setattr(ch,'ANDROID',old_android))
        args=[]
        original_command=ch.command
        def fake_command(argv, **kwargs):
            if argv[0]=='keytool':
                return original_command(argv,**kwargs)
            args.append(argv)
            self.assertEqual(argv[0],'fake-gradle')
            self.assertIn('--max-workers=1', argv)
            self.assertGreaterEqual(kwargs.get('timeout', 0), 3600)
            version=int(next(a.split('=')[1] for a in argv if a.startswith('-PunoOwnerUpdateVersionCode=')))
            (build_dir/'app/build/outputs/apk/debug/app-debug.apk').write_bytes(f'fake v{version}'.encode())
            return 'mock, NO SDK'
        def fake_inspect(apk,aapt,apksigner):
            version=int(apk.read_bytes().decode().split('v')[1])
            return ch.ApkIdentity(ch.APP_ID,version,(fingerprint,))
        with patch.object(ch,'command',side_effect=fake_command),patch.object(ch,'inspect',side_effect=fake_inspect):
            ch.build(self.folder,'keytool','fake-gradle','fake-aapt','fake-apksigner')
            ch.build(self.folder,'keytool','fake-gradle','fake-aapt','fake-apksigner')
            releases=list((self.folder/'releases').iterdir())
            self.assertEqual(len(releases),4)
            self.assertEqual([int(next(x.split('=')[1] for x in a if x.startswith('-PunoOwnerUpdateVersionCode='))) for a in args],[1,2])
            for a in args:
                self.assertIn('-PunoOwnerUpdateApplicationId=org.unovyra.uno',a)
                self.assertNotIn('-PunoIsolatedDebugSuffix', ' '.join(a))
                self.assertNotIn('install', ' '.join(a))
            self.assertEqual(ch.last_release(self.folder,fingerprint,'aapt','apksigner').version_code,2)
            # Reject corrupted historical output rather than issuing a new version.
            apk=next((self.folder/'releases').glob('uno-v2-*.apk'))
            apk.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'INTEGRITY'):
                ch.build(self.folder,'keytool','fake-gradle','fake-aapt','fake-apksigner')
    def test_invalid_metadata_fails_closed(self):
        ch.init(self.folder,'keytool')
        p=self.folder/ch.CHANNEL
        x=json.loads(p.read_text()); x['application_id']='org.bad.app'
        p.write_text(json.dumps(x))
        with self.assertRaisesRegex(ValueError,'METADATA_INVALID'):
            ch.load_channel(self.folder,'keytool')

if __name__=='__main__':unittest.main(verbosity=2)
