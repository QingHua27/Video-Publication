import test from 'node:test'
import assert from 'node:assert/strict'
import {manualXhsEnabled,createManualXhsTask,manualXhsText,manualXhsMaterials} from './xhsManual.mjs'
import {loadTaskSnapshot,saveTaskSnapshot} from './taskSnapshot.mjs'
import {loadPublishDraft,savePublishDraft} from './publishDraft.mjs'
test('manual publishing is opt-in and only applies to Xiaohongshu',()=>{
 assert.equal(manualXhsEnabled({},1),false);assert.equal(manualXhsEnabled({xhsManual:true},1),true);assert.equal(manualXhsEnabled({xhsManual:true},3),false)
})
test('manual task freezes the submitted material and never creates an automated job',()=>{
 const payload={fileList:['video.mp4'],thumbnail:'portrait.png',title:'第25章',tags:['小说']}
 const task=createManualXhsTask(1,'小红书 · 测试',payload,'外婆 · 第25章')
 payload.fileList[0]='next.mp4'
 assert.equal(task.status,'awaiting_confirmation');assert.equal(task.jobId,null);assert.equal(task.manualXhs,true)
 assert.equal(task.submissionPayload.fileList[0],'video.mp4');assert.equal(task.materialLabel,'外婆 · 第25章')
 assert.equal(manualXhsText(task.submissionPayload),'第25章\n\n#小说')
 assert.deepEqual(manualXhsMaterials(task.submissionPayload),[{label:'视频1',path:'video.mp4'},{label:'竖版封面',path:'portrait.png'}])
})
test('manual pending and user-confirmed completion survive refresh; option persists',()=>{
 let value;const storage={getItem:()=>value,setItem:(_,v)=>value=v}
 const task=createManualXhsTask(1,'账号',{fileList:['video.mp4']},'第1集')
 saveTaskSnapshot(storage,[{name:'tab1',destinationResults:[task]}]);assert.equal(loadTaskSnapshot(storage)[0].results[0].manualXhs,true)
 task.status='completed';saveTaskSnapshot(storage,[{name:'tab1',destinationResults:[task]}]);assert.equal(loadTaskSnapshot(storage)[0].results[0].status,'completed')
 savePublishDraft(storage,[{name:'tab1',fileList:[],xhsManual:true}]);assert.equal(loadPublishDraft(storage)[0].xhsManual,true)
})
