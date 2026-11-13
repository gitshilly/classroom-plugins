"""Configured file audit with explicit missing evidence; no UI, no product writes."""
import argparse
import json
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
from check_delivery import inspect_pptx, script_pages, normalize, file_map, compare_maps, digest, timing


def summary_status(checks):
    if any(c['status'] == '需修改' for c in checks):
        return '需修改', 2
    if any(c['status'] == '未检查' for c in checks):
        return '已检查项目通过；有证据缺项', 3
    return '文件检查通过', 0


def audit(config_path):
    cfg = json.loads(config_path.read_text(encoding='utf-8-sig'))
    root = (config_path.parent / cfg['workspace_root']).resolve()
    b = cfg['baseline']
    path = lambda name: (root / name).resolve()
    checks = []
    def check(key, passed=None, evidence=None):
        checks.append({'id':key, 'status':'未检查' if passed is None else ('通过' if passed else '需修改'), 'evidence':evidence})
    actual = inspect_pptx(path(b['pptx']))
    count = actual['slides']
    with ZipFile(path(b['pptx'])) as z:
        check('pptx_crc', z.testzip() is None)
    if b.get('expected_sha256'):
        check('selected_file_identity', b['expected_sha256'] == actual['sha256'], actual['sha256'])
    if b.get('manifest'):
        manifest = json.loads(path(b['manifest']).read_text(encoding='utf-8-sig'))
        check('historical_manifest', manifest['sha256'] == actual['sha256'])
    else:
        check('historical_manifest', evidence='未提供独立历史版本清单；本次计算哈希不冒充历史版本证据')
    transcript = script_pages(path(b['transcript']).read_text(encoding='utf-8-sig'))
    check('txt_page_sequence', [r['page'] for r in transcript] == list(range(1,count+1)))
    rows = json.loads(path(b['content']).read_text(encoding='utf-8-sig')) if b.get('content') else None
    if rows is not None:
        check('content_page_sequence', [r['page'] for r in rows] == list(range(1,count+1)))
    else:
        check('independent_content', evidence='未提供独立逐页底稿，不以PPT备注反向生成后自比通过')
    page_checks = []
    for page in actual['pages']:
        n=page['page']
        txt=next((t for t in transcript if t['page']==n),None)
        source=next((r for r in rows if r['page']==n),None) if rows is not None else None
        page_checks.append({'page':n,'notes_match_txt_strict':txt is not None and normalize(page['notes'])==txt['text'],
            'notes_relationship_count':page['notes_relationship_count'],
            'notes_match_content_strict':normalize(page['notes'])==normalize(source['notes']) if source else None,
            'txt_trailing_blank_lines':txt['trailing_blank_lines'] if txt else None,
            'native_text_shapes':page['native_text_shapes'],'has_timing_element':page['has_timing_element']})
    check('notes_txt', all(r['notes_match_txt_strict'] and r['notes_relationship_count']==1 for r in page_checks),
          {'matching_pages':[r['page'] for r in page_checks if r['notes_match_txt_strict']], 'different_pages':[r['page'] for r in page_checks if not r['notes_match_txt_strict']]})
    if rows is not None:
        check('notes_content', all(r['notes_match_content_strict'] for r in page_checks))
    if cfg.get('require_two_blank_lines', False):
        check('two_blank_lines', all(r['txt_trailing_blank_lines']==2 for r in page_checks))
    image_rows=[]
    if b.get('images'):
        images=sorted(path(b['images']).glob('*.png'))
        check('image_page_sequence', [p.name for p in images]==[f'{i:02}.png' for i in range(1,count+1)])
        for p in images:
            try:
                with Image.open(p) as img:
                    img.load()
                    size=list(img.size)
                error=None
            except Exception as exc:
                size=None;error=type(exc).__name__+': '+str(exc)
            image_rows.append({'name':p.name,'sha256':digest(p.read_bytes()),'size':size,'decode_error':error})
        check('image_decode', bool(image_rows) and all(r['decode_error'] is None for r in image_rows))
        if cfg.get('expected_image_size'):
            check('image_dimensions', bool(image_rows) and all(r['size']==cfg['expected_image_size'] for r in image_rows))
    else:
        check('rendered_images', evidence='未提供逐页图片')
    expected=file_map(path(b['delivery_folder']))
    zip_report=None
    if b.get('zip'):
        with ZipFile(path(b['zip'])) as z:
            entries=[i for i in z.infolist() if not i.is_dir()]
            names=[i.filename.replace('\\','/') for i in entries]
            prefix=b.get('zip_prefix','')
            if prefix and not prefix.endswith('/'):
                raise ValueError('zip_prefix must end with /')
            if prefix and not all(n.startswith(prefix) for n in names):
                raise ValueError('ZIP contains files outside explicit zip_prefix')
            mapping={(n[len(prefix):] if prefix else n):digest(z.read(i)) for n,i in zip(names,entries)}
            zip_report=compare_maps(expected,mapping) | {'crc_bad_member':z.testzip(), 'duplicate_names':sorted({n for n in names if names.count(n)>1}), 'sha256':digest(path(b['zip']).read_bytes())}
        check('delivery_zip', zip_report['identical'] and zip_report['crc_bad_member'] is None and not zip_report['duplicate_names'], zip_report)
    else:
        check('delivery_zip', evidence='未提供与所选交付目录对应的完整教学包')
    extracted=None
    if b.get('extracted_copy'):
        extracted=compare_maps(expected,file_map(path(b['extracted_copy'])))
        check('extracted_copy', extracted['identical'], extracted)
    else:
        check('extracted_copy', evidence='未提供独立解压对照目录')
    promo=[]
    for item in cfg.get('promo_direct_exports',[]):
        equal=digest(path(item['image']).read_bytes())==digest((path(b['images'])/f"{item['page']:02}.png").read_bytes())
        promo.append({'image':item['image'],'page':item['page'],'byte_identical':equal})
    if promo:
        check('promo_direct_exports', all(r['byte_identical'] for r in promo), promo)
    else:
        check('promo_direct_exports', evidence='本轮未指定宣传图对照；不推断宣传图已通过')
    timed=None
    if rows is not None and all(all(k in r for k in ('page','notes','seconds','wait_seconds')) for r in rows):
        timed=timing(rows,cfg.get('timing_rates',[180,160,150]))
    status,code=summary_status(checks)
    return {'schema_version':'0.2','audit_date':cfg['audit_date'],'case_role':cfg.get('case_role'),
      'sales_version_confirmation':cfg.get('sales_version_confirmation'),
      'baseline':{k:v for k,v in actual.items() if k!='pages'},'checks':checks,'page_checks':page_checks,
      'images':image_rows,'images_provenance':cfg.get('image_evidence_note','只核对现有图像文件；本次未重新渲染绑定PPT哈希'),
      'delivery_files_sha256':expected,'zip':zip_report,'extracted_copy':extracted,
      'timing':timed,'timing_status':'静态估算，未试讲' if timed else '未核算：缺独立时间预算，不猜定等待时间',
      'boundary_text_observed':{'slide_2':actual['pages'][1]['visible_text'] if count>1 else None,'last_slide':actual['pages'][-1]['visible_text'] if count else None},
      'file_consistency_status':status,'exit_code':code,
      'not_tested':['事实准确性','图像使用依据','本轮渲染出处与版本绑定','逐页视觉检查','放映及鼠标试改','真实试讲与课堂','商品发布验收'],
      'status_scope':'文件对照与工具迁移；有缺项不算全验收通过；不同版本对照出现差异不自动判定旧商品损坏。'}


def guard_output(config_path,output):
    cfg=json.loads(config_path.read_text(encoding='utf-8-sig'))
    root=(config_path.parent/cfg['workspace_root']).resolve()
    if output==config_path:raise ValueError('Refuse to overwrite config')
    for key in ('pptx','transcript','content','manifest','zip'):
        value=cfg['baseline'].get(key)
        if value and output==(root/value).resolve():raise ValueError('Report would overwrite input')
    for key in ('delivery_folder','extracted_copy','images'):
        value=cfg['baseline'].get(key)
        if value and output.is_relative_to((root/value).resolve()):raise ValueError('Report must stay outside product folders')
    def strings(obj):
        if isinstance(obj,dict):
            for value in obj.values():yield from strings(value)
        elif isinstance(obj,list):
            for value in obj:yield from strings(value)
        elif isinstance(obj,str):yield obj
    for value in strings(cfg):
        if ('/' in value or '\\' in value) and output==(root/value).resolve():raise ValueError('Report would overwrite input')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();config=args.config.resolve();output=args.output.resolve()
    guard_output(config,output)
    report=audit(config)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(output),'pages':report['baseline']['slides'],'status':report['file_consistency_status'],
      'needs_revision':[r['id'] for r in report['checks'] if r['status']=='需修改'],
      'missing_evidence':[r['id'] for r in report['checks'] if r['status']=='未检查']},ensure_ascii=False))
    raise SystemExit(report['exit_code'])

if __name__=='__main__':main()
