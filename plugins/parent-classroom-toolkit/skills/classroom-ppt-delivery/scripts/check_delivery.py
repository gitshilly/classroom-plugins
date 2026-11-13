"""Read-only delivery audit. Writes only the explicitly selected report file.

This checks files, not teaching effectiveness, factual accuracy, or slideshow behavior.
Python standard library only. Pass a JSON config and --output report.json.
"""
import argparse
import hashlib
import json
import posixpath
import re
import struct
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def resolve(part, target):
    return posixpath.normpath(posixpath.join(posixpath.dirname(part), target)) if not target.startswith('/') else target.lstrip('/')


def relationships(z, part):
    name = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    if name not in z.namelist():
        return {}
    return {e.get('Id'): (e.get('Target'), e.get('Type'), e.get('TargetMode')) for e in ET.fromstring(z.read(name))}


def paragraph_text(node):
    paragraphs = []
    for p in node.findall('.//a:p', NS):
        text = []
        for el in p.iter():
            if el.tag == '{' + NS['a'] + '}t':
                text.append(el.text or '')
            elif el.tag == '{' + NS['a'] + '}br':
                text.append('\n')
        paragraphs.append(''.join(text))
    return '\n'.join(paragraphs)


def normalize(text):
    # Ignore platform line endings and outer page delimiters, never inner whitespace.
    return text.replace('\r\n', '\n').replace('\r', '\n').strip()


def characters_only(text):
    # Diagnostic only: a match here does not pass the strict paragraph check.
    return re.sub(r'\s', '', text)


def inspect_pptx(path):
    rows = []
    with ZipFile(path) as z:
        pres = ET.fromstring(z.read('ppt/presentation.xml'))
        rel = relationships(z, 'ppt/presentation.xml')
        for number, sid in enumerate(pres.findall('./p:sldIdLst/p:sldId', NS), 1):
            target, _, mode = rel[sid.get('{' + NS['r'] + '}id')]
            if mode == 'External':
                raise ValueError('External slide relationship')
            part = resolve('ppt/presentation.xml', target)
            slide = ET.fromstring(z.read(part))
            note_targets = [t for t, typ, mode in relationships(z, part).values() if typ.endswith('/notesSlide') and mode != 'External']
            notes = []
            for target in note_targets:
                note = ET.fromstring(z.read(resolve(part, target)))
                for shape in note.findall('.//p:sp', NS):
                    ph = shape.find('./p:nvSpPr/p:nvPr/p:ph', NS)
                    if ph is not None and ph.get('type') == 'body':
                        notes.append(paragraph_text(shape))
            rows.append({
                'page': number, 'slide_part': part,
                'visible_text': paragraph_text(slide),
                'notes': '\n'.join(notes), 'notes_relationship_count': len(note_targets),
                'native_text_shapes': sum(bool(s.findall('.//a:t', NS)) for s in slide.findall('.//p:sp', NS)),
                'pictures': len(slide.findall('.//p:pic', NS)),
                'has_timing_element': slide.find('.//p:timing', NS) is not None,
            })
        size = pres.find('./p:sldSz', NS)
        return {'path': str(path), 'sha256': digest(path.read_bytes()), 'slides': len(rows),
                'size_emu': dict(size.attrib) if size is not None else None,
                'pages_with_nonempty_notes': sum(bool(normalize(r['notes'])) for r in rows), 'pages': rows}


def script_pages(text):
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    matches = list(re.finditer(r'(?m)^第(\d+)页[｜|]', text))
    out = []
    for i, match in enumerate(matches):
        block = text[match.start():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        tail = block[len(block.rstrip('\n')):]
        out.append({'page': int(match.group(1)), 'text': normalize(block),
                    'trailing_blank_lines': max(0, len(tail) - 1)})
    return out


def file_map(folder):
    return {f.relative_to(folder).as_posix(): digest(f.read_bytes()) for f in sorted(folder.rglob('*')) if f.is_file()}


def compare_maps(expected, actual):
    return {'missing': sorted(expected.keys() - actual.keys()),
            'extra': sorted(actual.keys() - expected.keys()),
            'different': sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k]),
            'identical': expected == actual}


def timing(rows, rates):
    pages = []
    for row in rows:
        speech = row['notes'].split('\n', 1)[1]
        speech = re.sub(r'【.*?】', '', speech, flags=re.S)
        count = len(re.findall(r'[\u4e00-\u9fff]', speech))
        pages.append({'page': row['page'], 'spoken_hanzi': count, 'wait_seconds': row['wait_seconds'], 'budget_seconds': row['seconds']})
    count = sum(p['spoken_hanzi'] for p in pages)
    wait = sum(p['wait_seconds'] for p in pages)
    budget = sum(p['budget_seconds'] for p in pages)
    return {'actual_rehearsal': False, 'method': '汉字计数；排除页头及【提示】；沿用底稿等待预算；每页加3秒；语速仅为情景参数。未校准现场反馈、读数字及停顿。',
            'spoken_hanzi': count, 'interaction_seconds': wait, 'transition_seconds': 3 * len(pages),
            'budget_seconds': budget, 'scenarios': [
                {'hanzi_per_minute': rate, 'total_seconds': round(count / rate * 60 + wait + 3 * len(pages), 1),
                 'margin_seconds': round(budget - count / rate * 60 - wait - 3 * len(pages), 1),
                 'over_budget_pages': [p['page'] for p in pages if p['spoken_hanzi'] / rate * 60 + p['wait_seconds'] + 3 > p['budget_seconds'] + .01]}
                for rate in rates], 'pages': pages}


def audit(config_path):
    cfg = json.loads(config_path.read_text(encoding='utf-8-sig'))
    root = (config_path.parent / cfg['workspace_root']).resolve()
    path = lambda s: root / s
    baseline = cfg['baseline']
    report = {'schema_version': 1, 'audit_date': cfg['audit_date'], 'scope': 'read-only file consistency and workflow research',
              'sales_version_confirmation': cfg['sales_version_confirmation']}
    inventory = [inspect_pptx(path(item['pptx'])) | {'role': item['role']} for item in cfg['versions']]
    report['versions'] = [{k: v for k, v in item.items() if k != 'pages'} for item in inventory]
    actual = inspect_pptx(path(baseline['pptx']))
    rows = json.loads(path(baseline['content']).read_text(encoding='utf-8-sig'))
    transcript = script_pages(path(baseline['transcript']).read_text(encoding='utf-8-sig'))
    manifest = json.loads(path(baseline['manifest']).read_text(encoding='utf-8-sig'))
    report['baseline'] = {k: v for k, v in actual.items() if k != 'pages'}
    report['manifest_sha_matches'] = manifest['sha256'] == actual['sha256']
    report['page_counts'] = {'pptx': actual['slides'], 'content': len(rows), 'txt': len(transcript),
                             'content_sequence_correct': [r['page'] for r in rows] == list(range(1, actual['slides'] + 1)),
                             'txt_sequence_correct': [r['page'] for r in transcript] == list(range(1, actual['slides'] + 1))}
    report['page_checks'] = []
    for page in actual['pages']:
        n = page['page']
        source = next((r['notes'] for r in rows if r['page'] == n), None)
        txt = next((r for r in transcript if r['page'] == n), None)
        report['page_checks'].append({
            'page': n, 'notes_relationship_count': page['notes_relationship_count'],
            'native_text_shapes': page['native_text_shapes'], 'pictures': page['pictures'],
            'has_timing_element': page['has_timing_element'],
            'notes_match_content_strict': source is not None and normalize(page['notes']) == normalize(source),
            'notes_match_txt_strict': txt is not None and normalize(page['notes']) == txt['text'],
            'notes_match_txt_ignoring_whitespace_DIAGNOSTIC': txt is not None and characters_only(page['notes']) == characters_only(txt['text']),
            'txt_trailing_blank_lines': txt['trailing_blank_lines'] if txt else None,
        })
    report['boundary_text_observed'] = {'slide_2': actual['pages'][1]['visible_text'], 'last_slide': actual['pages'][-1]['visible_text']}
    images = sorted(path(baseline['images']).glob('*.png'))
    image_rows = []
    for image in images:
        data = image.read_bytes()
        size = struct.unpack('>II', data[16:24]) if data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR' else None
        image_rows.append({'name': image.name, 'size': size, 'sha256': digest(data)})
    report['images'] = {'count': len(images), 'names_complete': [f.name for f in images] == [f'{i:02}.png' for i in range(1, actual['slides'] + 1)],
                        'files': image_rows, 'provenance': '既有记录称来自最终PowerPoint渲染；本次核对文件及既有PPT哈希，未重渲染，也未证明每张PNG由该哈希生成。'}
    expected = file_map(path(baseline['delivery_folder']))
    report['delivery_files_sha256'] = expected
    with ZipFile(path(baseline['zip'])) as z:
        entries = [info for info in z.infolist() if not info.is_dir()]
        names = [info.filename.replace('\\', '/') for info in entries]
        zipped = {info.filename.replace('\\', '/'): digest(z.read(info)) for info in entries}
        report['zip'] = compare_maps(expected, zipped) | {'crc_bad_member': z.testzip(),
                                                        'duplicate_names': sorted({n for n in names if names.count(n) > 1}),
                                                        'sha256': digest(path(baseline['zip']).read_bytes())}
    report['extracted_copy'] = compare_maps(expected, file_map(path(baseline['extracted_copy'])))
    report['promo_direct_exports'] = [{'image': item['image'], 'ppt_page': item['page'],
                                       'byte_identical': digest(path(item['image']).read_bytes()) == digest(path(baseline['images']).joinpath(f"{item['page']:02}.png").read_bytes())}
                                      for item in cfg['promo_direct_exports']]
    report['timing'] = timing(rows, cfg['timing_rates'])
    checks = [report['manifest_sha_matches'],
              actual['slides'] == len(rows) == len(transcript),
              report['page_counts']['content_sequence_correct'], report['page_counts']['txt_sequence_correct'],
              all(r['notes_relationship_count'] == 1 and r['notes_match_content_strict'] and r['notes_match_txt_strict'] for r in report['page_checks']),
              report['images']['names_complete'], report['zip']['identical'],
              report['zip']['crc_bad_member'] is None, not report['zip']['duplicate_names'],
              report['extracted_copy']['identical'], all(r['byte_identical'] for r in report['promo_direct_exports'])]
    report['file_consistency_status'] = '通过' if all(checks) else '需修改'
    report['status_scope'] = '仅上述文件一致性检查，不代表事实、视觉、课堂和正式发布验收通过。'
    report['not_tested'] = ['本次未重新逐页渲染或进行PowerPoint放映测试', '未重做六类知识的外部事实核验', '未进行真实试讲、投影后排测试或买家访谈', '原始插画商用许可未独立核验']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.config.resolve())
    # Refuse to overwrite anything named as input in the config.
    cfg = json.loads(args.config.read_text(encoding='utf-8-sig'))
    root = (args.config.parent / cfg['workspace_root']).resolve()
    output = args.output.resolve()
    protected_folders = [root / cfg['baseline'][key] for key in ['delivery_folder', 'extracted_copy', 'images']]
    if output == args.config.resolve() or any(output.is_relative_to(folder.resolve()) for folder in protected_folders):
        raise ValueError('Report must not overwrite the config or enter the product delivery folder')
    def values(obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from values(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from values(v)
        elif isinstance(obj, str):
            yield obj
    for value in values(cfg):
        if '/' in value or '\\' in value:
            if output == (root / value).resolve():
                raise ValueError('Report would overwrite a configured input')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'report': str(output), 'slides': report['baseline']['slides'],
                      'file_consistency_status': report['file_consistency_status'],
                      'strict_notes_txt_matches': sum(r['notes_match_txt_strict'] for r in report['page_checks']),
                      'zip_identical': report['zip']['identical'], 'extracted_copy_identical': report['extracted_copy']['identical'],
                      'timing': report['timing']['scenarios']}, ensure_ascii=False))
    if report['file_consistency_status'] != '通过':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
