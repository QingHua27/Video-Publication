<template>
  <div id="app" class="monochrome-shell reference-shell" :class="{'publish-shell':route.path === '/publish-center'}" :style="{'--publish-sidebar-width':`${sidebarWidth}px`}">
    <el-container>
      <el-aside :width="`${sidebarWidth}px`">
        <div class="sidebar">
          <div class="logo">
            <span class="studio-brand-mark" aria-hidden="true"><StudioNavIcon name="publish" /></span>
            <h2 v-show="!isCollapse">创作工作台</h2>
          </div>
          <el-menu
            :router="true"
            :default-active="activeMenu"
            :collapse="isCollapse"
            class="sidebar-menu"
            background-color="#001529"
            text-color="#fff"
            active-text-color="#409EFF"
          >
            <el-menu-item index="/" aria-label="首页" title="首页">
              <el-icon><StudioNavIcon name="home" /></el-icon>
              <span>首页</span>
            </el-menu-item>
            <el-menu-item index="/account-management" aria-label="账号管理" title="账号管理">
              <el-icon><StudioNavIcon name="account" /></el-icon>
              <span>账号管理</span>
            </el-menu-item>
            <el-menu-item index="/material-management" aria-label="素材管理" title="素材管理">
              <el-icon><StudioNavIcon name="materials" /></el-icon>
              <span>素材管理</span>
            </el-menu-item>
            <el-menu-item index="/publish-center" aria-label="发布中心" title="发布中心">
              <el-icon><StudioNavIcon name="publish" /></el-icon>
              <span>发布中心</span>
            </el-menu-item>
            <el-menu-item index="/data-center" aria-label="数据中心" title="数据中心">
              <el-icon><StudioNavIcon name="data" /></el-icon>
              <span>数据中心</span>
            </el-menu-item>
            <el-menu-item index="/about" aria-label="关于" title="关于">
              <el-icon><StudioNavIcon name="about" /></el-icon>
              <span>关于</span>
            </el-menu-item>
          </el-menu>
          <div class="sidebar-bottom">
            <ThemePicker :collapsed="isCollapse" :model-value="themeId" @update:model-value="changeTheme"/>
            <el-button class="exit-app-button" :loading="exiting" :disabled="exiting" aria-label="退出并停止服务" title="退出并停止本机前后端服务" @click="exitApplication">
              <el-icon><StudioNavIcon name="exit" /></el-icon><span v-show="!isCollapse" class="exit-button-label">退出</span>
            </el-button>
          </div>
        </div>
      </el-aside>
      <el-container>
        <el-header>
          <div v-if="route.path === '/publish-center'" class="reference-publish-topbar"><strong class="reference-workspace-title">发布中心</strong><div id="publish-header-slot" /></div>
          <div v-else class="header-content">
            <div class="header-left">
              <el-icon class="toggle-sidebar" @click="toggleSidebar"><Fold /></el-icon>
            </div>
            <div class="header-right"><span class="workspace-title">{{ {'/':'首页','/account-management':'账号管理','/material-management':'素材管理','/publish-center':'发布中心','/data-center':'数据中心','/about':'关于'}[route.path] || '工作台' }}</span></div>
          </div>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
    <div v-if="themeId==='botanical'" class="botanical-art-overlay" aria-hidden="true"><i class="botanical-art-left"/><i class="botanical-art-top"/><i class="botanical-art-right"/></div>
    <div v-if="exitScreen" class="exit-screen" role="status" aria-live="polite"><div class="exit-screen-content">
      <el-icon class="exit-screen-icon"><SwitchButton /></el-icon>
      <h1>{{ exitDisconnected ? '已退出' : '正在退出…' }}</h1>
      <p>{{ exitDisconnected ? '本地服务连接已断开，可以关闭此页。' : '已请求停止本机前后端服务，正在等待退出。' }}</p>
      <small>如果浏览器未自动关闭，请手动关闭当前标签页。</small>
    </div></div>
  </div>
</template>

<script setup>
import { ref, computed, provide } from 'vue'
import StudioNavIcon from './components/StudioNavIcon.vue'
import ThemePicker from './components/ThemePicker.vue'
import {applyTheme,DEFAULT_THEME,themes} from './utils/themes.mjs'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { http } from '@/utils/request'
import {
  HomeFilled, User, DataLine, InfoFilled,
  Fold, Picture, Upload, SwitchButton
} from '@element-plus/icons-vue'

const route = useRoute()

// 当前激活的菜单项
const activeMenu = computed(() => {
  return route.path
})

// 侧边栏折叠状态
const isCollapse = ref(false)
const themeId=ref(document.documentElement.dataset.theme || DEFAULT_THEME)
const sidebarWidth=computed(()=>isCollapse.value ? 64 : themes.find(theme=>theme.id===themeId.value)?.sidebarWidth || 207)
const changeTheme=id=>{
 let storage
 try{storage=window.localStorage}catch{}
 themeId.value=applyTheme(id,document.documentElement,storage)
 requestAnimationFrame(()=>window.dispatchEvent(new Event('resize')))
}
const exiting = ref(false)
const exitScreen = ref(false)
const exitDisconnected = ref(false)
const exitApplication = async () => {
  if (exiting.value) return
  exiting.value = true
  try {
    await http.post('/local/exit', {}, {headers:{'X-OmniPost-Exit':'1'}})
    exitScreen.value = true
    try { window.close() } catch { /* Browser may disallow closing a user-opened tab. */ }
    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'
    for (let attempt=0; attempt<6; attempt++) {
      await new Promise(resolve=>setTimeout(resolve,1500))
      try { await fetch(`${base}/local/status`,{cache:'no-store',signal:AbortSignal.timeout(1500)}) }
      catch { exitDisconnected.value = true; return }
    }
    exitScreen.value = false
    ElMessage.error('服务未能自动停止，请使用项目目录的 stop.cmd')
  } catch {
    // The shared HTTP client already displays the request failure once.
  } finally { exiting.value = false }
}

// 切换侧边栏折叠状态
const toggleSidebar = () => {
  isCollapse.value = !isCollapse.value
}
provide('toggleStudioSidebar',toggleSidebar)
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

#app {
  min-height: 100vh;
}

.el-container {
  height: 100vh;
}

.el-aside {
  background-color: #001529;
  color: #fff;
  height: 100vh;
  overflow: hidden;
  transition: width 0.3s;
  
  .sidebar {
    display: flex;
    flex-direction: column;
    height: 100%;
    
    .logo {
      height: 60px;
      padding: 0 16px;
      display: flex;
      align-items: center;
      background-color: #002140;
      overflow: hidden;
      
      .logo-img {
        width: 32px;
        height: 32px;
        margin-right: 12px;
      }
      
      h2 {
        color: #fff;
        font-size: 16px;
        font-weight: 600;
        white-space: nowrap;
        margin: 0;
      }
    }
    
    .sidebar-menu {
      border-right: none;
      flex: 1;
      
      .el-menu-item {
        display: flex;
        align-items: center;
        
        .el-icon {
          margin-right: 10px;
          font-size: 18px;
        }
      }
    }
  }
}

.el-header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  padding: 0;
  height: 60px;
  
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 100%;
    padding: 0 16px;
    
    .header-left {
      .toggle-sidebar {
        font-size: 20px;
        cursor: pointer;
        color: $text-regular;
        
        &:hover {
          color: $primary-color;
        }
      }
    }
    
    .header-right {
      .user-dropdown {
        display: flex;
        align-items: center;
        cursor: pointer;
        
        .username {
          margin: 0 8px;
          color: $text-regular;
        }
        
        .el-icon {
          font-size: 12px;
          color: $text-secondary;
        }
      }
    }
  }
}

.el-main {
  background-color: $bg-color-page;
  padding: 20px;
  overflow-y: auto;
}
</style>
<style scoped>
.sidebar-bottom{margin-top:auto;border-top:1px solid #e7e7e7;padding:14px 10px 18px}
.exit-app-button{width:100%;justify-content:flex-start;background:transparent;border:0;border-radius:4px;color:#666;gap:10px;height:38px}
.exit-app-button:hover{color:#171717;background:#f4f4f4}.exit-app-button .el-icon{color:#b07a70;font-size:18px}.exit-app-button span{font-size:13px}
.exit-screen{position:fixed;inset:0;z-index:10000;background:#fafafa;display:grid;place-items:center;padding:24px;text-align:center}
.exit-screen-icon{font-size:32px;color:#b07a70}.exit-screen h1{font-size:26px;font-weight:550;margin:20px 0 12px;color:#222}.exit-screen p{font-size:14px;color:#666;line-height:1.8}.exit-screen small{font-size:12px;color:#999}
@media(max-width:930px){.exit-app-button{justify-content:center;padding:0}.exit-button-label{display:none}.sidebar-bottom{padding:12px 7px}.exit-app-button :deep(.el-icon){display:inline-flex}}
.monochrome-shell .el-aside{background:#fff;color:#333;border-right:1px solid #ddd}
.monochrome-shell .sidebar .logo{background:#fff;border-bottom:1px solid #eee}
.monochrome-shell .sidebar .logo h2{color:#222;font-size:14px}
.monochrome-shell .sidebar-menu{background:#fff!important;--el-menu-bg-color:#fff;--el-menu-text-color:#737373;--el-menu-active-color:#171717;--el-menu-hover-bg-color:#f6f6f6}
.monochrome-shell .sidebar-menu .el-menu-item{color:#777;margin:4px 10px;border-radius:4px;height:44px;font-size:13px}
.monochrome-shell .sidebar-menu .el-menu-item.is-active{background:#191919;color:#fff}
.monochrome-shell .sidebar-menu .el-menu-item:nth-child(1) .el-icon{color:#658ac4}
.monochrome-shell .sidebar-menu .el-menu-item:nth-child(2) .el-icon{color:#9a7bc0}
.monochrome-shell .sidebar-menu .el-menu-item:nth-child(3) .el-icon{color:#59a293}
.monochrome-shell .sidebar-menu .el-menu-item:nth-child(4) .el-icon{color:#7da7e6}
.monochrome-shell .sidebar-menu .el-menu-item:nth-child(5) .el-icon{color:#d59d4e}
.monochrome-shell .sidebar-menu .el-menu-item:nth-child(6) .el-icon{color:#7d91ab}
.monochrome-shell .el-header{height:44px;box-shadow:none;border-bottom:1px solid #eee}
.monochrome-shell .el-main{background:#fafafa;padding:28px}
@media(max-width:930px){.monochrome-shell .el-aside{width:64px!important}.monochrome-shell .sidebar-menu .el-menu-item{padding:0!important;justify-content:center;margin:4px 7px}.monochrome-shell .sidebar-menu .el-menu-item span,.monochrome-shell .logo h2{display:none}.monochrome-shell .sidebar-menu .el-menu-item .el-icon{margin:0}.monochrome-shell .el-main{padding:16px}.monochrome-shell .sidebar .logo{padding:0 10px}}
@media(max-width:570px){.monochrome-shell .el-main{padding:12px}}
</style>
