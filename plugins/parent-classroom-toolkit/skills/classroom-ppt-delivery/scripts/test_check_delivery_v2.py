"""Failure-path checks for optional evidence and version/package mismatches."""
import json, tempfile, unittest
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import patch
from PIL import Image
from check_delivery import digest
from check_delivery_v2 import audit, guard_output


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.parent=Path(__file__).resolve().parent
        self.tmp=tempfile.TemporaryDirectory(prefix='migration_test_',dir=self.parent)
        self.root=Path(self.tmp.name).resolve()
        self.assertEqual(self.root.parent,self.parent)
        delivery=self.root/'delivery';delivery.mkdir()
        with ZipFile(delivery/'deck.pptx','w') as z:z.writestr('dummy','valid archive')
        (delivery/'script.txt').write_text('第1页｜标题\n\n口播\n\n\n',encoding='utf-8')
        images=delivery/'images';images.mkdir()
        Image.new('RGB',(16,9)).save(images/'01.png')
        self.cfg={'workspace_root':'.','audit_date':'fixture','baseline':{'pptx':'delivery/deck.pptx','transcript':'delivery/script.txt','images':'delivery/images','delivery_folder':'delivery'}}
        self.actual={'slides':1,'sha256':digest((delivery/'deck.pptx').read_bytes()),'pages':[{'page':1,'notes':'第1页｜标题\n\n口播','visible_text':'标题','notes_relationship_count':1,'native_text_shapes':1,'has_timing_element':False}]}

    def tearDown(self):self.tmp.cleanup()

    def run_audit(self):
        p=self.root/'config.json';p.write_text(json.dumps(self.cfg),encoding='utf-8')
        with patch('check_delivery_v2.inspect_pptx',return_value=self.actual):return audit(p)

    def test_missing_evidence_never_becomes_full_pass(self):
        r=self.run_audit()
        self.assertEqual(r['exit_code'],3)
        self.assertIsNone(r['timing'])
        self.assertEqual(next(c['status'] for c in r['checks'] if c['id']=='historical_manifest'),'未检查')

    def test_changed_speech_is_a_failure(self):
        (self.root/'delivery/script.txt').write_text('第1页｜标题\n\n错误口播\n',encoding='utf-8')
        r=self.run_audit()
        self.assertEqual(r['exit_code'],2)
        self.assertFalse(r['page_checks'][0]['notes_match_txt_strict'])

    def test_explicit_zip_prefix_and_changed_member(self):
        self.cfg['baseline'].update({'zip':'pack.zip','zip_prefix':'lesson/'})
        with ZipFile(self.root/'pack.zip','w') as z:
            for p in (self.root/'delivery').rglob('*'):
                if p.is_file():z.writestr('lesson/'+p.relative_to(self.root/'delivery').as_posix(),p.read_bytes())
        self.assertTrue(self.run_audit()['zip']['identical'])
        (self.root/'delivery/script.txt').write_text('different',encoding='utf-8')
        r=self.run_audit()
        self.assertEqual(r['zip']['different'],['script.txt'])
        self.assertEqual(r['exit_code'],2)

    def test_reports_cannot_overwrite_delivery(self):
        self.run_audit()
        with self.assertRaises(ValueError):guard_output(self.root/'config.json',self.root/'delivery/result.json')
        with self.assertRaises(ValueError):guard_output(self.root/'config.json',self.root/'config.json')

    def test_root_level_zip_input_is_protected(self):
        self.cfg['baseline']['zip']='pack.zip'
        p=self.root/'config.json';p.write_text(json.dumps(self.cfg),encoding='utf-8')
        with self.assertRaises(ValueError):guard_output(p,self.root/'pack.zip')

if __name__=='__main__':unittest.main()
