const terminal=new Set(['completed','failed','cancelled'])
export const taskStateLabels={queued:'排队中',running:'执行中',completed:'流程完成',failed:'失败',awaiting_confirmation:'待确认',cancelled:'已取消'}
export const taskStateColors={queued:'#a5adba',running:'#3478e5',completed:'#299957',failed:'#d65353',awaiting_confirmation:'#d79424',cancelled:'#a5adba'}
export function taskProgress(task){
 if(terminal.has(task.status))return 100
 return Math.min(99,Math.max(0,Number(task.progress)||0))
}
export function summarizeTasks(tasks){
 const count=status=>tasks.filter(task=>task.status===status).length
 return {total:tasks.length,completed:count('completed'),failed:count('failed'),queued:count('queued'),running:count('running'),confirmation:count('awaiting_confirmation'),cancelled:count('cancelled'),
 progress:tasks.length ? Math.round(tasks.reduce((sum,task)=>sum+taskProgress(task),0)/tasks.length) : 0}
}
export function visibleTaskStatuses(tasks,filter='all'){
 const priority={awaiting_confirmation:0,failed:1,running:2,queued:3,completed:4,cancelled:5}
 return tasks.filter(task=>filter==='all' || (filter==='active' ? (['running','queued'].includes(task.status) || ['waiting','running'].includes(task.collectionTask?.status)) : (['failed','awaiting_confirmation'].includes(task.status) || task.collectionTask?.status==='failed')))
  .map((task,index)=>({task,index})).sort((a,b)=>(a.task.collectionTask?.status==='failed'?1:priority[a.task.status]??6)-(b.task.collectionTask?.status==='failed'?1:priority[b.task.status]??6) || a.index-b.index).map(item=>item.task)
}

export function describeTaskMaterial(payload={},files=[],sectionName=''){
 const labels=(payload.fileList || []).map(path=>{
  const file=files.find(file=>(file.path || file.file_path)===path)
  return file?.episode_number != null ? `第${file.episode_number}${file.episode_unit || '集'}` : String(file?.name || file?.filename || path).replaceAll('\\','/').split('/').pop().replace(/\.[^.]+$/,'')
 })
 const name=[...new Set(labels)].join('、') || payload.title || '素材信息未记录'
 return sectionName ? `${sectionName} · ${name}` : name
}

export function taskStatusMessage(task){
 if(task.collectionTask?.status==='failed')return task.collectionTask.message || '加入合集失败'
 if(['failed','awaiting_confirmation'].includes(task.status))return task.message || task.stage || taskStateLabels[task.status]
 return task.collectionTask?.message || task.stage || task.message || taskStateLabels[task.status]
}
export function retrySubmissionPayload(result,newRequestId){
 const payload=JSON.parse(JSON.stringify(result.submissionPayload))
 if(result.jobId || result.submissionRejected || !payload.requestId){payload.requestId=newRequestId;delete payload.confirmRepeat}
 return payload
}

const phaseNames={precheck:'预检',upload:'上传',cover:'封面',collection:'合集',submission:'提交'}
const phaseStates={running:'处理中',waiting:'等待',completed:'完成',failed:'失败',skipped:'未启用',cancelled:'已停止',interrupted:'中断'}
export function taskPhaseEntries(task){
 const phases={...(task.phases || {})}
 if(task.collectionTask)phases.collection={status:task.collectionTask.status,message:task.collectionTask.message}
 return Object.entries(phaseNames).filter(([key])=>phases[key]).map(([key,name])=>{
  const phase=phases[key]
  const percent=key==='upload' && phase.status==='running' && typeof phase.progress==='number' && Number.isFinite(phase.progress) ? ` ${phase.progress}%` : ''
  return {key,label:`${name} · ${phaseStates[phase.status] || phase.status}${percent}`,message:phase.error || phase.message,type:phase.status==='failed'?'danger':phase.status==='completed'?'success':['waiting','interrupted'].includes(phase.status)?'warning':'info'}
 })
}
