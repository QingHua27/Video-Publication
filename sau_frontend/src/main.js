import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import pinia from './stores'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import './styles/index.scss'
import './styles/monochrome-theme.css'
import './styles/material-folders.css'
import './styles/studio-theme.css'
import './styles/publish-dense.css'
import './styles/episode-picker.css'
import './styles/publish-reference.css'
import './styles/task-status.css'
import './styles/reference-layout.css'
import './styles/apple-studio.css'
import './styles/themes.css'
import './styles/botanical-theme.css'
import './styles/studio-layout.css'
import {initializeTheme} from './utils/themes.mjs'

let themeStorage
try{themeStorage=window.localStorage}catch{}
initializeTheme(document.documentElement,themeStorage)
const app = createApp(App)

// 注册 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(router)
app.use(pinia)
app.use(ElementPlus)
app.mount('#app')
