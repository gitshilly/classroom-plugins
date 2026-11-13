import unittest
from delivery_assistant import assess


class EntryTests(unittest.TestCase):
    def report(self,code=0):
        return {'baseline':{'sha256':'abc'},'checks':[], 'exit_code':code,
          'file_consistency_status':'文件检查通过' if code==0 else '有缺项','not_tested':['放映']}

    def test_file_pass_never_becomes_full_release_pass(self):
        r=assess(self.report(),{'baseline':{'pptx_sha256':'abc','confirmed_by_user':True}})
        self.assertTrue(r['selected_version_confirmed_by_user'])
        self.assertEqual(r['full_release_status'],'本次未做正式发布验收')
        self.assertEqual(r['not_tested'],['放映'])

    def test_other_version_cannot_borrow_user_confirmation(self):
        r=assess(self.report(),{'baseline':{'pptx_sha256':'other','confirmed_by_user':True}})
        self.assertFalse(r['selected_version_confirmed_by_user'])
        self.assertEqual(r['problems'][0]['status'],'需修改')

    def test_missing_evidence_survives_human_summary(self):
        report=self.report(3)
        report['checks']=[{'id':'delivery_zip','status':'未检查','evidence':'没有对应包'}]
        r=assess(report,{'baseline':{'pptx_sha256':'abc','confirmed_by_user':False}})
        self.assertEqual(r['problems'][0]['status'],'未检查')
        self.assertFalse(r['selected_version_confirmed_by_user'])

if __name__=='__main__':unittest.main()
