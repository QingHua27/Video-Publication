export function automationOutcome(results){
 if(!results.length)return 'waiting'
 if(results.some(r=>['failed','awaiting_confirmation','cancelled'].includes(r.status) || r.windowVisible || r.collectionTask?.status==='failed'))return 'paused'
 if(results.some(r=>r.status!=='completed' || !r.jobId || (r.collectionTask && r.collectionTask.status!=='completed')))return 'waiting'
 if(results.some(r=>r.submissionPayload?.dryRun || r.submissionPayload?.isDraft))return 'paused'
 return 'next'
}
export function automationNextAvailable(files,path,sectionId){
 const current=files.filter(f=>f.file_path===path && (sectionId==null || (f.section_id || 0)===sectionId))
 if(current.length!==1 || current[0].episode_number==null)throw new Error('自动连续发布需要从素材库按集文件夹选择视频')
 const source=current[0]
 return files.some(f=>(f.section_id || 0)===(source.section_id || 0) && (f.episode_unit || '集')===(source.episode_unit || '集') && Number(f.episode_number)>Number(source.episode_number))
}
