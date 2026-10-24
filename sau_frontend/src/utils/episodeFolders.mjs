import {isVideoMaterial} from './episodeImport.mjs'
import {materialPublications} from './materialPublication.mjs'
export const coverKinds=['landscape','portrait','recommendation']
export function episodeFolders(materials,history){
 const groups=new Map()
 for(const file of materials){
  const name=file.folder_name || '未分类'
  if(!groups.has(name))groups.set(name,{name,number:file.episode_number ?? Infinity,files:[]})
  groups.get(name).files.push(file)
 }
 return [...groups.values()].sort((a,b)=>a.number-b.number || a.name.localeCompare(b.name,'zh-CN')).map(folder=>{
  const videos=folder.files.filter(isVideoMaterial)
  const covers=Object.fromEntries(coverKinds.map(kind=>[kind,folder.files.filter(file=>file.available!==false && file.material_role===`${kind}_cover`)]))
  const records=new Map()
  for(const file of videos)for(const record of materialPublications(file,history))records.set(record.id,record)
  return {...folder,count:folder.files.length,videos,covers,publications:[...records.values()],preview:(covers.landscape[0] || covers.recommendation[0] || covers.portrait[0])?.file_path,coverCount:Object.values(covers).reduce((sum,files)=>sum+files.length,0)}
 })
}
