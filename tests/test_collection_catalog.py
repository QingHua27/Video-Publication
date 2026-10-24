import unittest
from utils.collection_catalog import normalize_catalog, CollectionCatalogError

class CatalogTests(unittest.TestCase):
    def test_xhs_current_collection_info_list_schema(self):
        response={'data':{'collectionInfoList':[{'id':'xhs-series','name':'米格尔街','type':0,'noteNum':8}],'hasMore':False}}
        result=normalize_catalog(1,response,'/api/sns/v1/note/collection/pc/list_v2')
        self.assertEqual(result['items'],[{'id':'xhs-series','name':'米格尔街','value':'米格尔街'}])
        self.assertFalse(result['partial'])

    def test_paginated_catalog_warns_that_list_is_partial(self):
        result=normalize_catalog(6,{'code':0,'data':{'seasons':[{'id':123,'title':'系列甲'}],'total':30}},'/x2/creative/web/seasons')
        self.assertTrue(result['partial'])
        self.assertIn('部分',result['message'])
    def test_bilibili_uses_id_as_value_but_displays_name(self):
        result=normalize_catalog(6,{'code':0,'data':{'seasons':[{'id':123,'title':'系列甲'}],'total':1}},'/x2/creative/web/seasons')
        self.assertEqual(result['items'],[{'id':'123','name':'系列甲','value':'123'}])

    def test_wechat_uses_name_for_uploader_and_retains_platform_id(self):
        result=normalize_catalog(2,{'errCode':0,'data':{'collectionList':[{'id':'42','name':'我的合集'}]}},'/collection/get_collection_list')
        self.assertEqual(result['items'],[{'id':'42','name':'我的合集','value':'我的合集'}])

    def test_confirmed_empty_is_not_unknown_response(self):
        self.assertEqual(normalize_catalog(6,{'code':0,'data':{'seasons':None,'total':0}},'/x2/creative/web/seasons')['status'],'empty')
        self.assertIsNone(normalize_catalog(3,{'status_code':0,'data':{}},'/other/api'))

    def test_douyin_nested_mix_info_and_duplicate_ids(self):
        data={'status_code':0,'mix_infos':[{'mix_info':{'mix_id':'1','mix_name':'合集甲'}},{'mix_info':{'mix_id':'1','mix_name':'合集甲'}}]}
        result=normalize_catalog(3,data,'/mix/list')
        self.assertEqual(len(result['items']),1)

    def test_expired_login_and_platform_errors_are_not_empty_lists(self):
        with self.assertRaises(CollectionCatalogError):
            normalize_catalog(6,{'code':-101,'message':'not logged in'},'/x2/creative/web/seasons')
        with self.assertRaises(CollectionCatalogError):
            normalize_catalog(2,{'errCode':1001,'data':{}},'/collection/get_collection_list')

    def test_kuaishou_pending_collection_is_deferred(self):
        payload={'result':1,'data':{'list':[{'collectionId':1,'title':'外婆的道歉信','status':4,'size':0,'offlineReason':'有效剧集数不足，不公开展示'},{'collectionId':2,'title':'米格尔街','status':1,'size':17}],'total':2}}
        result=normalize_catalog(4,payload,'/rest/cp/works/v2/collection/list')
        self.assertTrue(result['items'][0]['deferred']);self.assertFalse(result['items'][0].get('disabled'));self.assertIn('有效剧集数不足',result['items'][0]['unavailableReason'])
        self.assertFalse(result['items'][1].get('disabled',False))

if __name__=='__main__':unittest.main()
