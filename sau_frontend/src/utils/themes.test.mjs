import test from 'node:test'
import assert from 'node:assert/strict'
import {themes,DEFAULT_THEME,THEME_STORAGE_KEY,loadTheme,applyTheme,initializeTheme} from './themes.mjs'
const storage=()=>{const data=new Map();return {getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)}}
test('theme registry has unique stable IDs and metadata for picker expansion',()=>{
 assert.equal(new Set(themes.map(t=>t.id)).size,themes.length)
 for(const theme of themes){assert.ok(theme.name&&theme.description&&theme.accent&&theme.surface)}
})
test('first use defaults to botanical; persisted choice restores before mount',()=>{
 const store=storage(),root={dataset:{},style:{}}
 assert.equal(initializeTheme(root,store),DEFAULT_THEME)
 applyTheme('apple',root,store)
 assert.equal(store.getItem(THEME_STORAGE_KEY),'apple')
 assert.equal(initializeTheme(root,store),'apple');assert.equal(root.dataset.theme,'apple')
})
test('unknown themes and unavailable storage cannot break application startup',()=>{
 const broken={getItem(){throw Error('denied')},setItem(){throw Error('denied')}}
 assert.equal(loadTheme(broken),DEFAULT_THEME)
 assert.equal(loadTheme({getItem:()=>'<script>'}),DEFAULT_THEME)
 const root={dataset:{},style:{}}
 assert.equal(applyTheme('unknown',root,broken),DEFAULT_THEME)
})
