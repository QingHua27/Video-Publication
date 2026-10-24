import test from 'node:test'
import assert from 'node:assert/strict'
import {materialPublications} from './materialPublication.mjs'
test('same episode marks other versions only within its section; ignores failed records',()=>{
 const material={file_path:'D:/剧一/第二集新版.mp4',section_id:1,episode_number:2}
 const rows=[{source_path:'D:/剧一/第二集.mp4',material_section_id:1,episode:2,status:'published'},
 {source_path:'D:/剧二/第二集.mp4',material_section_id:2,episode:2,status:'published'},
 {source_path:material.file_path,status:'failed'}]
 assert.deepEqual(materialPublications(material,rows),[rows[0]])
})
test('exact Windows path matches without case sensitivity; pending remains distinct',()=>{
 const row={source_path:'D:\\剧一\\第一集.mp4',status:'pending'}
 assert.deepEqual(materialPublications({file_path:'d:/剧一/第一集.mp4'},[row]),[row])
})
