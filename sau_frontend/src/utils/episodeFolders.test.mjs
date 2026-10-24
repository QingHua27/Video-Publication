import test from 'node:test'
import assert from 'node:assert/strict'
import {episodeFolders} from './episodeFolders.mjs'
test('folders sort numerically, keep ambiguous versions, all covers and publication marks',()=>{
 const files=[{id:1,filename:'第十集.mp4',file_path:'10.mp4',folder_name:'第十集',episode_number:10,material_role:'video'},
 {id:2,filename:'第二集.mp4',file_path:'2.mp4',folder_name:'第二集',episode_number:2,material_role:'video'},
 {id:3,filename:'第二集新版.mp4',file_path:'2v.mp4',folder_name:'第二集',episode_number:2,material_role:'video'},
 ...['landscape','portrait','recommendation'].map((kind,i)=>({id:i+4,file_path:`${kind}.png`,folder_name:'第二集',episode_number:2,material_role:`${kind}_cover`}))]
 const folders=episodeFolders(files,[{id:1,source_path:'2.mp4',platform:6,status:'published'}])
 assert.equal(folders[0].name,'第二集');assert.equal(folders[0].videos.length,2);assert.equal(folders[0].coverCount,3)
 assert.equal(folders[0].preview,'landscape.png');assert.equal(folders[0].publications.length,1)
})
