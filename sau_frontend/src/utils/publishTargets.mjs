export const platformNames = {1:'小红书',2:'视频号',3:'抖音',4:'快手',5:'百家号',6:'B站',7:'今日头条',8:'搜狐',9:'知乎'}

export function videoCoverPayload(platform, covers = {}) {
  const landscape = covers.landscape?.path || (platform !== 6 ? covers.recommendation?.path : '') || ''
  const portrait = covers.portrait?.path || ''
  const extra = platform === 6 && covers.recommendation?.path ? {bilibiliCover43: covers.recommendation.path} : {}
  return {...extra,thumbnail:[1,2,4].includes(platform) ? portrait : ([3,5,6,7].includes(platform) ? landscape : ''),
    portraitCover:platform === 3 ? portrait : ''}
}

export function buildDestinations(platforms, selectedIds, accounts) {
  const ids = new Set(selectedIds)
  const result = []
  for (const platform of new Set(platforms)) {
    const matches = accounts.filter(account => ids.has(account.id) && account.platform === platformNames[platform])
    if (!matches.length) throw new Error(`请为${platformNames[platform]}选择发布账号`)
    for (const account of matches) result.push({platform, account})
  }
  if (!result.length) throw new Error('请选择发布平台和账号')
  return result
}

export function defaultAccountSelection(accounts) {
  const known=accounts.filter(account => Object.values(platformNames).includes(account.platform))
  const platforms=[...new Set(known.map(account => Number(Object.keys(platformNames).find(key=>platformNames[key]===account.platform))))]
  return {platforms, accountIds:known.map(account=>account.id)}
}

export const platformSettingKeys = ['contentType','workStatement','isDraft','isOriginal','aiGenerated','bilibiliCreationStatement','bilibiliCategory','productLink','productTitle','dryRun','coverMode','coverImage','coverImages','coverPreviewUrl','coverFileName']

export function takePlatformSettings(tab) {
  return Object.fromEntries(platformSettingKeys.map(key => [key, Array.isArray(tab[key]) ? tab[key].map(item => ({...item})) : tab[key]]))
}

export function platformsWithSelectedAccounts(platforms, selectedIds, accounts) {
  const ids = new Set(selectedIds)
  const candidates = [...new Set([...platforms, ...Object.keys(platformNames).map(Number)])]
  return candidates.filter(platform => accounts.some(account => ids.has(account.id) && account.platform === platformNames[platform]))
}
