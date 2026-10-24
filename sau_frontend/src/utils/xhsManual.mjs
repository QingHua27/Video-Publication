export const manualXhsEnabled=(tab,platform)=>Number(platform)===1 && tab.xhsManual===true
export function createManualXhsTask(accountId,label,payload,materialLabel){
 return {accountId,label,manualXhs:true,status:'awaiting_confirmation',stage:'待人工发布',progress:0,jobId:null,materialLabel,submissionPayload:JSON.parse(JSON.stringify(payload)),message:'请在小红书官方页面手动上传和发布，完成后点击「已手动发布」。'}
}
export function manualXhsText(payload={}){return [payload.title || '',(payload.tags || []).map(tag=>'#'+String(tag).replace(/^#+/,'')).join(' ')].filter(Boolean).join('\n\n')}
export function manualXhsMaterials(payload={}){return [...(payload.fileList || []).map((path,index)=>({label:`视频${index+1}`,path})),...(payload.thumbnail ? [{label:'竖版封面',path:payload.thumbnail}] : [])]}
