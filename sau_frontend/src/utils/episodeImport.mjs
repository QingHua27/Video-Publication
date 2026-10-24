export const isVideoMaterial = material => material.available !== false && /\.(mp4|mov|avi|mkv|webm|m4v|flv|wmv)$/i.test(material.filename || '')

const auxiliaryVideo = /片头|片尾|试听|预览|手机版|预告|花絮|(?:^|[^a-z])(?:intro|outro|preview|trailer|teaser)(?:[^a-z]|$)/i
const videoPixels = file => {
 const width=Number(file.video_width || file.videoWidth),height=Number(file.video_height || file.videoHeight)
 if(width>0 && height>0)return width*height
 const match=String(file.filename || '').match(/(?:^|[^0-9])(\d{3,5})\s*[x×*]\s*(\d{3,5})(?![0-9])/i)
 if(match)return Number(match[1])*Number(match[2])
 const quality=String(file.filename || '').match(/(?:^|[^0-9])(2160|1440|1080|720|480)p(?:[^a-z0-9]|$)/i)
 if(quality)return Number(quality[1])**2*16/9
 return /(?:^|[^a-z0-9])4k(?:[^a-z0-9]|$)/i.test(file.filename || '') ? 3840*2160 : 0
}
export function selectDefaultVideo(files) {
 const candidates=files.filter(isVideoMaterial).filter(file=>!auxiliaryVideo.test(file.filename || ''))
 if(candidates.length===1)return candidates[0]
 if(!candidates.length || !candidates.some(file=>videoPixels(file)>0))return null
 return [...candidates].sort((a,b)=>videoPixels(b)-videoPixels(a) || Number(b.filesize || 0)-Number(a.filesize || 0) || String(a.filename).localeCompare(String(b.filename),'zh-CN') || Number(a.id)-Number(b.id))[0]
}

export function nextEpisodeFiles(materials, sourcePath, sectionId) {
  const current=materials.filter(file=>file.file_path===sourcePath && (sectionId==null || (file.section_id || 0)===sectionId))
  if (current.length!==1 || current[0].episode_number==null) throw new Error('无法确定当前剧集分区，请从素材库按集文件夹导入本集')
  const source=current[0]
  const number=Number(source.episode_number)+1
  const files=materials.filter(file=>(file.section_id || 0)===(source.section_id || 0) && Number(file.episode_number)===number && (file.episode_unit || '集')===(source.episode_unit || '集'))
  if (!files.some(isVideoMaterial)) throw new Error(`同一分区未找到第${number}${source.episode_unit || '集'}可用视频`)
  return {files,number,sectionId:source.section_id || 0,folder:files[0].folder_name}
}

export function distinctCoverChoices(files){
  const hashes=new Set()
  return files.filter(file=>{
    const hash=file.image_content_hash
    if(!hash)return true
    if(hashes.has(hash))return false
    hashes.add(hash);return true
  })
}

export function buildEpisodeImport(files, videoId, coverIds = {}) {
  const videos=files.filter(isVideoMaterial)
  if (!videos.length) throw new Error('当前文件夹没有视频')
  const video=videoId == null ? selectDefaultVideo(videos) : videos.find(file=>file.id===videoId)
  if(videoId==null && !video)throw new Error('无法确定本集正片视频版本，请手动选择；片头、试听和预览不会自动选中')
  if (!video) throw new Error('请选择当前文件夹的视频')
  const result={video}
  for (const kind of ['landscape','portrait','recommendation']) {
    const allChoices=files.filter(file=>file.available !== false && file.material_role===`${kind}_cover`)
    const choices=distinctCoverChoices(allChoices)
    if (coverIds[kind] === '-') {result[kind]=null;continue}
    if (coverIds[kind] != null && coverIds[kind] !== '') {
      result[kind]=allChoices.find(file=>file.id===coverIds[kind])
      if (!result[kind]) throw new Error('所选封面不在当前文件夹，请重新选择')
    } else {
      if (choices.length>1) throw new Error(`本集有多个${kind==='recommendation'?'B站4:3':kind==='landscape'?'横版':'竖版'}封面，请选择一个`)
      result[kind]=choices[0] || null
    }
  }
  return result
}
