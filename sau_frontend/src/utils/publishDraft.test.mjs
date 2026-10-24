import test from 'node:test'
import assert from 'node:assert/strict'
import {savePublishDraft,loadPublishDraft,unfinishedMaterial} from './publishDraft.mjs'
test('restores last video, covers, configuration without starting a publishing task',()=>{
 let value;const storage={getItem:()=>value,setItem:(_,v)=>value=v}
 savePublishDraft(storage,[{name:'tab1',label:'第一集',fileList:[{name:'第一集.mp4',path:'D:/video.mp4'}],videoCovers:{landscape:{path:'cover.png'}},episodeSectionId:2,title:'标题',selectedAccounts:[1],publishing:true,automationActive:true}])
 const [draft]=loadPublishDraft(storage)
 assert.equal(draft.fileList[0].path,'D:/video.mp4');assert.equal(draft.videoCovers.landscape.path,'cover.png');assert.equal(draft.episodeSectionId,2)
 assert.equal(draft.title,'标题');assert.equal(draft.automationActive,undefined);assert.equal(draft.publishing,undefined)
})
test('unfinished excludes confirmed published material, keeps failures and unverified submissions',()=>{
 const file={file_path:'D:/video.mp4'}
 assert.equal(unfinishedMaterial(file,[{source_path:file.file_path,status:'published'}]),false)
 assert.equal(unfinishedMaterial(file,[{source_path:file.file_path,status:'submitted'}]),true)
 assert.equal(unfinishedMaterial(file,[{source_path:file.file_path,status:'failed'}]),true)
})
test('bad or unavailable storage does not interrupt editing',()=>{
 assert.deepEqual(loadPublishDraft({getItem:()=>'{bad'}),[])
 assert.doesNotThrow(()=>savePublishDraft({setItem:()=>{throw Error('quota')}},[]))
})
