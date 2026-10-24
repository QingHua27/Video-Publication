const storageKey = account => `omnipost.collection.v1:${account.type}:${account.filePath}`

export function saveCollectionPreference(storage, account, value) {
  if (!account) return
  try { storage.setItem(storageKey(account), JSON.stringify(value || '')) } catch {}
}

export function restoreCollectionPreference(storage, account, items) {
  if (!account) return undefined
  try {
    const value = JSON.parse(storage.getItem(storageKey(account)))
    if (typeof value !== 'string') return undefined
    return value === '' || items.some(item => item.value === value && !item.disabled) ? value : undefined
  } catch { return undefined }
}

const chineseNumber = number => {
  if(number===0)return '零'
  const digits='零一二三四五六七八九',units=['','十','百','千']
  if(number>=10000)return String(number)
  let text='',zero=false
  for(let i=3;i>=0;i--){
    const digit=Math.floor(number/10**i)%10
    if(digit){if(zero)text+='零';text+=digits[digit]+units[i];zero=false}
    else if(text && number%10**i)zero=true
  }
  return text.replace(/^一十/,'十')
}
export function episodeTitleSuffix(tab){
  const source=tab.fileList?.[0]
  if(!source || tab.fileList.length!==1)return ''
  const number=Number(source.episode_number)
  const match=String(source.name || '').match(/第([零〇一二两三四五六七八九十百千万0-9]+)(集|章)/)
  const unit=source.episode_unit || match?.[2] || '集'
  if(Number.isInteger(number) && number>0)return `第${unit==='章'?chineseNumber(number):number}${unit}`
  if(match)return match[0]
  return ''
}
export function collectionEpisodeTitle(tab,name){
  const suffix=episodeTitleSuffix(tab)
  return suffix ? `${name} · ${suffix}` : name
}
export function applyCollectionTitle(tab, name) {
  if (!name) return
  if (!tab.title?.trim() || tab.title === tab.autoCollectionTitle) {
    tab.title = collectionEpisodeTitle(tab,name)
    tab.autoCollectionTitle = tab.title
  }
}
