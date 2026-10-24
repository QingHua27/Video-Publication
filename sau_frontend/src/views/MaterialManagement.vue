<template>
  <div class="material-management">
    <div class="page-header"><div class="page-kicker">WORKSPACE / LIBRARY</div>
      <h1>素材管理</h1><p class="page-description">整理视频与图片，为下一次发布做好准备。</p>
    </div>
    
    <div class="material-list-container">
      <div class="material-sections" aria-label="素材分区">
        <button :class="{'section-active':activeSection===0}" @click="chooseSection(0)" @dragover.prevent @drop="dropFolders($event,0)">未分区</button>
        <button v-for="section in sections" :key="section.id" :class="{'section-active':activeSection===section.id}" @click="chooseSection(section.id)" @dragover.prevent @drop="dropFolders($event,section.id)">{{ section.name }} <small>{{ section.count }}</small></button>
        <el-button text @click="addSection">＋ 新建分区</el-button>
        <el-button v-if="activeSection!==0" text type="danger" :loading="deletingSection" :disabled="isUploading || movingFolders || deletingFolderRecords" @click="deleteCurrentSection">删除当前分区</el-button>
      </div>
      <details v-if="linkedDirectories.length" class="linked-directory-summary"><summary>已关联 {{ linkedDirectories.length }} 个本地文件夹 · 每次刷新自动同步<span v-if="linkedDirectories.some(item=>item.status!=='ready')"> · 部分文件夹无法访问</span></summary><div v-for="directory in linkedDirectories" :key="directory.id" class="linked-directory-row"><span :title="directory.path">{{ directory.path }}</span><small>{{ sections.find(section=>section.id===directory.section_id)?.name || '未分区' }} · {{ directory.message }}</small></div></details>
      <div v-if="selectedFolder === null" class="folder-move-toolbar"><el-button :disabled="!episodeFolders.length || allFoldersSelected" @click="selectedFolderNames=episodeFolders.map(folder=>folder.name)">全选文件夹</el-button><el-button :disabled="!selectedFolderNames.length" @click="selectedFolderNames=[]">取消全选</el-button><el-button type="danger" :disabled="!selectedFolderNames.length || movingFolders || deletingFolderRecords" :loading="deletingFolderRecords" @click="deleteSelectedFolderRecords">批量删除记录</el-button><span>已选 {{ selectedFolderNames.length }} / {{ episodeFolders.length }} 个文件夹</span><el-select v-model="moveTarget" aria-label="目标分区" placeholder="移动到分区"><el-option v-if="activeSection!==0" label="未分区" :value="0"/><el-option v-for="section in sections.filter(item=>item.id!==activeSection)" :key="section.id" :value="section.id" :label="section.name"/></el-select><el-button :disabled="!selectedFolderNames.length || moveTarget === null" :loading="movingFolders" @click="moveSelectedFolders()">移动所选文件夹</el-button></div>
      <div class="material-search">
        <el-input
          v-model="searchKeyword"
          placeholder="输入文件名搜索"
          prefix-icon="Search"
          clearable
          @clear="handleSearch"
          @input="handleSearch"
        />
        <div class="action-buttons">
          <el-button
            type="danger"
            :disabled="selectedMaterials.length === 0"
            :loading="isBatchDeleting"
            @click="handleBatchDelete"
          >
            批量删除{{ selectedMaterials.length > 0 ? ` (${selectedMaterials.length})` : '' }}
          </el-button>
          <el-button type="primary" @click="handleUploadMaterial">关联素材文件夹</el-button>
          <el-button type="info" @click="fetchMaterials" :loading="isRefreshing">
            <el-icon :class="{ 'is-loading': isRefreshing }"><Refresh /></el-icon>
            <span>{{ isRefreshing ? '同步中' : '刷新' }}</span>
          </el-button>
        </div>
      </div>

      <div class="material-folder-nav">
        <el-button text @click="openFolder(null)"><el-icon><Folder /></el-icon>全部素材</el-button>
        <span v-if="selectedFolder !== null">/ {{ selectedFolder === 'all' ? '全部文件' : selectedFolder }}</span>
        <span v-else class="folder-summary">{{ episodeFolders.length }} 个文件夹 · {{ sectionMaterials.length }} 个文件</span>
        <el-button v-if="selectedFolder === null" text @click="openFolder('all')">查看全部文件</el-button>
      </div>
      <p class="folder-classification-hint">拖动空白处或未选中的卡片可框选；Ctrl / ⌘ 追加选择。选中后拖到上方分区即可移动。按文件名自动归集：同一集的视频、横竖封面及不同版本放在同一文件夹；未识别集数的文件放入“未分类”。</p>
      <div v-if="selectedFolder === null && !searchKeyword.trim()" class="episode-folder-grid" @pointerdown="startBoxSelection($event,'folders')" @click.capture="guardFolderClick">
        <article v-for="folder in episodeFolders" :key="folder.name" :data-folder-name="folder.name" class="episode-folder-card selectable-folder" :class="{'folder-selected':selectedFolderNames.includes(folder.name)}" :draggable="selectedFolderNames.includes(folder.name)" @dragstart="beginFolderDrag($event,folder.name)" @dragend="draggedFolders=null">
          <el-checkbox :model-value="selectedFolderNames.includes(folder.name)" :aria-label="`选择${folder.name}`" @change="toggleFolder(folder.name)"/>
          <button class="episode-folder-open" @click="openFolder(folder.name)"><el-icon class="episode-folder-icon"><FolderOpened /></el-icon><div><strong>{{ folder.name }}</strong><span>{{ folder.count }} 个文件</span><small>{{ folder.videos }} 视频 · {{ folder.images }} 图片<span v-if="folder.other"> · {{ folder.other }} 其他</span></small></div><span class="folder-open-arrow">↗</span></button>
        </article>
      </div>
      <div v-if="(selectedFolder !== null || searchKeyword.trim()) && filteredMaterials.length > 0" class="material-list" @pointerdown="startBoxSelection($event,'files')">
        <div class="file-selection-toolbar"><el-button @click="toggleAllFiles">{{ allFilesSelected ? '取消全选' : '全选文件' }}</el-button><span>已选 {{ selectedMaterials.length }} 个文件</span><small>从列表空白或文字处拖动框选，Ctrl / ⌘ 追加选择</small></div>
        <el-table
          ref="materialTableRef"
          :data="filteredMaterials"
          style="width: 100%"
          row-key="id"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="folder_name" label="文件夹" width="110" />
          <el-table-column prop="filename" label="文件名" width="300" />
          <el-table-column label="来源" min-width="180"><template #default="scope"><div class="local-material-path" :title="scope.row.file_path">{{ scope.row.source_kind === 'reference' ? scope.row.file_path : '旧素材库副本' }}</div><el-tag v-if="scope.row.available===false" type="danger">路径失效</el-tag></template></el-table-column>
          <el-table-column label="类型" width="110"><template #default="scope"><el-tag effect="plain">{{ materialRoleLabels[scope.row.material_role] || '文件' }}</el-tag></template></el-table-column>
          <el-table-column prop="filesize" label="文件大小" width="120">
            <template #default="scope">
              {{ scope.row.filesize }} MB
            </template>
          </el-table-column>
          <el-table-column prop="upload_time" label="上传时间" width="180" />
          <el-table-column label="操作">
            <template #default="scope">
              <el-button size="small" @click="handlePreview(scope.row)">预览</el-button>
              <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <div v-else-if="!episodeFolders.length || selectedFolder !== null || searchKeyword.trim()" class="empty-data">
        <el-empty description="暂无素材数据" />
      </div>
    </div>
    
    <div v-if="selectionBox" class="material-selection-box" :style="selectionBox" aria-hidden="true" />
    <!-- 上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="关联素材文件夹"
      class="material-upload-dialog"
      :close-on-click-modal="!isUploading && !isPicking"
      :close-on-press-escape="!isUploading && !isPicking"
      :show-close="!isUploading && !isPicking"
      width="40%"
      @close="handleUploadDialogClose"
    >
      <div class="upload-form">
        <el-form label-width="80px">
          <el-form-item label="分区"><el-select ref="uploadSectionSelect" automatic-dropdown v-model="uploadSectionId" aria-label="添加素材分区" placeholder="请先选择分区" :disabled="isUploading || isPicking" style="width:100%"><el-option label="未分区" :value="0"/><el-option v-for="section in sections" :key="section.id" :value="section.id" :label="section.name"/></el-select></el-form-item>
          <el-form-item label="选择文件夹">
            <div class="upload-kind-picker">
              <el-radio-group v-model="uploadFileKind" :disabled="isUploading" aria-label="扫描素材类型">
                <el-radio-button value="all">全部</el-radio-button><el-radio-button value="video">视频</el-radio-button><el-radio-button value="image">图片</el-radio-button>
              </el-radio-group>
              <span>{{ uploadFileKind === 'video' ? '仅扫描视频' : uploadFileKind === 'image' ? '仅扫描图片' : '自动扫描视频和图片' }}</span>
            </div>
            <div class="local-picker-panel"><el-icon><FolderOpened /></el-icon><strong>关联本地文件夹，自动整理素材</strong><p>包含子文件夹，按集自动整理；每次刷新同步新增和修改，只记录路径，不复制文件。</p><el-button @click="pickLocalFiles" :loading="isPicking" :disabled="isUploading || isPicking">{{ isPicking ? '等待本机窗口选择…' : '选择本地文件夹' }}</el-button><p v-if="uploadSectionId === null" class="section-required-hint" role="status">请先选择上方分区；不需要分类可选择“未分区”。</p><p v-if="isPicking" role="status">请在任务栏中的“OmniPost — 选择本地素材”窗口选择文件夹或取消，最长等待2分钟。</p></div>
          </el-form-item>
          <el-form-item label="" label-width="0px" class="upload-queue-item" v-if="fileList.length > 0">
            <div class="upload-queue-summary"><strong>已选 {{ fileList.length }} 个文件夹</strong><span>{{ Object.values(uploadProgress).filter(item=>item.state==='done').length }} 已关联 · {{ Object.values(uploadProgress).filter(item=>item.state==='failed').length }} 失败</span></div>
            <div class="upload-file-list">
              <div v-for="file in fileList" :key="file.uid" class="upload-file-item">
                <div class="upload-file-row"><span class="file-name" :title="file.path">{{ file.path }}</span><span class="upload-file-size">含子文件夹</span><el-button v-if="!isUploading" link aria-label="移除文件" @click="handleFileRemove(file, fileList.filter(item=>item.uid!==file.uid))">移除</el-button></div>
                <el-progress
                  :percentage="uploadProgress[file.uid]?.percentage || 0"
                  :show-text="false" :stroke-width="4"
                  :status="uploadProgress[file.uid]?.state === 'failed' ? 'exception' : uploadProgress[file.uid]?.state === 'done' ? 'success' : undefined"
                />
                <div class="upload-file-state">{{ uploadProgress[file.uid]?.state === 'done' ? (uploadProgress[file.uid]?.message || '已关联，刷新时自动同步') : uploadProgress[file.uid]?.state === 'failed' ? '关联失败，可重试' : uploadProgress[file.uid]?.state === 'uploading' ? `登记中 ${uploadProgress[file.uid]?.percentage || 0}% · ${uploadProgress[file.uid]?.speed || ''}` : '等待关联' }}</div>
              </div>
            </div>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="uploadDialogVisible = false" :disabled="isUploading || isPicking">关闭</el-button>
          <el-button type="primary" @click="submitUpload" :loading="isUploading" :disabled="isPicking || uploadSectionId === null || !fileList.length || fileList.every(file=>uploadProgress[file.uid]?.state==='done')">
            {{ isUploading ? '扫描中' : '关联并整理' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
    
    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      title="素材预览"
      width="50%"
      :top="'10vh'"
    >
      <div class="preview-container" v-if="currentMaterial">
        <div v-if="isVideoFile(currentMaterial.filename)" class="video-preview">
          <video controls style="max-width: 100%; max-height: 60vh;">
            <source :src="getPreviewUrl(currentMaterial.file_path)" type="video/mp4">
            您的浏览器不支持视频播放
          </video>
        </div>
        <div v-else-if="isImageFile(currentMaterial.filename)" class="image-preview">
          <img :src="getPreviewUrl(currentMaterial.file_path)" style="max-width: 100%; max-height: 60vh;" />
        </div>
        <div v-else class="file-info">
          <p>文件名: {{ currentMaterial.filename }}</p>
          <p>文件大小: {{ currentMaterial.filesize }} MB</p>
          <p>上传时间: {{ currentMaterial.upload_time }}</p>
          <el-button type="primary" @click="downloadFile(currentMaterial)">下载文件</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { Refresh, Upload } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { materialApi } from '@/api/material'
import { useAppStore } from '@/stores/app'

// 获取应用状态管理
const appStore = useAppStore()

// 搜索和状态控制
const sections = ref([])
const activeSection = ref(0)
const linkedDirectories = ref([])
const uploadSectionId = ref(0)
const uploadSectionSelect = ref(null)
const isPicking = ref(false)
const selectedFolderNames = ref([])
const moveTarget = ref(null)
const movingFolders = ref(false)
const draggedFolders = ref(null)
const sectionMaterials = computed(()=>appStore.materials.filter(file=>(file.section_id || 0)===activeSection.value))
const allFoldersSelected = computed(()=>episodeFolders.value.length>0 && episodeFolders.value.every(folder=>selectedFolderNames.value.includes(folder.name)))
const allFilesSelected = computed(()=>filteredMaterials.value.length>0 && filteredMaterials.value.every(file=>selectedMaterials.value.some(item=>item.id===file.id)))
const toggleAllFolders = () => { selectedFolderNames.value = allFoldersSelected.value ? [] : episodeFolders.value.map(folder=>folder.name) }
const setFileSelection = ids => {
  const table=materialTableRef.value
  if (!table) return
  table.clearSelection()
  for (const file of filteredMaterials.value) if (ids.has(file.id)) table.toggleRowSelection(file,true)
}
const toggleAllFiles = () => setFileSelection(new Set(allFilesSelected.value ? [] : filteredMaterials.value.map(file=>file.id)))
const selectionBox = ref(null)
let boxGesture = null
let suppressFolderClick = false
const guardFolderClick = event => {
  if (suppressFolderClick) { event.preventDefault();event.stopPropagation() }
}
const endBoxSelection = () => {
  if (boxGesture?.started && boxGesture.kind==='folders') {
    suppressFolderClick=true
    setTimeout(()=>{suppressFolderClick=false},0)
  }
  boxGesture=null;selectionBox.value=null
  window.removeEventListener('pointermove',moveBoxSelection)
  window.removeEventListener('pointerup',endBoxSelection)
  window.removeEventListener('pointercancel',endBoxSelection)
  window.removeEventListener('blur',endBoxSelection)
  document.body.classList.remove('material-box-selecting')
}
const moveBoxSelection = event => {
  const gesture=boxGesture
  if (!gesture) return
  if (!(event.buttons & 1)) { endBoxSelection();return }
  const left=Math.min(gesture.x,event.clientX),top=Math.min(gesture.y,event.clientY)
  const right=Math.max(gesture.x,event.clientX),bottom=Math.max(gesture.y,event.clientY)
  if (!gesture.started && Math.hypot(right-left,bottom-top)<5) return
  gesture.started=true;event.preventDefault()
  window.getSelection()?.removeAllRanges()
  document.body.classList.add('material-box-selecting')
  selectionBox.value={left:left+'px',top:top+'px',width:right-left+'px',height:bottom-top+'px'}
  const selected=new Set(gesture.initial)
  for (const item of gesture.items) {
    const rect=item.element.getBoundingClientRect()
    if (rect.right>left && rect.left<right && rect.bottom>top && rect.top<bottom) selected.add(item.id)
  }
  if (gesture.kind==='folders') selectedFolderNames.value=[...selected]
  else setFileSelection(selected)
}
const startBoxSelection = (event,kind) => {
  if (event.button!==0 || event.target.closest('input,label,a,.el-checkbox,.el-select,.el-table__header-wrapper,.file-selection-toolbar')) return
  if (event.target.closest('button') && !(kind==='folders' && event.target.closest('.episode-folder-open'))) return
  if (kind==='folders' && event.target.closest('.folder-selected')) return
  endBoxSelection()
  const elements=[...event.currentTarget.querySelectorAll(kind==='folders' ? '[data-folder-name]' : '.el-table__body-wrapper tbody tr')]
  const items=elements.map((element,index)=>({element,id:kind==='folders' ? element.dataset.folderName : filteredMaterials.value[index]?.id})).filter(item=>item.id!==undefined)
  boxGesture={x:event.clientX,y:event.clientY,kind,items,started:false,initial:event.ctrlKey || event.metaKey ? (kind==='folders' ? [...selectedFolderNames.value] : selectedMaterials.value.map(item=>item.id)) : []}
  window.addEventListener('pointermove',moveBoxSelection,{passive:false})
  window.addEventListener('pointerup',endBoxSelection)
  window.addEventListener('pointercancel',endBoxSelection)
  window.addEventListener('blur',endBoxSelection)
}
onBeforeUnmount(endBoxSelection)
const loadSections = async () => {
  const response = await materialApi.getSections()
  sections.value = Array.isArray(response.data) ? response.data : []
}
const chooseSection = id => {
  activeSection.value = id
  selectedFolderNames.value = []
  moveTarget.value = null
  openFolder(null)
}
const deletingSection=ref(false)
const deleteCurrentSection=async()=>{
 const section=sections.value.find(item=>item.id===activeSection.value)
 if(!section || deletingSection.value)return
 try{
  await ElMessageBox.confirm(`删除分区“${section.name}”？其中 ${section.count} 条素材及文件夹关联将移到“未分区”。本地文件和发布记录会保留。`,'删除素材分区',{confirmButtonText:'删除分区，保留素材',cancelButtonText:'取消',type:'warning'})
  deletingSection.value=true
  await materialApi.deleteSection(section.id)
  chooseSection(0)
  if(uploadSectionId.value===section.id)uploadSectionId.value=0
  await fetchMaterials()
  ElMessage.success('分区已删除，素材已移到未分区')
 }catch(error){
  if(!['cancel','close'].includes(error))ElMessage.warning(error?.response?.data?.msg || (error?.response?.status===404 || error?.code==='ERR_NETWORK' ? '删除分区接口未就绪，请等当前任务结束后重启后台再试' : error.message || '删除分区失败'))
 }finally{deletingSection.value=false}
}
const addSection = async () => {
  try {
    const {value} = await ElMessageBox.prompt('用剧名或项目名区分素材，最多60字','新建分区',{confirmButtonText:'创建',cancelButtonText:'取消',inputPlaceholder:'例如：米格尔街',inputValidator:value=>!!value?.trim() && value.trim().length<=60 || '请输入1至60字'})
    const response = await materialApi.createSection(value.trim())
    await loadSections()
    chooseSection(response.data.id)
  } catch {}
}
const toggleFolder = name => {
  selectedFolderNames.value = selectedFolderNames.value.includes(name) ? selectedFolderNames.value.filter(item=>item!==name) : [...selectedFolderNames.value,name]
}
const deletingFolderRecords = ref(false)
const deleteSelectedFolderRecords = async () => {
  if (!selectedFolderNames.value.length || deletingFolderRecords.value || movingFolders.value) return
  const sectionId=activeSection.value, folders=[...selectedFolderNames.value]
  const ids=sectionMaterials.value.filter(file=>folders.includes(file.folder_name || '未分类')).map(file=>file.id)
  deletingFolderRecords.value=true
  try {
    await ElMessageBox.confirm(`将删除所选 ${folders.length} 个文件夹中的 ${ids.length} 条素材记录。只删除记录，所有本地原文件及旧素材副本都保留。`, '批量删除素材记录', {confirmButtonText:'仅删除记录',cancelButtonText:'取消',type:'warning'})
    const response=await materialApi.deleteFolderRecords({sectionId,folders,ids})
    if (activeSection.value===sectionId) selectedFolderNames.value=selectedFolderNames.value.filter(name=>!folders.includes(name))
    await Promise.all([fetchMaterials(),loadSections()])
    ElMessage.success(`已删除 ${response.data.deleted} 条素材记录，本地文件已保留`)
  } catch(error) {
    if (error!=='cancel' && error!=='close') ElMessage.error(error?.response?.data?.msg || error.message || '删除记录失败')
  } finally { deletingFolderRecords.value=false }
}
const moveSelectedFolders = async (target=moveTarget.value, folders=[...selectedFolderNames.value], source=activeSection.value) => {
  if (target === null || !folders.length || target === source || movingFolders.value || deletingFolderRecords.value) return
  movingFolders.value = true
  const data={sourceSectionId:source,targetSectionId:target,folders}
  try {
    try { await materialApi.moveFolders(data) }
    catch (error) {
      const message=error?.response?.data?.msg || error.message
      if (!message.includes('同名文件夹')) throw error
      await ElMessageBox.confirm(message+'。文件不会覆盖，将合并显示。','确认合并',{confirmButtonText:'合并并移动',cancelButtonText:'取消'})
      await materialApi.moveFolders({...data,allowMerge:true})
    }
    selectedFolderNames.value=[]
    await Promise.all([fetchMaterials(),loadSections()])
    ElMessage.success('已移动所选文件夹，原文件位置未改变')
  } catch(error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(error?.response?.data?.msg || error.message || '移动失败')
  } finally { movingFolders.value=false }
}
const beginFolderDrag = (event,name) => {
  if (boxGesture) { event.preventDefault();return }
  const folders=selectedFolderNames.value.includes(name) ? [...selectedFolderNames.value] : [name]
  draggedFolders.value={source:activeSection.value,folders}
  event.dataTransfer.setData('application/x-omnipost-folders',JSON.stringify(draggedFolders.value))
  event.dataTransfer.effectAllowed='move'
}
const dropFolders = async (event,target) => {
  event.preventDefault()
  if (!draggedFolders.value) return
  const data=draggedFolders.value;draggedFolders.value=null
  await moveSelectedFolders(target,data.folders,data.source)
}
const searchKeyword = ref('')
const selectedFolder = ref(null)
const materialRoleLabels = {video:'视频',image:'图片',landscape_cover:'横版封面',portrait_cover:'竖版封面',recommendation_cover:'推荐页封面',other:'其他文件'}
const episodeFolders = computed(() => {
  const grouped = new Map()
  for (const material of sectionMaterials.value) {
    const name = material.folder_name || '未分类'
    if (!grouped.has(name)) grouped.set(name, {name, episode:material.episode_number ?? null, count:0, videos:0, images:0, other:0})
    const folder = grouped.get(name)
    folder.count++
    if (material.material_role === 'video' || /\.(mp4|mov|avi|mkv|webm|m4v|flv|wmv)$/i.test(material.filename)) folder.videos++
    else if (/\.(png|jpe?g|webp|gif|bmp)$/i.test(material.filename)) folder.images++
    else folder.other++
  }
  return [...grouped.values()].sort((a,b)=>(a.episode ?? Infinity)-(b.episode ?? Infinity) || a.name.localeCompare(b.name,'zh-CN'))
})
const openFolder = (name) => {
  selectedFolder.value = name
  selectedMaterials.value = []
  searchKeyword.value = ''
  materialTableRef.value?.clearSelection?.()
}
const isRefreshing = ref(false)
const isUploading = ref(false)
const isBatchDeleting = ref(false)

// 表格多选
const materialTableRef = ref(null)
const selectedMaterials = ref([])

// 对话框控制
const uploadDialogVisible = ref(false)
const previewDialogVisible = ref(false)
const currentMaterial = ref(null)

// 文件上传
const fileList = ref([])
const uploadFileKind = ref('all')
const materialUploadAccept = computed(() => {
  const video='video/*,.mp4,.mov,.avi,.mkv,.m4v,.webm,.flv,.wmv'
  const image='image/*,.jpg,.jpeg,.png,.webp,.bmp,.gif'
  return uploadFileKind.value==='video' ? video : uploadFileKind.value==='image' ? image : ''
})
const customFilename = ref('')
const customFilenameDisabled = computed(() => fileList.value.length > 1)
const uploadProgress = ref({}); // { [uid]: { percentage: 0, speed: '' } }


watch(fileList, (newList) => {
  if (newList.length <= 1) {
    // If you want to clear the custom name when going back to single file, uncomment below
    // customFilename.value = ''
  }
});


// 获取素材列表
const fetchMaterials = async () => {
  isRefreshing.value = true
  try {
    const response = await materialApi.getAllMaterials()

    if (response.code === 200) {
      appStore.setMaterials(response.data)
      linkedDirectories.value = response.directories || []
      await loadSections()
      selectedMaterials.value = []
      materialTableRef.value?.clearSelection?.()
      ElMessage.success('刷新成功')
    } else {
      ElMessage.error('获取素材列表失败')
    }
  } catch (error) {
    console.error('获取素材列表出错:', error)
    ElMessage.error('获取素材列表失败')
  } finally {
    isRefreshing.value = false
  }
}

// 过滤素材
const filteredMaterials = computed(() => {
  const files = selectedFolder.value && selectedFolder.value !== 'all'
    ? sectionMaterials.value.filter(material => (material.folder_name || '未分类') === selectedFolder.value)
    : sectionMaterials.value
  if (!searchKeyword.value.trim()) return files
  
  const keyword = searchKeyword.value.toLowerCase()
  return files.filter(material =>
    material.filename.toLowerCase().includes(keyword)
  )
})

// 搜索处理
const handleSearch = () => {
  // 搜索逻辑已通过计算属性实现
}

// 关联素材文件夹
const handleUploadMaterial = async () => {
  await loadSections()
  uploadSectionId.value = sections.value.length ? (activeSection.value || null) : 0
  // 清空变量
  fileList.value = []
  customFilename.value = ''
  uploadProgress.value = {};
  uploadDialogVisible.value = true
}

// 关闭上传对话框时清空变量
const handleUploadDialogClose = () => {
  fileList.value = []
  customFilename.value = ''
  uploadProgress.value = {};
}

// 文件选择变更
const handleFileChange = (file, uploadFileList) => {
  fileList.value = uploadFileList;
  const newProgress = {};
  for (const f of uploadFileList) {
    newProgress[f.uid] = uploadProgress.value[f.uid] || { percentage: 0, speed: '', state:'waiting' };
  }
  uploadProgress.value = newProgress;
}

const handleFileRemove = (file, uploadFileList) => {
  fileList.value = uploadFileList;
  const newProgress = { ...uploadProgress.value };
  delete newProgress[file.uid];
  uploadProgress.value = newProgress;
}

// 提交上传
const submitUpload = async () => {
  const pending = fileList.value.filter(file=>uploadProgress.value[file.uid]?.state !== 'done')
  if (!pending.length || uploadSectionId.value === null) { ElMessage.warning('请先选择分区和本地文件'); return }
  isUploading.value = true
  try {
    for (const file of pending) {
      const result = await materialApi.linkDirectory(file.path,uploadSectionId.value,uploadFileKind.value)
      const directory = result.data.directory
      if(directory?.status==='unavailable')throw new Error(directory.message)
      uploadProgress.value[file.uid] = {state:'done',percentage:100,message:directory?.message || '已关联，刷新时自动同步'}
    }
    ElMessage.success('文件夹已关联，刷新时自动同步素材，不复制文件')
    await fetchMaterials()
  } catch(error) {
    ElMessage.warning(error.message || '文件夹关联失败，请重试')
    for (const file of pending) if(uploadProgress.value[file.uid]?.state!=='done')uploadProgress.value[file.uid] = {state:'failed',percentage:0,speed:''}
  } finally { isUploading.value = false }
}

const pickLocalFiles = async () => {
  if (uploadSectionId.value === null) { ElMessage.warning('请先选择分区，不需要分类可选择“未分区”'); uploadSectionSelect.value?.focus(); return }
  isPicking.value = true
  try {
    const response = await materialApi.pickLocal('folder')
    for (const file of response.data || []) {
      if (fileList.value.some(item=>item.path.toLowerCase()===file.path.toLowerCase())) continue
      const entry = {...file,uid:file.path}
      fileList.value.push(entry)
      uploadProgress.value[entry.uid] = {state:'waiting',percentage:0,speed:''}
    }
  } catch { /* Request client displays the reason. */ }
  finally { isPicking.value = false }
}

// 预览素材
const handlePreview = async (material) => {
  currentMaterial.value = null
  previewDialogVisible.value = true
  ElMessage.info('加载中...')
  try {
    // 等待一小段时间以确保对话框已打开
    await new Promise(resolve => setTimeout(resolve, 100))
    currentMaterial.value = material
  } catch (error) {
    console.error('预览素材出错:', error)
    ElMessage.error('预览加载失败')
    previewDialogVisible.value = false
  }
}

// 表格多选变更
const handleSelectionChange = (selection) => {
  selectedMaterials.value = selection
}

// 删除素材
const handleDelete = (material) => {
  ElMessageBox.confirm(
    material.source_kind === 'reference' ? `移除素材记录 ${material.filename}？原文件会保留。` : `确定要删除旧素材库副本 ${material.filename} 吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        const response = await materialApi.deleteMaterial(material.id)

        if (response.code === 200) {
          appStore.removeMaterial(material.id)
          selectedMaterials.value = selectedMaterials.value.filter(item => item.id !== material.id)
          ElMessage.success('删除成功')
        } else {
          ElMessage.error(response.msg || '删除失败')
        }
      } catch (error) {
        console.error('删除素材出错:', error)
        ElMessage.error('删除失败')
      }
    })
    .catch(() => {
      // 取消删除
    })
}

// 批量删除素材
const handleBatchDelete = () => {
  if (selectedMaterials.value.length === 0) {
    ElMessage.warning('请先选择要删除的素材')
    return
  }

  const count = selectedMaterials.value.length
  ElMessageBox.confirm(
    `确定删除选中的 ${count} 个素材记录？引用的原文件会保留；旧素材库副本会删除。`,
    '批量删除',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      isBatchDeleting.value = true
      const targets = [...selectedMaterials.value]
      let successCount = 0
      let failCount = 0

      try {
        for (const material of targets) {
          try {
            const response = await materialApi.deleteMaterial(material.id)
            if (response.code === 200) {
              appStore.removeMaterial(material.id)
              successCount += 1
            } else {
              failCount += 1
              console.error(`删除素材 ${material.filename} 失败:`, response.msg)
            }
          } catch (error) {
            failCount += 1
            console.error(`删除素材 ${material.filename} 出错:`, error)
          }
        }

        selectedMaterials.value = []
        materialTableRef.value?.clearSelection?.()

        if (failCount === 0) {
          ElMessage.success(`成功删除 ${successCount} 个素材`)
        } else if (successCount === 0) {
          ElMessage.error('批量删除失败')
        } else {
          ElMessage.warning(`成功删除 ${successCount} 个，失败 ${failCount} 个`)
        }
      } finally {
        isBatchDeleting.value = false
      }
    })
    .catch(() => {
      // 取消删除
    })
}

// 获取预览URL
const getPreviewUrl = (filePath) => {
  return materialApi.getMaterialPreviewUrl(filePath)
}

// 下载文件
const downloadFile = (material) => {
  const url = materialApi.downloadMaterial(material.file_path)
  window.open(url, '_blank')
}

// 判断文件类型
const isVideoFile = (filename) => {
  const videoExtensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']
  return videoExtensions.some(ext => filename.toLowerCase().endsWith(ext))
}

const isImageFile = (filename) => {
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
  return imageExtensions.some(ext => filename.toLowerCase().endsWith(ext))
}

// 组件挂载时获取素材列表
onMounted(() => {
  void fetchMaterials()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.linked-directory-summary{margin:12px 0;padding:12px 14px;border:1px solid #e5e9ef;border-radius:8px;background:#fafbfc;font-size:13px;color:#667085}.linked-directory-summary summary{cursor:pointer}.linked-directory-summary summary>span{color:#b87513}.linked-directory-row{display:flex;flex-wrap:wrap;gap:6px 16px;justify-content:space-between;padding-top:10px}.linked-directory-row>span{overflow-wrap:anywhere;min-width:0}.linked-directory-row small{color:#87909c}



@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.material-management {
  
  .page-header {
    margin-bottom: 20px;
    
    h1 {
      font-size: 24px;
      font-weight: 500;
      color: $text-primary;
      margin: 0;
    }
  }
  
  .material-list-container {
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    padding: 20px;
    
    .material-search {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
      
      .el-input {
        width: 300px;
      }
      
      .action-buttons {
        display: flex;
        gap: 10px;
        
        // 仅旋转刷新图标；勿用裸 .is-loading，否则 el-button 的 loading 态整颗按钮也会转
        .el-icon.is-loading {
          animation: rotate 1s linear infinite;
        }
      }
    }
    
    .material-list {
      margin-top: 20px;
    }
    
    .empty-data {
      padding: 40px 0;
    }
  }
  
  .material-upload {
    width: 100%;
  }
  
  .preview-container {
    display: flex;
    justify-content: center;
    align-items: center;
    flex-direction: column;
    padding: 0 20px;
    
    .file-info {
      text-align: center;
      margin-top: 20px;
    }
  }
}

.upload-form {
  padding: 0 20px;
  
  .form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 5px;
  }
  
  .upload-demo {
    width: 100%;
  }
}

.dialog-footer {
  padding: 0 20px;
  display: flex;
  justify-content: flex-end;
}

.upload-file-list {
  width: 100%;
}

.upload-file-item {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  margin-bottom: 10px;
}

.upload-file-item .file-name {
  font-size: 14px;
  color: #606266;
  margin-bottom: 5px;
  display: block;
}

/* 覆盖Element Plus对话框样式 */
:deep(.el-dialog__body) {
  padding: 20px 0;
}

:deep(.el-dialog__header) {
  padding-left: 20px;
  padding-right: 20px;
  margin-right: 0;
}

:deep(.el-dialog__footer) {
  padding-top: 10px;
  padding-bottom: 15px;
}

/* 修改上传进度条样式 */
:deep(.el-progress__text) {
  color: #303133 !important; /* 深灰色字体，确保在各种背景上都可见 */
  font-size: 12px;
}

:deep(.el-progress--line) {
  margin-bottom: 10px;
}

.upload-file-item {
  border: 1px solid #dcdfe6;
  border-radius: 6px; /* 增加圆角 */
  padding: 12px; /* 增加内边距 */
  margin-bottom: 12px; /* 增加外边距 */
  background-color: #fafafa; /* 轻微背景色 */
  transition: box-shadow 0.3s; /* 添加过渡效果 */
}

.upload-file-item:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); /* 悬停效果 */
}

.upload-file-item .file-name {
  font-size: 14px;
  color: #303133; /* 深灰色字体 */
  margin-bottom: 8px; /* 增加底部间距 */
  display: block;
  font-weight: 500;
}
</style>
