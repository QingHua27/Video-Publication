import test from 'node:test'
import assert from 'node:assert/strict'
import {automationOutcome,automationNextAvailable} from './publishAutomation.mjs'
test('only completed destinations and collections allow advancing',()=>{
 const done={status:'completed',jobId:'j'}
 assert.equal(automationOutcome([done]),'next')
 for(const status of ['running','queued'])assert.equal(automationOutcome([{...done,status}]),'waiting')
 for(const status of ['failed','awaiting_confirmation','cancelled'])assert.equal(automationOutcome([{...done,status}]),'paused')
 assert.equal(automationOutcome([{...done,collectionTask:{status:'waiting'}}]),'waiting')
 assert.equal(automationOutcome([{...done,collectionTask:{status:'failed'}}]),'paused')
 assert.equal(automationOutcome([{...done,windowVisible:true}]),'paused')
 assert.equal(automationOutcome([{...done,submissionPayload:{dryRun:true}}]),'paused')
})
test('end of series differs from missing intermediate episode',()=>{
 const files=[{file_path:'one',section_id:1,episode_number:1},{file_path:'three',section_id:1,episode_number:3}]
 assert.equal(automationNextAvailable(files,'one',1),true)
 assert.equal(automationNextAvailable(files,'three',1),false)
 assert.throws(()=>automationNextAvailable(files,'local',1))
})
