import test from 'node:test'
import assert from 'node:assert/strict'
import {summarizeTasks,visibleTaskStatuses} from './taskStatus.mjs'
test('aggregates real stage progress and separates queue from execution',()=>{
 const result=summarizeTasks([{status:'running',progress:45},{status:'running',progress:35},{status:'queued',progress:0}])
 assert.equal(result.progress,27);assert.equal(result.running,2);assert.equal(result.queued,1);assert.equal(result.completed,0)
})
test('completed processing is not mislabeled successful publishing; actions sort first',()=>{
 const tasks=[{status:'completed'},{status:'queued'},{status:'failed',progress:30},{status:'awaiting_confirmation'}]
 const summary=summarizeTasks(tasks);assert.equal(summary.progress,50);assert.equal(summary.failed,1);assert.equal(summary.completed,1)
 assert.deepEqual(visibleTaskStatuses(tasks).map(task=>task.status),['awaiting_confirmation','failed','queued','completed'])
 assert.equal(visibleTaskStatuses(tasks,'attention').length,2)
})


test('task material uses submission snapshot, including series, chapter and multiple files',async()=>{
 const {describeTaskMaterial}=await import('./taskStatus.mjs')
 const payload={fileList:['D:/第一章.mp4'],title:'标题'}
 const label=describeTaskMaterial(payload,[{path:'D:/第一章.mp4',episode_number:1,episode_unit:'章'}],'外婆的道歉信')
 assert.equal(label,'外婆的道歉信 · 第1章')
 assert.equal(describeTaskMaterial({fileList:['uuid.mp4']},[{path:'uuid.mp4',name:'第十七集.mp4'}]),'第十七集')
 assert.equal(describeTaskMaterial({fileList:['D:\\视频\\第二集.mp4','D:/第三集.mp4']}),'第二集、第三集')
 assert.equal(describeTaskMaterial({fileList:[],title:'文章标题'}),'文章标题')
 assert.equal(describeTaskMaterial({}),'素材信息未记录')
})

test('failed compact task shows its error instead of the last successful stage',async()=>{
 const {taskStatusMessage,retrySubmissionPayload}=await import('./taskStatus.mjs')
 assert.equal(taskStatusMessage({status:'failed',stage:'视频和封面均已就绪',message:'快手合集页面加载超时'}),'快手合集页面加载超时')
 assert.equal(taskStatusMessage({status:'running',stage:'视频上传中',message:'已提交'}),'视频上传中')
 const original={requestId:'same',confirmRepeat:true,fileList:['first.mp4']}
 assert.deepEqual(retrySubmissionPayload({submissionPayload:original},'new'),original)
 const retried=retrySubmissionPayload({jobId:'failed-job',submissionPayload:original},'new')
 assert.equal(retried.requestId,'new');assert.equal(retried.confirmRepeat,undefined);assert.equal(original.confirmRepeat,true)
})

test('phase chips retain independent progress and do not invent unknown upload percentages',async()=>{
 const {taskPhaseEntries}=await import('./taskStatus.mjs')
 const rows=taskPhaseEntries({phases:{upload:{status:'running',progress:67,message:'上传中'},cover:{status:'running',message:'确认封面'}}})
 assert.match(rows.find(row=>row.key==='upload').label,/67%/)
 assert.match(rows.find(row=>row.key==='cover').label,/处理中/)
 assert.doesNotMatch(taskPhaseEntries({phases:{upload:{status:'running',progress:null}}})[0].label,/%/)
 assert.equal(taskPhaseEntries({phases:{collection:{status:'completed'}},collectionTask:{status:'failed',message:'加入合集失败'}})[0].type,'danger')
})
