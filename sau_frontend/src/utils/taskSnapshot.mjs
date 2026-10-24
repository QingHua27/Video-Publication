const key='omnipost.publish-tasks.v1'
export function loadTaskSnapshot(storage,now=Date.now()){
 try{
  const saved=JSON.parse(storage.getItem(key) || 'null')
  if(!saved || !Array.isArray(saved.tabs) || now-saved.savedAt>86400000)return []
  return saved.tabs.slice(0,20).filter(tab=>/^tab[0-9]+$/.test(tab.name) && Array.isArray(tab.results)).map(tab=>({name:tab.name,label:String(tab.label || '发布任务').slice(0,40),results:tab.results.slice(0,100).filter(result=>result && (result.jobId || result.manualXhs===true || result.status==='awaiting_confirmation')).map(result=>({...result,windowChanging:false,manualSaving:false}))})).filter(tab=>tab.results.length)
 }catch{return []}
}
export function saveTaskSnapshot(storage,tabs,now=Date.now()){
 try{storage.setItem(key,JSON.stringify({savedAt:now,tabs:tabs.filter(tab=>tab.destinationResults.length).map(tab=>({name:tab.name,label:tab.label,results:tab.destinationResults}))}))}catch{/* Private browsing or storage quota must not interrupt publishing. */}
}
