import test from 'node:test'
import assert from 'node:assert/strict'
import { buildDestinations, takePlatformSettings, defaultAccountSelection, videoCoverPayload, platformsWithSelectedAccounts } from './publishTargets.mjs'

const accounts = [
  {id: 1, platform: '抖音', filePath: 'douyin.json', name: 'D'},
  {id: 2, platform: 'B站', filePath: 'bili.json', name: 'B'},
  {id: 3, platform: '快手', filePath: 'ks.json', name: 'K'},
]

test('an account can restore its platform after deselection including all deselected', () => {
  let platforms=platformsWithSelectedAccounts([3,6],[1],accounts)
  assert.deepEqual(platforms,[3])
  platforms=platformsWithSelectedAccounts(platforms,[1,2],accounts)
  assert.deepEqual(platforms,[3,6])
  platforms=platformsWithSelectedAccounts(platforms,[],accounts)
  assert.deepEqual(platforms,[])
  platforms=platformsWithSelectedAccounts(platforms,[2],accounts)
  assert.deepEqual(platforms,[6])
  assert.deepEqual(buildDestinations(platforms,[2],accounts).map(item=>item.account.id),[2])
})

test('cover directions are never substituted across platform cover slots', () => {
  const dual={landscape:{path:'16x9.png'},recommendation:{path:'4x3.png'}}
  assert.equal(videoCoverPayload(6,dual).bilibiliCover43,'4x3.png')
  assert.equal(videoCoverPayload(6,dual).thumbnail,'16x9.png')
  assert.equal(videoCoverPayload(3,dual).bilibiliCover43,undefined)
  const cover={portrait:{path:'shared.png'}}
  for (const key of [1,2,4]) {
    assert.equal(videoCoverPayload(key,cover).thumbnail,'shared.png')
  }
  for (const key of [3,5,6,7]) assert.equal(videoCoverPayload(key,cover).thumbnail,'')
  for (const key of [1,2,4]) assert.equal(videoCoverPayload(key,{landscape:{path:'wide.png'}}).thumbnail,'')
  assert.equal(videoCoverPayload(3,cover).portraitCover,'shared.png')
  assert.deepEqual(videoCoverPayload(6,{}),{thumbnail:'',portraitCover:''})
  const both={landscape:{path:'wide.png'},portrait:{path:'tall.png'}}
  assert.deepEqual(videoCoverPayload(3,both),{thumbnail:'wide.png',portraitCover:'tall.png'})
  assert.equal(videoCoverPayload(2,both).thumbnail,'tall.png')
  assert.equal(videoCoverPayload(6,both).thumbnail,'wide.png')
})
test('each account goes only to its own selected platform', () => {
  const targets = buildDestinations([3,6], [1,2,3], accounts)
  assert.deepEqual(targets.map(t=>[t.platform,t.account.id]), [[3,1],[6,2]])
})
test('all selected platforms need accounts before any task is submitted', () => {
  assert.throws(()=>buildDestinations([3,6], [1], accounts), /B站/)
})
test('duplicates do not create duplicate publish destinations', () => {
  assert.equal(buildDestinations([3,3], [1,1], accounts).length,1)
})
test('platform cover choices and images are isolated snapshots', () => {
  const original={coverMode:'single',coverImage:'a.jpg',coverImages:[{path:'a.jpg'}]}
  const saved=takePlatformSettings(original)
  original.coverMode='none';original.coverImages[0].path='b.jpg'
  assert.equal(saved.coverMode,'single')
  assert.equal(saved.coverImage,'a.jpg')
  assert.equal(saved.coverImages[0].path,'a.jpg')
})
test('all added platforms and all their accounts are selected by default', () => {
  const result=defaultAccountSelection(accounts)
  assert.deepEqual(new Set(result.platforms),new Set([3,6,4]))
  assert.deepEqual(result.accountIds,[1,2,3])
})

test('unchecking the last Kuaishou account removes Kuaishou from selected platforms', async () => {
  const { platformsWithSelectedAccounts } = await import('./publishTargets.mjs')
  const accounts = [{id:1,platform:'抖音'},{id:2,platform:'快手'},{id:3,platform:'抖音'}]
  assert.deepEqual(platformsWithSelectedAccounts([3,4],[1],accounts),[3])
  assert.deepEqual(platformsWithSelectedAccounts([3,4],[1,2],accounts),[3,4])
  assert.deepEqual(platformsWithSelectedAccounts([3,4],[],accounts),[])
  assert.deepEqual(platformsWithSelectedAccounts([3,4],[3],accounts),[3])
})
