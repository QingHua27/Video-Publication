import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {fileURLToPath} from 'node:url'
import {resolveConfig} from '../sau_frontend/node_modules/vite/dist/node/index.js'

test('local preview leaves browser opening to start.cmd exactly once',async()=>{
 const root=fileURLToPath(new URL('../sau_frontend',import.meta.url))
 const config=await resolveConfig({root},'serve','production','production',true)
 assert.equal(config.preview.open,false,'Preview must not inherit server.open')
 const script=readFileSync(new URL('../start.cmd',import.meta.url),'utf8')
 assert.equal(script.split(/\r?\n/).filter(line=>/^start\s+.*http:\/\/127\.0\.0\.1:5173\//i.test(line)).length,1)
})
