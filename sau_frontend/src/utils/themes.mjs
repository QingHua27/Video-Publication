export const THEME_STORAGE_KEY='omnipost.appearance.theme.v1'
export const DEFAULT_THEME='botanical'
export const themes=Object.freeze([
 Object.freeze({id:'apple',name:'苹果浅色',description:'清透玻璃 · 简洁蓝白',surface:'#f3f6fc',accent:'#087cf1',preview:'apple',sidebarWidth:248}),
 Object.freeze({id:'botanical',name:'复古植物水彩',description:'温润纸纹 · 植物水彩',surface:'#f5f1e5',accent:'#2f643d',preview:'botanical',sidebarWidth:248,artwork:'/themes/botanical/botanical-overlay.png'})
])
export const validTheme=id=>themes.some(theme=>theme.id===id)
export function loadTheme(storage){
 try{const saved=storage.getItem(THEME_STORAGE_KEY);return validTheme(saved)?saved:DEFAULT_THEME}catch{return DEFAULT_THEME}
}
export function applyTheme(id,root,storage){
 const selected=validTheme(id)?id:DEFAULT_THEME
 root.dataset.theme=selected
 root.style.colorScheme='light'
 try{storage?.setItem(THEME_STORAGE_KEY,selected)}catch{}
 return selected
}
export function initializeTheme(root,storage){return applyTheme(loadTheme(storage),root,storage)}
