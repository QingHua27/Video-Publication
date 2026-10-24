import {materialPublications} from './materialPublication.mjs'
const key='omnipost.publish-draft.v1'
const fields=['name','label','title','description','topics','selectedPlatforms','selectedPlatform','selectedAccounts','collections','fileList','videoCovers','episodeSourceVideoPath','episodeSectionId','xhsManual']
export function savePublishDraft(storage,tabs){
 try{storage.setItem(key,JSON.stringify(tabs.slice(0,20).map(tab=>Object.fromEntries(fields.filter(field=>tab[field]!==undefined).map(field=>[field,tab[field]])))))}catch{}
}
export function loadPublishDraft(storage){
 try{const value=JSON.parse(storage.getItem(key) || '[]');return Array.isArray(value)?value.filter(tab=>tab && /^tab[0-9]+$/.test(tab.name) && Array.isArray(tab.fileList)).slice(0,20).map(tab=>Object.fromEntries(fields.filter(field=>tab[field]!==undefined).map(field=>[field,tab[field]]))):[]}catch{return []}
}
export function unfinishedMaterial(file,history){return !materialPublications(file,history).some(record=>record.status==='published')}
