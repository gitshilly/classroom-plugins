"""Checks failure detection and real relationship ordering, not presentation quality."""
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from check_delivery import NS, inspect_pptx, script_pages, normalize, compare_maps, timing


class AuditTests(unittest.TestCase):
    def test_relationship_order_and_notes_body(self):
        test_root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(prefix='audit_test_', dir=test_root) as tmp:
            # Only this newly created, verified child directory is auto-cleaned.
            self.assertEqual(Path(tmp).resolve().parent, test_root)
            path = Path(tmp) / 'sample.pptx'
            relns = 'http://schemas.openxmlformats.org/package/2006/relationships'
            def rels(items):
                return f'<Relationships xmlns="{relns}">' + ''.join(f'<Relationship Id="{rid}" Target="{target}" Type="{NS["r"]}/{typ}"/>' for rid, target, typ in items) + '</Relationships>'
            def shape(kind, text):
                return f'<p:sp><p:nvSpPr><p:nvPr><p:ph type="{kind}"/></p:nvPr></p:nvSpPr><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp>'
            def tree(tag, text):
                return f'<p:{tag} xmlns:p="{NS["p"]}" xmlns:a="{NS["a"]}"><p:cSld><p:spTree>{text}</p:spTree></p:cSld></p:{tag}>'
            with ZipFile(path, 'w') as z:
                z.writestr('ppt/presentation.xml', f'<p:presentation xmlns:p="{NS["p"]}" xmlns:r="{NS["r"]}"><p:sldIdLst><p:sldId id="256" r:id="r9"/><p:sldId id="257" r:id="r2"/></p:sldIdLst></p:presentation>')
                z.writestr('ppt/_rels/presentation.xml.rels', rels([('r2', 'slides/slide1.xml', 'slide'), ('r9', 'slides/slide3.xml', 'slide')]))
                for slide, note, speech in [(3, 5, '第一段'), (1, 4, '第二段')]:
                    z.writestr(f'ppt/slides/slide{slide}.xml', tree('sld', shape('title', f'页{slide}')))
                    z.writestr(f'ppt/slides/_rels/slide{slide}.xml.rels', rels([('n', f'../notesSlides/notesSlide{note}.xml', 'notesSlide')]))
                    z.writestr(f'ppt/notesSlides/notesSlide{note}.xml', tree('notes', shape('sldNum', '999') + shape('body', speech)))
            result = inspect_pptx(path)
            self.assertEqual([p['slide_part'] for p in result['pages']], ['ppt/slides/slide3.xml', 'ppt/slides/slide1.xml'])
            self.assertEqual([p['notes'] for p in result['pages']], ['第一段', '第二段'])

    def test_whitespace_not_silently_discarded(self):
        self.assertEqual(normalize('a\r\nb'), normalize('a\nb'))
        self.assertNotEqual(normalize('a\n\nb'), normalize('a\nb'))
        self.assertNotEqual(normalize('不，正确'), normalize('不正确'))

    def test_blank_lines_including_last_page(self):
        rows = script_pages('第1页｜甲\n\n口播\n\n\n第2页｜乙\n\n口播\n')
        self.assertEqual([r['trailing_blank_lines'] for r in rows], [2, 0])

    def test_package_missing_extra_and_changed(self):
        result = compare_maps({'pptx': 'a', 'notes': 'b', '01.png': 'c'}, {'pptx': 'a', 'notes': 'wrong', 'old.txt': 'd'})
        self.assertFalse(result['identical'])
        self.assertEqual(result['missing'], ['01.png'])
        self.assertEqual(result['extra'], ['old.txt'])
        self.assertEqual(result['different'], ['notes'])

    def test_timing_excludes_prompt_and_keeps_wait(self):
        result = timing([{'page': 1, 'notes': '第1页｜标题\n\n一二三【静看十秒】', 'wait_seconds': 10, 'seconds': 20}], [60])
        self.assertEqual(result['spoken_hanzi'], 3)
        self.assertEqual(result['scenarios'][0]['total_seconds'], 16)


if __name__ == '__main__':
    unittest.main()
