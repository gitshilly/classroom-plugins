"""Run one registered audit and produce a readable handoff. No product mutation or UI."""
import argparse
import json
from pathlib import Path
from check_delivery import digest
from check_delivery_v2 import audit, guard_output

LABELS = {
 'pptx_crc':'PPT文件完整性','selected_file_identity':'指定PPT版本','historical_manifest':'历史版本清单',
 'txt_page_sequence':'TXT页码顺序','content_page_sequence':'独立底稿页码','independent_content':'独立逐页底稿',
 'notes_txt':'PPT备注与TXT','notes_content':'PPT备注与独立底稿','two_blank_lines':'逐页两行空白',
 'image_page_sequence':'逐页图片数量和编号','image_decode':'图片完整解码','image_dimensions':'图片尺寸',
 'rendered_images':'逐页图片','delivery_zip':'目录与教学ZIP','extracted_copy':'独立解压对照',
 'promo_direct_exports':'指定商品直出内页'}
ACTION = {
 'notes_txt':'回到版本配对：找出与本PPT备注一致的TXT；如需改稿，先改共同底稿，再同步PPT备注和TXT。',
 'selected_file_identity':'当前PPT与锁定的文件不同，先确认改动和应核对的版本。',
 'delivery_zip':'确认是同一交付版本，再核对缺失/多余/变化成员；不要自动拿旧包替代。',
 'independent_content':'补充本版本独立逐页底稿；从PPT反抄的文字不能充当独立核验依据。',
 'historical_manifest':'查找本版本历史清单；本次计算的哈希只锁定当前文件。',
 'extracted_copy':'需要验包时使用明确对应版本的解压副本。',
 'promo_direct_exports':'涉及商品展示时，再指定真实PPT页码与实际导出图。'}


def assess(report,work):
    baseline=work.get('baseline',{})
    matched=baseline.get('pptx_sha256')==report['baseline']['sha256']
    confirmed=matched and baseline.get('confirmed_by_user') is True
    problems=[]
    for c in report['checks']:
        if c['status']!='通过':
            problems.append({'item':LABELS.get(c['id'],c['id']),'status':c['status'],
              'evidence':c['evidence'],'next_action':ACTION.get(c['id'],'查看完整核验报告，定位文件或页码后复查。')})
    if not matched:
        problems.append({'item':'工作单与PPT身份','status':'需修改','evidence':'工作单哈希不匹配，不能借用其确认或检查结论','next_action':'重新配对工作单和PPT版本。'})
    return {'file_status':report['file_consistency_status'],
      'selected_version_confirmed_by_user':confirmed,'work_order_hash_matches':matched,
      'full_release_status':'本次未做正式发布验收',
      'next_action':'先处理具体文件差异，再复跑。' if report['exit_code']==2 or not matched else
        ('可继续其他阶段研究；完善本版本证据和配套包后再做发布验收。' if report['exit_code']==3 else
         '文件一致性已通过；可据此检查内容、使用与展示等其余适用项目。'),
      'problems':problems,'not_tested':report['not_tested']}


def run(registry_path,case_id,run_date):
    base=registry_path.parent
    registry=json.loads(registry_path.read_text(encoding='utf-8-sig'))
    case=registry['cases'][case_id]
    cfg_path=(base/case['config']).resolve()
    work_path=(base/case['work_order']).resolve()
    config=json.loads(cfg_path.read_text(encoding='utf-8-sig'))
    work=json.loads(work_path.read_text(encoding='utf-8-sig'))
    output=(base/registry['output_folder']/case_id).resolve()
    # Runner outputs stay in the research tree and outside every configured input folder.
    if not output.is_relative_to(base.resolve()):raise ValueError('Output must stay inside the research folder')
    filenames=['完整核验.json','运行记录.json','检查结果.txt','待处理问题.txt','交付文件清单.txt']
    for name in filenames:
        dest=output/name;guard_output(cfg_path,dest)
        if dest in (registry_path,work_path):raise ValueError('Cannot overwrite registry/work order')
    report=audit(cfg_path)
    report['configuration_audit_date']=report['audit_date'];report['audit_date']=run_date
    result=assess(report,work)
    # Check that the selected PPT has not changed during the audit.
    if digest(Path(report['baseline']['path']).read_bytes())!=report['baseline']['sha256']:
        raise ValueError('PPT changed while auditing; rerun before trusting the result')
    output.mkdir(parents=True,exist_ok=True)
    (output/'完整核验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    pages=report['baseline']['slides'];matches=sum(r['notes_match_txt_strict'] for r in report['page_checks'])
    lines=[case['title']+'｜交付核验结果',run_date+'｜内部研究记录', '',
      '本次范围：'+case['scope_note'],
      '文件检查：'+result['file_status'],
      '产品完整验收：'+result['full_release_status'],
      '用户确认的交付版本：'+('是（工作单确认与PPT哈希匹配）' if result['selected_version_confirmed_by_user'] else '未确认，不据此决定买家交付版本'),
      f'实际页数：{pages}；备注与TXT匹配：{matches}/{pages}；逐页图片：{len(report["images"])}；被核对交付目录文件：{len(report["delivery_files_sha256"])}',
      'PPT：'+report['baseline']['path'],'PPT SHA256：'+report['baseline']['sha256'],'','检查明细：']
    lines += [f'- {LABELS.get(c["id"],c["id"])}：{c["status"]}' for c in report['checks']]
    lines += ['','本轮未检查/未实测：']+['- '+s for s in result['not_tested']]
    lines += ['','图片来源边界：'+report['images_provenance'],
      '其他历史记录不会自动计入本次通过项；未实测不等于文件损坏，也不能写成已经通过。',
      '下一步：'+result['next_action'],'',
      '完整报告、待处理问题和文件清单在本目录。未自动改文件、打包、替换商品或联系买家。']
    (output/'检查结果.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    issues=[case['title']+'｜待处理问题',run_date,'']
    if not result['problems']:issues.append('本次文件检查没有发现差异；这不代表全部产品项目已验收。')
    for n,p in enumerate(result['problems'],1):
        issues.extend([f'{n}. {p["item"]}｜{p["status"]}', '证据：'+json.dumps(p['evidence'],ensure_ascii=False), '处理：'+p['next_action'],''])
    issues.extend(['独立于文件检查的未核验项：']+['- '+s for s in result['not_tested']])
    issues.extend(['','范围说明：这些是本轮证据边界，不是一律暂停研究的条件；具体发布条件按适用项目规则另判。'])
    (output/'待处理问题.txt').write_text('\n'.join(issues)+'\n',encoding='utf-8')
    manifest=['被核对的现有交付目录文件清单',run_date,
      '用途：定位同一目录内的文件；不等于已批准的新交付包，也不表示缺失附件已补齐。',
      '源目录：'+config['baseline']['delivery_folder'],'']
    manifest += [f'{n:02}. {name}\n    SHA256 {sha}' for n,(name,sha) in enumerate(sorted(report['delivery_files_sha256'].items()),1)]
    (output/'交付文件清单.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
    receipt={'date':run_date,'case':case_id,'result':result,'input_config_sha256':digest(cfg_path.read_bytes()),
      'input_work_order_sha256':digest(work_path.read_bytes()),'pptx_sha256':report['baseline']['sha256'],
      'product_changed':False,'ui_used':False,'automatically_published':False,
      'outputs':{name:digest((output/name).read_bytes()) for name in filenames if name!='运行记录.json'}}
    (output/'运行记录.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return output,result,report['exit_code'] if result['work_order_hash_matches'] else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry',type=Path,required=True)
    parser.add_argument('--case',required=True);parser.add_argument('--date',required=True)
    args=parser.parse_args()
    output,result,code=run(args.registry.resolve(),args.case,args.date)
    print(json.dumps({'output':str(output),'file_status':result['file_status'],'next_action':result['next_action']},ensure_ascii=False))
    raise SystemExit(code)

if __name__=='__main__':main()
