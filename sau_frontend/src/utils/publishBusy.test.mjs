import test from 'node:test'
import assert from 'node:assert/strict'
import {publishBusyState} from './publishBusy.mjs'
test('locks during submission, queued uploads, running uploads and retries',()=>{
 for(const state of [{publishing:true},{destinationResults:[{status:'queued'}]},{destinationResults:[{status:'running'}]}]){
  const result=publishBusyState({selectedAccounts:[1],...state})
  assert.equal(result.disabled,true);assert.equal(result.loading,true)
 }
})
test('confirmation remains locked and terminal jobs release the submit button',()=>{
 assert.equal(publishBusyState({selectedAccounts:[1],destinationResults:[{status:'awaiting_confirmation'}]}).disabled,true)
 for(const status of ['failed','completed','cancelled'])assert.equal(publishBusyState({selectedAccounts:[1],destinationResults:[{status}]}).disabled,false)
})

test('preflight locks submission and exposes its own busy label',()=>{const state=publishBusyState({preflighting:true,selectedAccounts:[1],destinationResults:[]});assert.equal(state.disabled,true);assert.match(state.label,/检查素材/)})
