import test from 'node:test'
import assert from 'node:assert/strict'
import {saveCollectionPreference,restoreCollectionPreference,applyCollectionTitle} from './collectionPreferences.mjs'
test('remember per platform and account, validate choices and retain explicit empty',()=>{
 const entries=new Map();const storage={getItem:k=>entries.get(k)??null,setItem:(k,v)=>entries.set(k,v)}
 const account={type:6,filePath:'a.json'};const items=[{value:'123',name:'剧A'}]
 saveCollectionPreference(storage,account,'123')
 assert.equal(restoreCollectionPreference(storage,account,items),'123')
 assert.equal(restoreCollectionPreference(storage,{...account,filePath:'b.json'},items),undefined)
 assert.equal(restoreCollectionPreference(storage,account,[]),undefined)
 assert.equal(restoreCollectionPreference(storage,account,[{...items[0],disabled:true}]),undefined)
 saveCollectionPreference(storage,account,'');assert.equal(restoreCollectionPreference(storage,account,items),'')
})
test('title uses collection name and preserves manual editing',()=>{
 const tab={title:''};applyCollectionTitle(tab,'米格尔街');assert.equal(tab.title,'米格尔街')
 applyCollectionTitle(tab,'另一部剧');assert.equal(tab.title,'另一部剧')
 tab.title='自定义标题';applyCollectionTitle(tab,'合集三');assert.equal(tab.title,'自定义标题')
})

test('episode and chapter titles follow materials and preserve manual title',()=>{
 const tab={title:'',fileList:[{name:'第五集.mp4',episode_number:5,episode_unit:'集'}]}
 applyCollectionTitle(tab,'合集');assert.equal(tab.title,'合集 · 第5集')
 tab.fileList=[{name:'第三章.mp4',episode_number:3,episode_unit:'章'}]
 applyCollectionTitle(tab,'合集');assert.equal(tab.title,'合集 · 第三章')
 tab.fileList=[{name:'第十一章.mp4',episode_number:11,episode_unit:'章'}]
 applyCollectionTitle(tab,'合集');assert.equal(tab.title,'合集 · 第十一章')
 tab.title='手动标题';applyCollectionTitle(tab,'另一个合集');assert.equal(tab.title,'手动标题')
})
