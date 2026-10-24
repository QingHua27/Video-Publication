import test from 'node:test'
import assert from 'node:assert/strict'
import {loadTaskSnapshot,saveTaskSnapshot} from './taskSnapshot.mjs'
test('refresh restores task ids and retry payloads without a submission',()=>{
 let value=null;const storage={getItem:()=>value,setItem:(_,text)=>value=text}
 const tabs=[{name:'tab2',label:'发布2',destinationResults:[{jobId:'job1',status:'running',accountId:1,submissionPayload:{title:'原始标题'},windowChanging:true}]}]
 saveTaskSnapshot(storage,tabs,1000)
 const restored=loadTaskSnapshot(storage,1001)
 assert.equal(restored[0].results[0].jobId,'job1');assert.equal(restored[0].results[0].windowChanging,false)
 assert.equal(restored[0].results[0].submissionPayload.title,'原始标题');assert.equal(loadTaskSnapshot(storage,100000000).length,0)
})
test('bad or unavailable storage cannot break the publishing page',()=>{
 assert.deepEqual(loadTaskSnapshot({getItem:()=>'{broken'}),[])
 assert.doesNotThrow(()=>saveTaskSnapshot({setItem:()=>{throw Error('quota')}},[]))
})
