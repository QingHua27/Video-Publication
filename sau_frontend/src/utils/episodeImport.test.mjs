import test from 'node:test'
import assert from 'node:assert/strict'
import { buildEpisodeImport, selectDefaultVideo } from './episodeImport.mjs'
const files=[{id:1,filename:'第一集.mp4',material_role:'video'},{id:2,filename:'第一集封面横板.png',material_role:'landscape_cover'},{id:3,filename:'第一集封面竖版.png',material_role:'portrait_cover'}]
test('Bilibili recommendation and space covers import independently',()=>{
 const result=buildEpisodeImport([...files,{id:4,filename:'第一集4x3.png',material_role:'recommendation_cover'}])
 assert.equal(result.landscape.id,2);assert.equal(result.recommendation.id,4)
 assert.equal(buildEpisodeImport(files).recommendation,null)
})
test('one episode imports its video and both covers',()=>{
 const result=buildEpisodeImport(files)
 assert.equal(result.video.id,1);assert.equal(result.landscape.id,2);assert.equal(result.portrait.id,3)
})
test('preview is excluded by default but can be selected manually',()=>{
 const versions=[...files,{id:4,filename:'第一集_预览.mp4',material_role:'video'}]
 assert.equal(buildEpisodeImport(versions).video.id,1)
 assert.equal(buildEpisodeImport(versions,4).video.id,4)
})
test('duplicate direction covers require selection; missing direction remains empty',()=>{
 assert.throws(()=>buildEpisodeImport([...files,{...files[1],id:5}]),/横版/)
 assert.equal(buildEpisodeImport([files[0],files[2]]).landscape,null)
 assert.equal(buildEpisodeImport(files,1,{landscape:'-'}).landscape,null)
})
test('foreign video choice cannot leak across folders',()=>{
 assert.throws(()=>buildEpisodeImport(files,99),/当前文件夹/)
})

test('highest resolution feature wins even when auxiliary videos are larger',()=>{
 const videos=[
  {id:1,filename:'外婆的道歉信_第一章烟草_1080x1920.mp4',video_width:1080,video_height:1920,filesize:174},
  {id:2,filename:'第一章_正片_720x1280.mp4',video_width:720,video_height:1280,filesize:200},
  {id:3,filename:'第一章_片头_4K.mp4',video_width:3840,video_height:2160,filesize:999},
  {id:4,filename:'第一章_试听.mp4',video_width:3840,video_height:2160},
  {id:5,filename:'第一章_手机版预览.mp4',video_width:3840,video_height:2160}
 ]
 assert.equal(selectDefaultVideo(videos).id,1)
 assert.equal(buildEpisodeImport(videos).video.id,1)
 assert.equal(selectDefaultVideo([...videos].reverse()).id,1)
})
test('filename dimensions are fallback and an all-preview folder has no default',()=>{
 assert.equal(selectDefaultVideo([{id:1,filename:'第2章_720x1280.mp4'},{id:2,filename:'第2章_1080x1920.mp4'}]).id,2)
 assert.equal(selectDefaultVideo([{id:1,filename:'第一章_片头.mp4'}]),null)
 assert.equal(selectDefaultVideo([{id:1,filename:'第一章.mp4',available:false}]),null)
})

test('identical pixel fingerprints auto-select; different or unknown images require choice',()=>{
 const same=[files[0],{...files[1],image_content_hash:'pixels-a'},{...files[1],id:5,filename:'copy.png',image_content_hash:'pixels-a'}]
 assert.equal(buildEpisodeImport(same).landscape.id,2)
 assert.equal(buildEpisodeImport(same,1,{landscape:5}).landscape.id,5)
 assert.throws(()=>buildEpisodeImport([...same,{...files[1],id:6,image_content_hash:'pixels-b'}]),/横版/)
 assert.throws(()=>buildEpisodeImport([...same,{...files[1],id:6}]),/横版/)
})
