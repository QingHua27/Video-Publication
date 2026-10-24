import test from 'node:test'
import assert from 'node:assert/strict'
import {nextEpisodeFiles,buildEpisodeImport} from './episodeImport.mjs'
const materials=[
 {id:1,file_path:'one.mp4',filename:'第一集.mp4',section_id:4,episode_number:1},
 {id:2,file_path:'two.mp4',filename:'第二集.mp4',section_id:4,episode_number:2,folder_name:'第二集'},
 {id:3,file_path:'wide.png',filename:'第二集横版.png',section_id:4,episode_number:2,material_role:'landscape_cover'},
 {id:4,file_path:'tall.png',filename:'第二集竖版.png',section_id:4,episode_number:2,material_role:'portrait_cover'},
 {id:5,file_path:'other.mp4',filename:'第二集.mp4',section_id:5,episode_number:2}
]
test('next episode uses same section and brings both covers',()=>{
 const next=nextEpisodeFiles(materials,'one.mp4',4);const chosen=buildEpisodeImport(next.files)
 assert.equal(next.number,2);assert.equal(chosen.video.id,2);assert.equal(chosen.landscape.id,3);assert.equal(chosen.portrait.id,4)
})
test('missing episodes never skip to a different episode or section',()=>{
 assert.throws(()=>nextEpisodeFiles(materials,'two.mp4',4),/第3集/)
 assert.throws(()=>nextEpisodeFiles(materials,'unknown.mp4'),/无法确定/)
})
test('ambiguous section or multiple versions require a choice',()=>{
 assert.throws(()=>nextEpisodeFiles([...materials,{...materials[0],section_id:6}],'one.mp4'),/无法确定/)
 const next=nextEpisodeFiles([...materials,{...materials[1],id:6,file_path:'two-preview.mp4'}],'one.mp4',4)
 assert.throws(()=>buildEpisodeImport(next.files),/正片视频版本/)
})

test('chapters advance to next chapter without mixing episode folders',()=>{
 const files=[
  {id:10,file_path:'chapter1.mp4',filename:'第一章_烟草.mp4',section_id:4,episode_number:1,episode_unit:'章'},
  {id:11,file_path:'chapter2.mp4',filename:'第二章_猴子.mp4',section_id:4,episode_number:2,episode_unit:'章',folder_name:'第二章'},
  {...materials[1],episode_unit:'集'}
 ]
 assert.deepEqual(nextEpisodeFiles(files,'chapter1.mp4',4).files.map(file=>file.id),[11])
 assert.throws(()=>nextEpisodeFiles(files,'chapter2.mp4',4),/第3章/)
})
