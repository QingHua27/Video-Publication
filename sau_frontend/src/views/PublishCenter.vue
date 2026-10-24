<template>
  <div class="publish-center"><header class="publish-page-heading"><h1>发布中心</h1></header>
    <!-- Tab管理区域 -->
    <Teleport to="#publish-header-slot" :disabled="!publishHeaderReady">
      <div class="tab-management reference-tabs"><div class="tab-header"><div class="tab-list"><div v-for="tab in tabs" :key="tab.name" :class="['tab-item',{active:activeTab===tab.name}]" @click="activeTab=tab.name"><span>{{ tab.label }}</span><el-icon class="close-icon" @click.stop="closeReferenceTab(tab.name)"><Close/></el-icon></div></div><div class="tab-actions"><el-button size="small" @click="addTab"><el-icon><Plus/></el-icon>新建任务</el-button><el-button size="small" @click="openPublishHistory"><el-icon><Clock/></el-icon>发布记录</el-button><el-dropdown trigger="click" @command="handlePublishMenu"><el-button link aria-label="更多发布操作"><el-icon><MoreFilled/></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="jobs">任务记录</el-dropdown-item><el-dropdown-item command="preflight" :disabled="!preflightRows.length">最近预检结果</el-dropdown-item><el-dropdown-item command="batch" :disabled="batchPublishing">批量发布</el-dropdown-item><el-dropdown-item command="sidebar">展开 / 收起导航栏</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div></div></div>
    </Teleport>

    <!-- 内容区域 -->
    <div class="publish-content">
      <div class="tab-content-wrapper">
        <div
          v-for="tab in tabs"
          :key="tab.name"
          v-show="activeTab === tab.name"
          class="tab-content"
        ><div class="publish-grid" :class="{'has-task-status':floatingResults.length}"><div class="publish-main-column"><section v-if="!isArticleTab(tab)" class="editor-panel video-panel"><div class="panel-caption"><span>01</span> 视频素材</div><div v-if="!isArticleTab(tab)" class="upload-section">
            <h3>视频</h3>
            <div class="upload-options" v-if="!tab.fileList.length">
              <el-button type="primary" @click="showUploadOptions(tab)" class="upload-btn">
                <el-icon><Upload /></el-icon>
                上传视频
              </el-button>
            </div>

            <!-- 已上传文件列表 -->
            <div v-if="tab.fileList.length > 0" class="uploaded-files">

              <div class="file-list">
                <div v-for="(file, index) in tab.fileList" :key="index" class="file-item">
                  <video class="selected-video-preview" :src="file.url" :poster="tab.videoCovers.landscape?.previewUrl || tab.videoCovers.recommendation?.previewUrl" preload="metadata" controls playsinline @loadedmetadata="event=>setSelectedVideoMetadata(file,event)"></video><div class="video-file-details"><el-link :href="file.url" target="_blank" type="primary">{{ file.name }}</el-link>
                  <span class="file-size">{{ (file.size / 1024 / 1024).toFixed(2) }}MB<span v-if="file.videoWidth"> · {{ file.videoWidth }}×{{ file.videoHeight }}</span><span v-if="file.videoDuration"> · {{ videoDurationLabel(file.videoDuration) }}</span></span></div>
                  <div class="material-publication-marks video-platform-statuses"><el-tooltip v-for="record in libraryPublicationMarks({file_path:file.path,episode_number:file.episode_number,section_id:tab.episodeSectionId})" :key="record.id" :content="`${platformNames[record.platform]} · ${publicationLabels[record.status]}`" placement="top"><span class="video-platform-status" :class="{'is-confirmed':record.status==='published'}"><span class="botanical-status-icon" :style="{background:platformColors[record.platform]}"><img v-if="platformIconPaths[record.platform]" :src="platformIconPaths[record.platform]" alt=""/></span>{{ platformNames[record.platform] }}<el-icon><CircleCheckFilled v-if="record.status==='published'"/><Clock v-else/></el-icon></span></el-tooltip><span v-if="!libraryPublicationMarks({file_path:file.path,episode_number:file.episode_number,section_id:tab.episodeSectionId}).length" class="video-material-ready"><el-icon><CircleCheckFilled/></el-icon> 素材已就绪</span></div>
                  <div class="video-item-actions"><el-button @click="showUploadOptions(tab)"><el-icon><RefreshRight/></el-icon>替换</el-button><el-button aria-label="载入素材库下一集" class="next-episode-action" :loading="nextEpisodeLoading===tab.name" @click="loadNextEpisode(tab)"><el-icon><DArrowRight/></el-icon>下一集</el-button><el-dropdown trigger="click" @command="command=>command==='library' ? openLibraryForTab(tab) : removeFile(tab,index)"><el-button aria-label="更多视频操作"><el-icon><MoreFilled/></el-icon></el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="library"><el-icon><Folder/></el-icon>素材库</el-dropdown-item><el-dropdown-item command="delete" divided><el-icon><Delete/></el-icon>删除视频</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div>
                </div>
              </div>
            </div>
          </div></section><section class="editor-panel basic-panel"><div class="panel-caption"><span>02</span> 基本信息</div><div class="title-section">
            <h3>标题<span v-if="tab.selectedPlatform === 1 || tab.selectedPlatform === 2 || tab.selectedPlatform === 3 || tab.selectedPlatform === 4" class="optional-hint">（选填）</span><span v-else-if="tab.selectedPlatform === 8" class="optional-hint">（必填，5-72字）</span><span v-else-if="tab.selectedPlatform === 9" class="optional-hint">（必填，最多100字）</span><span v-else-if="tab.selectedPlatform === 5 && tab.contentType === 'article'" class="optional-hint">（必填，2-64字）</span><span v-else-if="tab.selectedPlatform === 7 && tab.contentType === 'article'" class="optional-hint">（必填，最多30字）</span></h3>
            <el-input
              v-model="tab.title"
              type="textarea"
              :rows="1"
              :placeholder="(tab.selectedPlatform === 1 || tab.selectedPlatform === 2 || tab.selectedPlatform === 3 || tab.selectedPlatform === 4) ? '请输入标题（可不填）' : (tab.selectedPlatform === 8 ? '请输入标题（5-72字）' : (tab.selectedPlatform === 9 ? '请输入标题（最多100字）' : '请输入标题'))"
              :maxlength="tab.selectedPlatform === 7 && tab.contentType === 'article' ? 30 : (tab.selectedPlatform === 8 ? 72 : (tab.selectedPlatform === 9 ? 100 : 100))"
              show-word-limit
              class="title-input"
            />
          </div><div v-if="isArticleTab(tab)" class="article-body-section">
            <h3>正文<span class="optional-hint">（必填，纯文本，换行保留）</span></h3>
            <el-input
              v-model="tab.articleBody"
              type="textarea"
              :rows="12"
              placeholder="请输入文章正文"
              maxlength="20000"
              show-word-limit
              class="article-body-input"
            />
          </div><div class="topic-section">
            <h3>
              话题标签
              <span class="optional-hint">{{ getTopicCountHint(tab.selectedPlatform) }}</span>
            </h3>
            <div class="topic-display">
              <div class="selected-topics">
                <el-tag
                  v-for="(topic, index) in tab.selectedTopics"
                  :key="index"
                  closable
                  @close="removeTopic(tab, index)"
                  class="topic-tag"
                >
                  #{{ topic }}
                </el-tag>
              </div>
              <div class="topic-actions">
                <el-button
                  type="success"
                  plain
                  @click="randomPickTopics(tab)"
                  class="select-topic-btn"
                >
                  <el-icon><Box/></el-icon>随机抽取
                </el-button>
                <el-button
                  type="primary"
                  plain
                  aria-label="添加话题"
                  @click="openTopicDialog(tab)"
                  class="select-topic-btn"
                >
                  <el-icon><Plus/></el-icon>添加
                </el-button>
              </div>
            </div>
          </div></section><section class="editor-panel covers-panel"><div class="panel-caption"><span>03</span><el-icon class="botanical-heading-icon"><Picture/></el-icon> 封面设置<span class="reference-caption-note">一次选择，按平台自动分配。</span></div><div v-if="!isArticleTab(tab)" class="video-cover-section">
            <h3>视频封面（全平台共用）</h3>
            <div class="optional-hint">横版16:9、竖版及B站推荐页4:3封面各选一次，按平台封面入口分配，不用逐个平台重复选。未选择对应方向时保留平台默认封面，不用另一方向补位。</div>
            <div class="video-cover-grid">
              <div v-for="kind in ['landscape', 'portrait', 'recommendation']" :key="kind" class="video-cover-card">
                <strong>{{ kind === 'recommendation' ? '推荐页 4:3' : kind === 'landscape' ? '横版 16:9' : '竖版 3:4' }}</strong>
                <div class="optional-hint">{{ kind === 'recommendation' ? 'B站推荐页' : kind === 'landscape' ? 'B站个人空间 · 抖音' : '视频号 · 小红书 · 快手' }}</div>
                <el-upload :class="['video-cover-upload',kind]" :show-file-list="false" accept="image/jpeg,image/png,image/webp,image/bmp,.jpg,.jpeg,.png,.webp,.bmp"
                  :action="`${apiBaseUrl}/upload`" :headers="authHeaders"
                  :before-upload="beforeVideoCoverUpload"
                  :on-success="(response, file) => handleVideoCoverSuccess(response, file, tab, kind)" :on-error="handleCoverUploadError">
                  <img v-if="tab.videoCovers[kind]" :src="tab.videoCovers[kind].previewUrl" :alt="kind === 'landscape' ? '横版封面预览' : '竖版封面预览'" />
                  <span v-else>＋ 选择{{ kind === 'recommendation' ? 'B站4:3' : kind === 'landscape' ? '横版' : '竖版' }}封面</span>
                </el-upload>
                <div v-if="tab.videoCovers[kind]" class="cover-file-name"><span class="cover-file-label" :title="tab.videoCovers[kind].name"><span class="cover-ready-check">✓</span>{{ tab.videoCovers[kind].name }}</span><span class="cover-file-actions"><el-button link @click="pickCoverReplacement">更换</el-button><el-button link type="danger" @click="delete tab.videoCovers[kind]">移除</el-button></span></div>
              </div>
            </div>
            <div class="optional-hint">支持 JPG、PNG、WebP、BMP，不额外限制 2MB 或图片方向；裁切及实际限制以平台为准。</div>
            <div v-if="episodeSourceLabel(tab)" class="reference-import-source">已从「{{ episodeSourceLabel(tab) }}」带入视频和{{ Object.keys(tab.videoCovers).length }}张封面</div>
          </div><div v-if="isArticleTab(tab)" class="article-cover-section">
            <h3>
              展示封面
              <span v-if="tab.selectedPlatform === 5" class="optional-hint">（必填，单图；JPEG/PNG，最大 5MB）</span>
              <span v-else-if="tab.selectedPlatform === 8" class="optional-hint">（选填；尺寸大于 450×300，jpg/jpeg/png，最大 10MB）</span>
              <span v-else-if="tab.selectedPlatform === 9" class="optional-hint">（选填，单图；JPEG/PNG，最大 10MB）</span>
              <span v-else class="optional-hint">（选填，单图；JPEG/PNG，最大 20MB）</span>
            </h3>
            <el-radio-group v-model="tab.coverMode" class="cover-mode-radios">
              <el-radio label="single">{{ tab.selectedPlatform === 8 ? '上传封面' : '单图' }}</el-radio>
              <el-radio v-if="tab.selectedPlatform !== 5" label="none">无封面</el-radio>
            </el-radio-group>

            <!-- 搜狐：封面（后台弹窗最多 1 张） -->
            <div v-if="tab.coverMode === 'single' && tab.selectedPlatform === 8" class="article-cover-upload-wrap sohu-multi-cover">
              <div class="sohu-cover-list">
                <div
                  v-for="(img, idx) in tab.coverImages"
                  :key="img.path || idx"
                  class="cover-preview-box sohu-cover-item"
                >
                  <img :src="img.previewUrl" alt="封面预览" class="cover-preview-img" />
                  <div class="cover-preview-mask">
                    <span @click.stop="removeSohuCover(tab, idx)">删除</span>
                  </div>
                </div>
                <el-upload
                  v-if="!(tab.coverImages && tab.coverImages.length)"
                  class="article-cover-upload"
                  :show-file-list="false"
                  :auto-upload="true"
                  accept="image/jpeg,image/jpg,image/png,.jpg,.jpeg,.png"
                  :action="`${apiBaseUrl}/upload`"
                  :headers="authHeaders"
                  :before-upload="(file) => beforeCoverUpload(file, tab)"
                  :on-success="(response, file) => handleSohuCoverUploadSuccess(response, file, tab)"
                  :on-error="handleCoverUploadError"
                >
                  <div class="cover-plus-box">
                    <el-icon :size="28"><Plus /></el-icon>
                  </div>
                </el-upload>
              </div>
              <div class="cover-tip">封面图片尺寸应大于 450×300，最大 10M，格式限制：jpg、jpeg、png</div>
            </div>

            <!-- 其它平台：单图封面 -->
            <div v-else-if="tab.coverMode === 'single'" class="article-cover-upload-wrap">
              <el-upload
                class="article-cover-upload"
                :show-file-list="false"
                :auto-upload="true"
                accept="image/jpeg,image/jpg,image/png,.jpg,.jpeg,.png"
                :action="`${apiBaseUrl}/upload`"
                :headers="authHeaders"
                :before-upload="(file) => beforeCoverUpload(file, tab)"
                :on-success="(response, file) => handleCoverUploadSuccess(response, file, tab)"
                :on-error="handleCoverUploadError"
              >
                <div v-if="tab.coverPreviewUrl" class="cover-preview-box">
                  <img :src="tab.coverPreviewUrl" alt="封面预览" class="cover-preview-img" />
                  <div class="cover-preview-mask">
                    <span>更换封面</span>
                  </div>
                </div>
                <div v-else class="cover-plus-box">
                  <el-icon :size="28"><Plus /></el-icon>
                </div>
              </el-upload>
              <div class="cover-side-actions">
                <el-button
                  v-if="tab.coverPreviewUrl"
                  type="primary"
                  link
                  @click="previewArticleCover(tab)"
                >
                  预览
                </el-button>
                <el-button
                  v-if="tab.coverImage"
                  type="danger"
                  link
                  @click="clearArticleCover(tab)"
                >
                  删除
                </el-button>
              </div>
              <div class="cover-tip">{{ tab.selectedPlatform === 5 ? '优质的封面有利于推荐，格式支持 JPEG、PNG，单张最大 5MB' : (tab.selectedPlatform === 9 ? '优质的封面有利于推荐，格式支持 JPEG、PNG，单张最大 10MB' : '优质的封面有利于推荐，格式支持 JPEG、PNG，单张最大 20MB') }}</div>
              <div v-if="tab.coverFileName" class="cover-file-name">{{ tab.coverFileName }}</div>
            </div>
          </div></section><section class="editor-panel schedule-panel" :class="{'is-scheduled':tab.scheduleEnabled}"><div class="panel-caption"><span>04</span><el-icon class="botanical-heading-icon"><Setting/></el-icon> 发布设置</div><div class="schedule-section">
            <h3>发布时间</h3>
            <div class="schedule-controls">
              <el-select v-model="tab.scheduleEnabled" class="reference-publish-time" aria-label="发布时间"><el-option label="立即发布" :value="false"/><el-option label="定时发布" :value="true"/></el-select><el-checkbox v-if="[1,2,3,4,6].includes(tab.selectedPlatform)" class="reference-ai-toggle" :model-value="referenceAiEnabled(tab)" @change="value=>setReferenceAi(tab,value)" title="仅修改当前平台的AI创作声明">{{ referenceAiEnabled(tab) ? '已启用 AI 创作声明' : 'AI 创作声明' }}</el-checkbox>
              <div v-if="tab.scheduleEnabled" class="schedule-settings">
                <div class="schedule-item">
                  <span class="label">每天发布视频数：</span>
                  <el-select v-model="tab.videosPerDay" placeholder="选择发布数量">
                    <el-option
                      v-for="num in 55"
                      :key="num"
                      :label="num"
                      :value="num"
                    />
                  </el-select>
                </div>
                <div class="schedule-item">
                  <span class="label">每天发布时间：</span>
                  <el-time-select
                    v-for="(time, index) in tab.dailyTimes"
                    :key="index"
                    v-model="tab.dailyTimes[index]"
                    start="00:00"
                    step="00:30"
                    end="23:30"
                    placeholder="选择时间"
                  />
                  <el-button
                    v-if="tab.dailyTimes.length < tab.videosPerDay"
                    type="primary"
                    size="small"
                    @click="tab.dailyTimes.push('10:00')"
                  >
                    添加时间
                  </el-button>
                </div>
                <div class="schedule-item">
                  <span class="label">开始天数：</span>
                  <el-select v-model="tab.startDays" placeholder="选择开始天数">
                    <el-option :label="'明天'" :value="0" />
                    <el-option :label="'后天'" :value="1" />
                  </el-select>
                </div>
              </div>
            </div>
          </div></section></div><aside class="publish-settings-column"><div class="account-section">
            <div class="accounts-panel-heading"><h3>发布到 <span class="section-count">已选{{ tab.selectedAccounts.length }}个账号</span></h3><el-checkbox :model-value="allPickerAccountsSelected(tab)" @change="checked=>toggleAllPublishAccounts(tab,checked)">全选</el-checkbox></div>
            <div class="account-platform-grid icon-account-grid"><template v-for="platform in accountPlatformGroups" :key="platform.key"><el-tooltip v-for="account in platform.accounts" :key="account.id" :content="`${platform.name} · ${account.name}`" placement="top" :show-after="150"><div class="account-platform-card icon-account-card" :data-platform="platform.key" :class="{'is-selected':tab.selectedAccounts.includes(account.id)}">
              <el-checkbox :model-value="tab.selectedAccounts.includes(account.id)" :aria-label="`${platform.name} · ${account.name}`" @change="checked=>togglePublishAccount(tab,account.id,checked)"><span class="platform-badge" :style="{background:platformColors[platform.key]}" aria-hidden="true"><img v-if="platformIconPaths[platform.key]" :src="platformIconPaths[platform.key]" alt=""/><span v-else>{{ platform.name.slice(0,1) }}</span></span><span class="botanical-account-details"><strong>{{ platform.name }}</strong><small>{{ account.name }}</small></span></el-checkbox>
            </div></el-tooltip></template></div>
          </div><section class="editor-panel platform-options-panel"><div class="platform-section">
            <h3>平台专属设置</h3>
            <details class="platform-range"><summary>调整平台范围</summary><el-checkbox-group v-model="tab.selectedPlatforms" class="platform-radios" @change="() => onPlatformsChange(tab)">
              <el-checkbox
                v-for="platform in platforms"
                :key="platform.key"
                :value="platform.key"
                class="platform-radio"
              >
                {{ platform.name }}
              </el-checkbox>
            </el-checkbox-group></details>
            <div class="optional-hint">可多选；每个平台至少选择一个账号。标题和视频共用，平台选项分别保存。</div>
            <div v-if="tab.selectedPlatforms.length" style="margin-top: 12px">
              <div class="optional-hint">切换下方标签，分别设置各平台选项</div>
              <el-radio-group :model-value="tab.selectedPlatform" @change="value => switchPlatformSettings(tab, value)" class="platform-settings-tabs">
                <el-radio-button v-for="key in tab.selectedPlatforms" :key="key" :value="key" :data-platform="key" :aria-label="`${platformNames[key]}设置`" :title="platformNames[key]"><span class="settings-platform-icon" :style="{background:platformColors[key]}"><img v-if="platformIconPaths[key]" :src="platformIconPaths[key]" :alt="platformNames[key]"/><span v-else>{{ platformNames[key].slice(0,1) }}</span></span><span class="settings-platform-label">{{ platformNames[key] }}</span></el-radio-button>
              </el-radio-group>
            </div>
          </div><div v-if="tab.selectedPlatform===1" class="xhs-manual-setting"><el-checkbox v-model="tab.xhsManual" @change="()=>onXhsManualChange(tab)">小红书半自动发布</el-checkbox><p class="optional-hint">开启后仅整理素材和文案，由你在官方页面上传发布，再手动标记完成。其他平台照常提交。</p></div><div v-if="tab.selectedPlatform===6" class="bilibili-category-section"><h3>分区</h3><el-select v-model="tab.bilibiliCategory" aria-label="B站分区"><el-option label="日常" :value="21"/></el-select></div><div v-if="!manualXhsEnabled(tab,tab.selectedPlatform) && tab.selectedAccounts.some(id => getAccountPlatformName(id) === platformNames[tab.selectedPlatform])" class="account-section reference-collection" :class="{'multiple-collection-accounts':tab.selectedAccounts.filter(id=>getAccountPlatformName(id)===platformNames[tab.selectedPlatform]).length>1}">
            <h3>加入合集</h3>
            <p class="optional-hint">自动读取各账号已创建的合集，直接选择名称；不选择则不加入合集。B站 ID 由系统自动处理。</p>
            <div v-for="accountId in tab.selectedAccounts.filter(id => getAccountPlatformName(id) === platformNames[tab.selectedPlatform])" :key="accountId" class="collection-account-row">
              <span class="collection-account-name">{{ getAccountPlatformName(accountId) }} · {{ getAccountDisplayName(accountId) }}</span>
              <div class="collection-account-control">
                <div style="display:flex;gap:8px">
                  <el-select v-model="tab.collections[accountId]" :aria-label="`${getAccountPlatformName(accountId)} · ${getAccountDisplayName(accountId)}合集`" placeholder="不加入合集" clearable filterable :loading="tab.collectionCatalogs[accountId]?.loading" :disabled="tab.collectionCatalogs[accountId]?.loading" @change="() => acknowledgeCollection(tab, accountId)" style="flex:1">
                    <el-option label="不加入合集" value="" />
                    <el-option v-for="option in tab.collectionCatalogs[accountId]?.items || []" :key="option.id" :value="option.value" :label="option.displayName || (option.disabled ? `${option.name}（同名合集，无法自动区分）` : option.name)" :title="option.unavailableReason || option.name" :disabled="option.disabled" />
                  </el-select>
                  <el-button :loading="tab.collectionCatalogs[accountId]?.loading" @click="loadAccountCollections(tab, accountId, true)">刷新</el-button>
                </div>
                <div class="optional-hint" role="status">{{ tab.collectionCatalogs[accountId]?.loading ? '正在读取该账号的合集…' : tab.collectionCatalogs[accountId]?.message || '等待加载' }}</div>
                <el-button v-if="tab.collectionCatalogs[accountId]?.selectionInvalid" link type="warning" @click="tab.collections[accountId] = ''; acknowledgeCollection(tab, accountId)">确认不加入合集</el-button>
              </div>
            </div>
          </div><div v-if="articleCapablePlatforms.includes(tab.selectedPlatform)" class="content-type-section">
            <h3>内容类型</h3>
            <el-radio-group v-model="tab.contentType" class="content-type-radios" @change="() => onContentTypeChange(tab)">
              <el-radio v-if="!articleOnlyPlatforms.includes(tab.selectedPlatform)" label="video">视频</el-radio>
              <el-radio label="article">图文文章</el-radio>
            </el-radio-group>
            <div v-if="tab.selectedPlatform === 8" class="optional-hint">搜狐号第一期仅支持图文文章（mp.sohu.com）</div>
            <div v-else-if="tab.selectedPlatform === 9" class="optional-hint">知乎第一期仅支持文章（zhuanlan.zhihu.com/write）</div>
            <div v-else-if="tab.selectedPlatform === 7" class="optional-hint">文章走创作者后台「发文章」，不做微头条</div>
            <div v-else class="optional-hint">文章走百家号后台「图文」，标题需 2-64 字</div>
          </div>
<div v-if="tab.selectedPlatform === 7 && tab.contentType === 'article'" class="work-statement-section">
            <h3>
              作品声明
              <span class="optional-hint">（选填，单选）</span>
            </h3>
            <el-radio-group v-model="tab.workStatement" class="work-statement-group">
              <el-radio label="">不声明</el-radio>
              <el-radio
                v-for="opt in toutiaoWorkStatementOptions"
                :key="opt"
                :label="opt"
              >
                {{ opt }}
              </el-radio>
            </el-radio-group>
          </div>
<div v-if="tab.selectedPlatform === 8" class="work-statement-section">
            <h3>
              信息来源
              <span class="optional-hint">（单选，默认无特别声明）</span>
            </h3>
            <el-radio-group v-model="tab.workStatement" class="work-statement-group">
              <el-radio
                v-for="opt in sohuInfoSourceOptions"
                :key="opt"
                :label="opt"
              >
                {{ opt }}
              </el-radio>
            </el-radio-group>
          </div>
<div v-if="tab.selectedPlatform === 9" class="work-statement-section">
            <h3>
              创作声明
              <span class="optional-hint">（下拉单选，默认无声明）</span>
            </h3>
            <el-select
              v-model="tab.workStatement"
              placeholder="选择创作声明"
              class="bilibili-creation-select"
            >
              <el-option
                v-for="opt in zhihuCreationStatementOptions"
                :key="opt"
                :label="opt"
                :value="opt"
              />
            </el-select>
          </div>
<div v-if="tab.selectedPlatform === 2" class="original-section">
            <el-checkbox
              v-model="tab.isOriginal"
              label="声明原创"
              class="original-checkbox"
            />
          </div>
<div v-if="tab.selectedPlatform === 2" class="draft-section">
            <el-checkbox
              v-model="tab.isDraft"
              label="视频号仅保存草稿(用手机发布)"
              class="draft-checkbox"
            />
          </div>
<div v-if="tab.selectedPlatform === 1 || tab.selectedPlatform === 2 || tab.selectedPlatform === 3 || tab.selectedPlatform === 4" class="ai-declaration-section">
            <el-checkbox
              v-model="tab.aiGenerated"
              :label="tab.selectedPlatform === 2 ? '视频标注：含AI生成内容' : tab.selectedPlatform === 4 ? '作者声明：内容为AI生成' : tab.selectedPlatform === 1 ? '内容类型声明：笔记含AI合成内容' : '自主声明：内容由AI生成'"
              class="ai-declaration-checkbox"
            />
          </div>
<div v-if="tab.selectedPlatform === 6" class="bilibili-creation-section">
            <h3>创作声明</h3>
            <el-select
              v-model="tab.bilibiliCreationStatement"
              placeholder="选择创作声明"
              clearable
              class="bilibili-creation-select"
            >
              <el-option
                v-for="opt in bilibiliCreationOptions"
                :key="String(opt.value)"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <div class="optional-hint">对应 B 站投稿页「创作声明」；通过 biliup 的 --extra-fields 提交</div>
          </div>
<details v-if="tab.selectedPlatform!==6" class="publication-more"><summary>更多设置</summary><div class="dry-run-section">
            <el-checkbox
              v-model="tab.dryRun"
              label="仅预览不发布（填完表后停住，方便核对）"
              class="dry-run-checkbox"
            />
          </div>
<details v-if="tab.selectedPlatform === 3" class="product-more"><summary>更多设置 · 商品链接</summary><div class="product-section">
            <h3>商品链接</h3>
            <el-input
              v-model="tab.productTitle"
              type="text"
              :rows="1"
              placeholder="请输入商品名称"
              maxlength="200"
              class="product-name-input"
            />
            <el-input
              v-model="tab.productLink"
              type="text"
              :rows="1"
              placeholder="请输入商品链接"
              maxlength="200"
              class="product-link-input"
            />
          </div></details></details></section><section class="editor-panel compact-task-panel"><div class="compact-task-heading"><strong>发布任务状态</strong><span class="reference-task-counts">{{ taskSummary.completed }}完成 · {{ taskSummary.running }}进行中 · {{ taskSummary.confirmation }}待确认</span><el-button v-if="floatingResults.length" link @click="statusCollapsed=!statusCollapsed">详情</el-button></div><el-progress :percentage="finishedTaskPercent" :stroke-width="5" color="#191919"/><div v-for="item in visibleTaskStatuses(floatingResults).slice(0,2)" :key="`${item.tabName}-${item.accountId}`" class="compact-task-row"><strong :title="item.materialLabel || describeTaskMaterial(item.submissionPayload)">{{ item.label }} · {{ item.materialLabel || describeTaskMaterial(item.submissionPayload) }}</strong><span :class="`task-text-${item.status}`" :title="taskStatusMessage(item)">{{ taskStatusMessage(item) }}</span><el-button v-if="item.collectionTask?.status==='failed'" link @click="retryCollection(item)">重试加入合集</el-button><el-progress class="reference-mini-progress" :percentage="item.progress || 0" :show-text="false" :stroke-width="4" :color="taskStateColors[item.status] || '#3478e5'"/><small>{{ item.progress || 0 }}%</small><el-button v-if="item.status==='failed' && item.submissionPayload" link @click="retryFailedUpload(item)">重试</el-button><el-button v-else-if="item.manualXhs && item.status==='awaiting_confirmation'" link @click="statusCollapsed=false">处理人工发布</el-button><el-button v-else-if="item.status==='awaiting_confirmation'" link @click="continueRepeatUpload(item)">继续上传</el-button></div><div v-if="!floatingResults.length" class="reference-task-empty">尚无发布任务，提交后在此查看进度</div></section></aside></div><div class="action-buttons"><button class="task-dock-summary" :class="{'no-tasks':!floatingResults.length}" :disabled="!floatingResults.length" @click="statusCollapsed=!statusCollapsed" :aria-expanded="!statusCollapsed"><el-progress type="circle" :percentage="finishedTaskPercent" :width="30" :stroke-width="4" :show-text="false" color="#171b23"/><span v-if="floatingResults.length"><strong>发布任务状态</strong></span><span v-if="floatingResults.length" class="dock-percent">{{ finishedTaskPercent }}%</span><el-icon v-if="floatingResults.length"><ArrowUp v-if="statusCollapsed"/><ArrowDown v-else/></el-icon></button><div v-if="floatingResults.length" class="dock-task-counts"><span>{{ taskSummary.completed }}完成</span> · <span :class="{'has-failures':taskSummary.failed}">{{ taskSummary.failed }}失败</span> · <span>{{ taskSummary.running }}发布中</span><span v-if="taskSummary.queued"> · {{ taskSummary.queued }}排队</span><span v-if="taskSummary.confirmation"> · {{ taskSummary.confirmation }}待确认</span></div><div v-if="tab.publishStatus" class="publish-submit-notice" :class="`notice-${tab.publishStatus.type}`" role="status" :title="tab.publishStatus.message">{{ tab.publishStatus.message }}</div><div v-else class="publish-summary"><strong :class="{'configuration-ready':publishConfigurationReady(tab)}">{{ publishConfigurationReady(tab) ? '✓ 发布配置完整' : '完善发布配置' }}</strong><span>{{ tab.selectedAccounts.length }}个账号 · {{ tab.fileList.length }}个视频 · {{ Object.keys(tab.videoCovers).length }}张封面</span></div>
            <span v-if="tab.automationMessage" class="automation-message" role="status">{{ tab.automationMessage }}</span>
            <el-button v-if="tab.automationActive" size="small" type="danger" plain @click="stopAutomation(tab)">停止自动化</el-button>
            <el-checkbox v-else v-model="tab.autoPublish" :disabled="tab.publishing || isArticleTab(tab)">自动连续发布</el-checkbox>
            <el-button size="small" @click="stopAutomation(tab);cancelPublish(tab)">取消</el-button>
            <el-button
              size="small"
              type="primary"
              @click="confirmPublish(tab).catch(error => ElMessage.warning(error.message))"
              class="publish-submit"
              :loading="publishBusyState(tab).loading"
              :disabled="publishBusyState(tab).disabled"
            >
              <el-icon v-if="!publishBusyState(tab).disabled"><Promotion/></el-icon>{{ publishBusyState(tab).disabled ? publishBusyState(tab).label : `提交发布（${tab.selectedAccounts.length}）` }}
            </el-button>
          </div><el-dialog
            v-model="uploadOptionsVisible"
            title="选择上传方式"
            width="640px"
            class="upload-options-dialog"
          >
            <div class="upload-options-content">
              <button type="button" aria-label="本地上传" @click="selectLocalUpload" class="upload-method-card"><el-icon class="upload-method-icon"><Upload /></el-icon><strong>本地上传</strong><span>从电脑选择视频文件</span><small>支持多个视频</small></button>
              <button type="button" aria-label="素材库" @click="selectMaterialLibrary" class="upload-method-card"><el-icon class="upload-method-icon library-method-icon"><Folder /></el-icon><strong>素材库</strong><span>按分区和集数选择素材</span><small>自动带入视频与三种封面</small></button>
            </div>
          </el-dialog>
<el-dialog
            v-model="localUploadVisible"
            title="本地上传"
            width="600px"
            class="local-upload-dialog"
          >
            <el-upload
              class="video-upload"
              drag
              :auto-upload="true"
              :action="`${apiBaseUrl}/upload`"
              :on-success="(response, file) => handleUploadSuccess(response, file, currentUploadTab)"
              :on-error="handleUploadError"
              multiple
              accept="video/*"
              :headers="authHeaders"
            >
              <el-icon class="el-icon--upload"><Upload /></el-icon>
              <div class="el-upload__text">
                将视频文件拖到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持MP4、AVI等视频格式，可上传多个文件
                </div>
              </template>
            </el-upload>
          </el-dialog>
<el-dialog
            v-model="batchPublishDialogVisible"
            title="批量提交进度"
            width="500px"
            :close-on-click-modal="false"
            :close-on-press-escape="false"
            :show-close="false"
          >
            <div class="publish-progress">
              <el-progress
                :percentage="publishProgress"
                :status="publishProgress === 100 ? 'success' : ''"
              />
              <div v-if="currentPublishingTab" class="current-publishing">
                正在提交：{{ currentPublishingTab.label }}
              </div>

              <!-- 发布结果列表 -->
              <div class="publish-results" v-if="publishResults.length > 0">
                <div
                  v-for="(result, index) in publishResults"
                  :key="index"
                  :class="['result-item', result.status]"
                >
                  <el-icon v-if="result.status === 'success'"><Check /></el-icon>
                  <el-icon v-else-if="result.status === 'error'"><Close /></el-icon>
                  <el-icon v-else><InfoFilled /></el-icon>
                  <span class="label">{{ result.label }}</span>
                  <span class="message">{{ result.message }}</span>
                </div>
              </div>
            </div>

            <template #footer>
              <div class="dialog-footer">
                <el-button
                  @click="cancelBatchPublish"
                  :disabled="publishProgress === 100"
                >
                  取消发布
                </el-button>
                <el-button
                  type="primary"
                  @click="batchPublishDialogVisible = false"
                  v-if="publishProgress === 100"
                >
                  关闭
                </el-button>
              </div>
            </template>
          </el-dialog>
<el-dialog
            v-if="activeTab === tab.name"
            v-model="materialLibraryVisible"
            title="选择素材"
            width="1240px"
            class="material-library-dialog episode-picker-dialog"
          >
            <div class="episode-picker">
              <aside class="picker-sections">
                <el-input v-model="librarySectionSearch" placeholder="搜索分区" clearable aria-label="搜索素材分区" />
                <div class="picker-section-heading"><strong>剧集分区</strong><el-button link @click="createPickerSection">＋ 新建</el-button></div>
                <button v-for="section in pickerSections" :key="section.id" type="button" class="picker-section-button" :class="{active:librarySectionId===section.id}" :aria-pressed="librarySectionId===section.id" @click="selectPickerSection(section.id)"><span class="picker-folder-symbol">▰</span><strong>{{ section.name }}</strong><small>{{ section.count }}个素材</small></button>
                <p class="picker-sidebar-note">按分区整理，避免同名集数混淆。</p>
              </aside>
              <div class="picker-main">
                <header class="picker-main-heading"><div><strong>{{ pickerSectionName }}</strong><span>{{ libraryFolders.length }}个文件夹</span></div><el-input v-model="librarySearch" placeholder="搜索集数或文件名" clearable aria-label="搜索集数或文件名" /></header>
                <div class="picker-toolbar"><div class="picker-filter-tabs"><button v-for="filter in pickerFilters" :key="filter.value" type="button" :class="{active:libraryFilter===filter.value}" @click="libraryFilter=filter.value">{{ filter.label }}</button></div><el-checkbox v-model="libraryOnlyUnfinished">仅查看未完成</el-checkbox><el-button size="small" :loading="bilibiliHistoryBusy" @click="syncBilibiliHistory(true)">同步B站已发布</el-button></div>
                <div class="picker-grid-scroll" v-if="!libraryManualMode">
                  <div class="episode-picker-grid">
                    <button v-for="folder in filteredLibraryFolders" :key="folder.name" type="button" class="episode-picker-folder" :class="{selected:libraryFolder===folder.name}" :aria-label="`选择${folder.name}`" :aria-pressed="libraryFolder===folder.name" @click="selectEpisodeFolder(folder)">
                      <span class="folder-check">{{ libraryFolder===folder.name ? '✓' : '' }}</span>
                      <span class="episode-folder-art"><img v-if="folder.preview" :src="materialApi.getMaterialPreviewUrl(folder.preview)" :alt="`${folder.name}封面`" loading="lazy"/><span v-else class="folder-empty-art">暂无封面</span></span>
                      <strong class="episode-folder-title">{{ folder.name }}<small v-if="folder.videos.length>1">{{ folder.videos.length }}视频版本</small></strong>
                      <span class="episode-folder-meta">{{ folder.videos.length }}视频 · {{ folder.coverCount }}封面</span><span v-if="folder.files.some(file=>file.available===false)" class="folder-path-warning">{{ folder.files.filter(file=>file.available===false).length }}个文件路径失效，请检查素材目录</span>
                      <span class="episode-folder-publications"><el-tag v-for="record in folder.publications" :key="record.id" size="small" :type="record.status==='published' ? 'success' : record.status==='submitted' ? 'primary' : 'warning'" :title="historyAccountLabel(record)">{{ platformNames[record.platform] }} · {{ publicationLabels[record.status] }}</el-tag><span v-if="!folder.publications.length" class="folder-unpublished">暂无发布记录</span></span>
                      <span class="episode-folder-ratios"><span v-for="kind in pickerCoverKinds" :key="kind" :class="{ready:folder.covers[kind].length}">{{ pickerCoverLabels[kind] }} {{ folder.covers[kind].length ? '✓' : '—' }}</span></span>
                    </button>
                  </div>
                  <el-empty v-if="!filteredLibraryFolders.length" description="暂无匹配素材，请切换分区或搜索条件" :image-size="52" />
                </div>
                <div v-else class="picker-manual-files"><p>手动多选视频；按集导入请返回文件夹视图。</p><el-checkbox-group v-model="selectedMaterials"><div v-for="material in manualLibraryVideos" :key="material.id" class="material-item" :class="{'material-has-history':libraryPublicationMarks(material).length}"><el-checkbox :value="material.id"><div class="material-info"><strong>{{ material.filename }}</strong><div class="material-publication-marks"><el-tag v-for="record in libraryPublicationMarks(material)" :key="record.id" size="small" :type="record.status==='published' ? 'success' : 'info'">{{ platformNames[record.platform] }} · {{ publicationLabels[record.status] }}</el-tag></div><small>{{ material.filesize }}MB · {{ material.upload_time }}</small></div></el-checkbox></div></el-checkbox-group></div>
                <div v-if="!libraryManualMode && pickerSelectedFolder && pickerNeedsVersion" class="picker-version-panel"><small>默认选择最高分辨率正片，排除片头、试听、手机版预览；可手动更换。</small>
                  <div v-if="libraryVideos.length && (libraryVideos.length>1 || !selectedMaterials.length)" class="library-cover-choice"><span>视频版本</span><el-select :model-value="selectedMaterials[0]" @change="value=>selectedMaterials=[value]" placeholder="请选择要发布的视频" aria-label="本集视频版本"><el-option v-for="video in libraryVideos" :key="video.id" :value="video.id" :label="video.filename"/></el-select></div>
                  <div v-for="kind in pickerCoverKinds.filter(kind=>libraryCoverOptions(kind).length>1)" :key="kind" class="library-cover-choice"><span>{{ pickerCoverLabels[kind] }}封面</span><el-select v-model="libraryCoverIds[kind]" :aria-label="`${pickerCoverLabels[kind]}封面版本`" placeholder="请选择封面版本"><el-option label="不使用此方向封面" value="-"/><el-option v-for="cover in libraryCoverOptions(kind)" :key="cover.id" :value="cover.id" :label="cover.filename"/></el-select></div>
                </div>
                <footer class="picker-pagination"><el-button link @click="toggleManualLibrary">{{ libraryManualMode ? '返回文件夹视图' : '全部视频（手动多选）' }}</el-button><span>{{ filteredLibraryFolders.length }}个文件夹 · 滚动查看全部</span></footer>
              </div>
            </div>
            <template #footer><div class="picker-footer"><div class="picker-selection-summary"><strong>{{ libraryManualMode ? `已选${selectedMaterials.length}个视频` : pickerSelectedFolder ? `已选：${pickerSectionName} / ${libraryFolder}` : '请选择本集文件夹' }}</strong><small>{{ !libraryManualMode && pickerSelectedFolder ? `将导入1个视频和${pickerSelectedFolder.coverCount}张候选封面，缺少的方向会清空` : '按集带入视频及16:9、3:4、4:3封面' }}</small></div><el-button @click="materialLibraryVisible=false">取消</el-button><el-button type="primary" :disabled="!selectedMaterials.length || (!libraryManualMode && pickerNeedsCoverSelection)" @click="confirmMaterialSelection">{{ libraryManualMode ? '导入所选视频' : '导入本集素材' }}</el-button></div></template>
          </el-dialog>
<el-dialog
            v-model="accountDialogVisible"
            title="选择账号"
            width="600px"
            class="account-dialog"
          >
            <div class="account-dialog-content">
              <el-checkbox-group v-model="tempSelectedAccounts">
                <div class="account-list">
                  <el-checkbox
                    v-for="account in availableAccounts"
                    :key="account.id"
                    :label="account.id"
                    class="account-item"
                  >
                    <div class="account-info">
                      <span class="account-name">{{ account.name }}</span>
                    </div>
                  </el-checkbox>
                </div>
              </el-checkbox-group>
            </div>

            <template #footer>
              <div class="dialog-footer">
                <el-button @click="accountDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="confirmAccountSelection">确定</el-button>
              </div>
            </template>
          </el-dialog>
<el-dialog
            v-model="topicDialogVisible"
            title="添加话题"
            width="600px"
            class="topic-dialog"
          >
            <div class="topic-dialog-content">
              <!-- 自定义话题输入 -->
              <div class="custom-topic-input">
                <el-input
                  v-model="customTopic"
                  placeholder="输入自定义话题"
                  class="custom-input"
                >
                  <template #prepend>#</template>
                </el-input>
                <el-button type="primary" @click="addCustomTopic">添加</el-button>
              </div>

              <!-- 推荐话题 -->
              <div class="recommended-topics">
                <h4>推荐话题</h4>
                <div class="topic-grid">
                  <el-button
                    v-for="topic in recommendedTopics"
                    :key="topic"
                    :type="currentTab?.selectedTopics?.includes(topic) ? 'primary' : 'default'"
                    @click="toggleRecommendedTopic(topic)"
                    class="topic-btn"
                  >
                    {{ topic }}
                  </el-button>
                </div>
              </div>
            </div>

            <template #footer>
              <div class="dialog-footer">
                <el-button @click="topicDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="confirmTopicSelection">确定</el-button>
              </div>
            </template>
          </el-dialog></div>
      </div>
    </div>
  </div>
  <el-dialog v-model="historyVisible" title="发布记录" width="min(1180px, 94vw)" class="publication-history-dialog" top="32px" append-to-body>
    <template #header><div class="publication-history-heading"><strong>发布记录</strong><span>查看各账号的发布结果，核对后更新状态</span></div></template>
    <div class="history-toolbar"><el-input v-model="historySearch" placeholder="搜索剧集、集数、平台或账号" clearable aria-label="搜索发布记录"><template #prefix><el-icon><Search/></el-icon></template></el-input><span class="history-record-count">{{ filteredPublishHistory.length }} 条记录</span><el-button :loading="bilibiliHistoryBusy" @click="syncBilibiliHistory(true)">同步B站已发布</el-button><el-button :loading="historyBusy" @click="loadPublishHistory"><el-icon><RefreshRight/></el-icon>刷新</el-button></div>
    <details class="history-manual-panel"><summary>补记手动发布<span>已在平台发布的作品，可手动登记</span></summary><div class="history-manual">
      <span class="history-current-file" :title="historyCurrentFiles">{{ historyCurrentFiles || '先在当前任务选择已经发布的视频' }}</span>
      <el-select v-model="historyManualAccount" placeholder="选择已发布到的账号" aria-label="补记发布账号"><el-option v-for="account in accountStore.accounts" :key="account.id" :value="account.id" :label="`${account.platform} · ${account.name}`"/></el-select>
      <el-button type="primary" :disabled="!historyManualAccount || !historyCurrentFiles" :loading="historyBusy" @click="recordManualPublication">记为已发布</el-button>
    </div></details>
    <div class="history-table-area"><el-table :data="filteredPublishHistory" height="100%" empty-text="暂无发布记录，提交视频后会自动记录">
      <el-table-column label="平台 / 账号" min-width="210"><template #default="{row}"><span class="history-account-identity" :title="historyAccountLabel(row)"><span class="history-platform-icon" :style="{background:platformColors[row.platform]}"><img v-if="platformIconPaths[row.platform]" :src="platformIconPaths[row.platform]" alt=""/><span v-else>{{ (platformNames[row.platform] || '平台').slice(0,1) }}</span></span><span>{{ historyAccountLabel(row) }}</span></span></template></el-table-column>
      <el-table-column prop="series" label="分区 / 剧集" min-width="175" show-overflow-tooltip/>
      <el-table-column label="集数 / 文件" min-width="200"><template #default="{row}"><strong class="history-episode">{{ row.episode ? `第${row.episode}集` : '未识别集数' }}</strong><div class="history-file" :title="row.filename">{{ row.filename }}</div></template></el-table-column>
      <el-table-column label="发布状态" width="145"><template #default="{row}"><el-tag :type="row.status==='published' ? 'success' : row.status==='needs_review' ? 'warning' : 'info'">{{ historyStatusLabels[row.status] || row.status }}</el-tag></template></el-table-column>
      <el-table-column label="更新时间" width="130"><template #default="{row}"><span class="history-date">{{ new Date(row.updated_at*1000).toLocaleDateString('zh-CN') }}</span><span class="history-time">{{ new Date(row.updated_at*1000).toLocaleTimeString('zh-CN',{hour12:false}) }}</span></template></el-table-column>
      <el-table-column label="核对结果" width="205" fixed="right"><template #default="{row}"><div class="history-row-actions"><el-button v-if="!['published','cleared'].includes(row.status)" size="small" :disabled="historyBusy" @click="reconcilePublication(row,'published')">确认已发布</el-button><el-button v-if="!['cleared','failed'].includes(row.status)" size="small" :disabled="historyBusy" @click="reconcilePublication(row,'cleared')">确认未发布</el-button><span v-if="row.status==='cleared'" class="history-reconciled">已解除拦截</span></div></template></el-table-column>
    </el-table></div>
    <template #footer><div class="history-dialog-footer"><span>已提交不代表已发布，请核对平台结果；记录会用于重复发布提醒。</span><el-button @click="historyVisible=false">关闭</el-button></div></template>
  </el-dialog>
  <Teleport to="body">
    <el-dialog v-model="preflightVisible" title="发布前检查结果" width="1000px" class="publish-preflight-dialog">
      <p class="optional-hint">检查仅使用本地文件和发布记录，不会登录平台；本地登录文件可读取不代表平台登录仍有效。硬性错误会阻止所有账号提交，提醒需你核对。</p>
      <el-table :data="preflightRows" max-height="520" empty-text="暂无预检结果">
        <el-table-column prop="account" label="平台 / 账号" min-width="170"/>
        <el-table-column prop="label" label="检查项" width="120"/>
        <el-table-column label="结果" width="95"><template #default="{row}"><el-tag :type="row.status==='error'?'danger':row.status==='warning'?'warning':'success'">{{ row.status==='error'?'未通过':row.status==='warning'?'需核对':'通过' }}</el-tag></template></el-table-column>
        <el-table-column prop="message" label="说明" min-width="350"/>
      </el-table>
      <template #footer><el-button @click="preflightVisible=false">关闭</el-button></template>
    </el-dialog>
    <el-dialog v-model="jobHistoryVisible" title="发布任务记录" width="1000px" class="job-history-dialog">
      <p class="optional-hint">记录提交时的素材、账号、阶段和结果。服务重启不会自动重发；流程完成仍需核对平台发布状态。</p>
      <div class="history-toolbar"><el-input v-model="jobHistorySearch" placeholder="搜索剧集、账号或失败原因" clearable aria-label="搜索发布任务记录"/><el-button :loading="jobHistoryBusy" @click="loadJobHistory">刷新任务记录</el-button></div>
      <el-alert v-if="jobHistoryError" :title="jobHistoryError" type="warning" :closable="false"/>
      <el-table v-loading="jobHistoryBusy" :data="filteredJobRecords" max-height="520" empty-text="暂无任务记录，仅记录升级后新提交的任务">
        <el-table-column label="提交时间" width="170"><template #default="{row}">{{ jobRecordTime(row.createdAt) }}</template></el-table-column>
        <el-table-column label="平台 / 账号" min-width="160"><template #default="{row}">{{ row.accountLabel || platformNames[row.platform] }}</template></el-table-column>
        <el-table-column label="剧集 / 素材" min-width="180"><template #default="{row}"><strong>{{ row.materialLabel || row.title || '未记录名称' }}</strong><div v-for="path in row.fileList || []" :key="path" class="history-file" :title="path">{{ path.replaceAll('\\','/').split('/').pop() }}</div></template></el-table-column>
        <el-table-column label="状态 / 最后阶段" min-width="170"><template #default="{row}"><el-tag :type="row.resultUncertain ? 'warning' : row.status==='failed' ? 'danger' : row.status==='completed' ? 'success' : 'info'">{{ row.resultUncertain ? '结果待核对' : taskStateLabels[row.status] || row.status }}</el-tag><div>{{ row.stage }} · {{ row.progress || 0 }}%</div></template></el-table-column>
        <el-table-column prop="message" label="结果 / 失败原因" min-width="250"/>
      </el-table>
    </el-dialog>

    <aside v-if="floatingResults.length && !statusCollapsed" ref="statusFloatRef" class="publish-status-float task-status-card" :class="{'is-dragging':statusDragging}" :style="statusFloatStyle" aria-label="发布任务状态浮窗">
      <header class="task-status-drag-handle" @pointerdown="startStatusDrag"><div><el-progress type="circle" :percentage="finishedTaskPercent" :width="22" :stroke-width="4" :show-text="false" color="#202938"/><strong>发布任务状态</strong><span class="float-total-percent">{{ finishedTaskPercent }}%</span></div><div class="task-window-actions"><button @click="openJobHistory">任务记录</button><button v-if="statusFloatPosition" @click="statusFloatPosition=null" aria-label="重置任务窗位置">归位</button><button @click="statusCollapsed=true" :aria-expanded="false">收起</button></div></header>
      <div class="task-status-overview"><div class="task-metric"><span>任务处理进度</span><strong>{{ finishedTaskPercent }}<small>%</small></strong></div><el-progress :percentage="finishedTaskPercent" :show-text="false" :stroke-width="6" :color="taskSummary.failed ? '#d65353' : '#3478e5'"/><div class="task-status-counts"><span class="count-running">{{ taskSummary.running }}执行</span><span>{{ taskSummary.queued }}排队</span><span class="count-completed">{{ taskSummary.completed }}完成</span><span class="count-failed">{{ taskSummary.failed }}失败</span><span class="count-confirmation">{{ taskSummary.confirmation }}待确认</span></div></div>
      <nav class="task-status-filters" aria-label="筛选任务状态"><button v-for="filter in taskStatusFilters" :key="filter.value" :class="{active:statusTaskFilter===filter.value}" @click="statusTaskFilter=filter.value">{{ filter.label }}</button></nav>
      <div class="publish-status-list" aria-label="各账号任务结果">
        <article v-for="result in filteredStatusTasks" :key="result.jobId || `${result.tabName}-${result.accountId}`" :class="`status-${result.status}`">
          <button class="task-inline-row" @click="expandedTaskRows[`${result.tabName}-${result.accountId}`]=!expandedTaskRows[`${result.tabName}-${result.accountId}`]" :aria-expanded="!!expandedTaskRows[`${result.tabName}-${result.accountId}`]" :title="`${result.materialLabel || describeTaskMaterial(result.submissionPayload)} · ${taskStatusMessage(result)}`">
            <img v-if="taskPlatformIcon(result)" class="task-platform-icon" :src="taskPlatformIcon(result)" alt=""/>
            <span class="task-inline-account">{{ result.label }}</span>
            <el-progress :percentage="result.progress || 0" :show-text="false" :stroke-width="5" :color="taskStateColors[result.status] || '#4a90ed'"/>
            <span class="task-inline-percent">{{ result.progress || 0 }}%</span>
            <span class="task-inline-state" :style="{color:taskStateColors[result.status]}">{{ taskStateLabels[result.status] || result.status }}</span>
          </button>
          <div v-show="expandedTaskRows[`${result.tabName}-${result.accountId}`]" class="task-expanded-details">
          <div class="status-account"><span class="status-account-identity"><span class="status-dot" :style="{background:taskStateColors[result.status]}"/><img v-if="taskPlatformIcon(result)" class="task-platform-icon" :src="taskPlatformIcon(result)" alt=""/><strong>{{ result.label }}</strong></span><span class="task-state-badge" :style="{color:taskStateColors[result.status]}">{{ result.manualXhs && result.status==='awaiting_confirmation' ? '待人工发布' : taskStateLabels[result.status] || result.status }}</span></div>
          <div v-if="taskPhaseEntries(result).length" class="task-phase-summary"><el-tag v-for="phase in taskPhaseEntries(result)" :key="phase.key" size="small" :type="phase.type" :title="phase.message">{{ phase.label }}</el-tag></div>
          <div class="task-material-label" :title="result.materialLabel || describeTaskMaterial(result.submissionPayload)">{{ result.materialLabel || describeTaskMaterial(result.submissionPayload) }}</div><div class="task-stage"><span>{{ result.stage || taskStateLabels[result.status] }}</span><small>{{ result.progress || 0 }}%</small></div><el-progress :percentage="result.progress || 0" :show-text="false" :stroke-width="4" :color="taskStateColors[result.status] || '#3478e5'"/>
          <div v-if="result.collectionTask" class="task-collection-state"><p :style="{color:result.collectionTask.status==='completed'?'#169b50':'#d48806'}">{{ result.collectionTask.message }}</p><el-button v-if="result.collectionTask.status==='failed'" size="small" :loading="result.collectionChanging" @click="retryCollection(result)">重试加入合集</el-button></div>
          <p v-if="result.status==='running' && result.uploadWaiting" class="task-queue-message">{{ result.uploadPercent == null ? '平台未提供上传百分比，正在等待视频上传完成' : `平台上传进度：${result.uploadPercent}%` }}</p>
          <p v-if="['failed','awaiting_confirmation'].includes(result.status)" class="task-attention-message">{{ result.message }}</p><p v-else-if="result.status==='queued'" class="task-queue-message">等待空闲上传名额，最多同时2个账号</p><details v-else-if="result.message" class="task-message-details"><summary>{{ result.tabLabel }} · 查看详情</summary><p>{{ result.message }}</p></details>
          <div v-if="result.status==='running' && result.windowAvailable" class="task-repeat-actions"><el-button size="small" :loading="result.windowChanging" @click="togglePublishWindow(result)">{{ result.windowVisible ? '恢复隐藏' : '显示页面' }}</el-button><span v-if="result.windowVisible" class="optional-hint">验证完成后可恢复隐藏，请勿关闭浏览器</span></div><div v-if="result.status==='failed' && result.submissionPayload" class="task-repeat-actions"><el-button size="small" @click="retryFailedUpload(result)">重试</el-button></div><div v-if="result.manualXhs && result.status==='awaiting_confirmation'" class="xhs-manual-task"><p class="optional-hint">账号：{{ result.label }}。请在官方页面核对登录账号；封面、合集、AI声明和定时设置需手动填写。</p><div class="task-repeat-actions"><a href="https://creator.xiaohongshu.com/publish/publish?from=homepage&amp;target=video" target="_blank" rel="noopener noreferrer" class="manual-publish-link">打开小红书发布页</a><el-button size="small" @click="copyManualText(result)">复制标题和话题</el-button></div><el-input type="textarea" :rows="3" readonly :model-value="manualXhsText(result.submissionPayload)" aria-label="小红书半自动发布文案"/><div v-for="file in manualXhsMaterials(result.submissionPayload)" :key="file.path" class="manual-material-file"><span :title="file.path">{{ file.label }}：{{ file.path.replaceAll('\\','/').split('/').pop() }}</span><el-button link @click="openManualMaterial(file.path)">打开文件夹</el-button><el-button link @click="copyManualPath(file.path)">复制路径</el-button></div><div class="task-repeat-actions"><el-button type="primary" size="small" :loading="result.manualSaving" @click="confirmManualXhs(result)">已手动发布</el-button><el-button size="small" :disabled="result.manualSaving" @click="cancelRepeatUpload(result)">取消本账号</el-button></div></div><div v-else-if="result.status==='awaiting_confirmation'" class="task-repeat-actions"><el-button size="small" type="primary" @click="continueRepeatUpload(result)">继续上传</el-button><el-button size="small" @click="cancelRepeatUpload(result)">取消本账号</el-button></div>
          </div>
        </article><div v-if="!filteredStatusTasks.length" class="task-status-empty">暂无此类任务</div>
      </div><footer class="task-status-footnote">进度为任务流程阶段，完成后仍需核对平台发布结果</footer>
    </aside>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, inject } from 'vue'
import { Upload, Plus, Close, Folder } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
const publishHeaderReady=ref(false)
onMounted(()=>{publishHeaderReady.value=true})
const toggleStudioSidebar=inject('toggleStudioSidebar',()=>{})
const handlePublishMenu=command=>command==='batch' ? batchPublish() : command==='jobs' ? openJobHistory() : command==='preflight' ? (preflightVisible.value=true) : toggleStudioSidebar()
const closeReferenceTab=name=>{if(tabs.length>1)removeTab(name)}
import { useAccountStore } from '@/stores/account'
import { useAppStore } from '@/stores/app'
import { materialApi } from '@/api/material'
import { accountApi } from '@/api/account'
import { http } from '@/utils/request'
import { platformsWithSelectedAccounts, buildDestinations, platformNames, takePlatformSettings, defaultAccountSelection, videoCoverPayload } from '@/utils/publishTargets.mjs'
import { materialPublications, publicationLabels } from '@/utils/materialPublication.mjs'
import { publishBusyState } from '@/utils/publishBusy.mjs'
import { episodeFolders, coverKinds as pickerCoverKinds } from '@/utils/episodeFolders.mjs'
import { summarizeTasks, visibleTaskStatuses, taskStateColors, taskStateLabels, describeTaskMaterial, taskStatusMessage, retrySubmissionPayload, taskPhaseEntries } from '@/utils/taskStatus.mjs'
import {loadTaskSnapshot,saveTaskSnapshot} from '@/utils/taskSnapshot.mjs'
import {manualXhsEnabled,createManualXhsTask,manualXhsText,manualXhsMaterials} from '@/utils/xhsManual.mjs'
import {loadPublishDraft,savePublishDraft,unfinishedMaterial} from '@/utils/publishDraft.mjs'
import {automationOutcome,automationNextAvailable} from '@/utils/publishAutomation.mjs'
import { buildEpisodeImport, isVideoMaterial, nextEpisodeFiles, selectDefaultVideo, distinctCoverChoices } from '@/utils/episodeImport.mjs'
import { saveCollectionPreference, restoreCollectionPreference, applyCollectionTitle, collectionEpisodeTitle } from '@/utils/collectionPreferences.mjs'

const historyVisible=ref(false)
const historyBusy=ref(false)
const historySearch=ref('')
const preflightVisible=ref(false)
const preflightRows=ref([])
const runPublishPreflight=async(prepared,automatic=false)=>{
 const rows=[];const errors=[];const warnings=[]
 try{
  const reports=await Promise.all(prepared.map(async item=>({item,report:(await http.post('/publishPreflight',{...item.payload,manual:item.manual===true},{headers:{'X-OmniPost-Local':'1'},silentError:true})).data})))
  for(const {item,report} of reports){
   if(typeof report?.ok!=='boolean' || !Array.isArray(report.checks))throw new Error('本地预检返回异常，请检查后台后重试')
   for(const check of report.checks)rows.push({...check,account:item.payload.accountLabel || item.account.name})
   if(!report.ok && !(report.errors || []).length)errors.push(`${item.payload.accountLabel}：预检未通过，请查看检查结果`)
   for(const message of report.errors || [])errors.push(`${item.payload.accountLabel}：${message}`)
   for(const message of report.warnings || [])warnings.push(`${item.payload.accountLabel}：${message}`)
  }
  preflightRows.value=rows
  if(errors.length){preflightVisible.value=true;throw new Error(`发布前检查未通过：${errors[0]}`)}
  if(warnings.length){
   if(automatic){preflightVisible.value=true;throw new Error('预检发现需人工确认的提醒，自动连续发布已暂停，请查看预检结果')}
   try{await ElMessageBox.confirm(warnings.slice(0,6).join('\n')+(warnings.length>6?'\n更多提醒请查看最近预检结果':''),'发布前检查提醒',{confirmButtonText:'已核对，继续提交',cancelButtonText:'返回修改',type:'warning',customClass:'preflight-warning-message'})}
   catch{throw new Error('已取消提交，请修改后重试')}
  }
 }catch(error){
  if(error?.response?.status===404)throw new Error('发布前检查功能需要先重启软件后台；请等待当前任务结束后重启再提交')
  if(error?.code==='ERR_NETWORK')throw new Error('无法连接发布前检查接口。后台可能仍是旧版本；请等待当前任务结束后重启软件，再刷新网页提交。本次未创建发布任务。')
  throw error
 }
}

const jobHistoryVisible=ref(false)
const jobHistoryBusy=ref(false)
const jobHistoryError=ref('')
const jobHistorySearch=ref('')
const jobRecords=ref([])
const filteredJobRecords=computed(()=>{
 const query=jobHistorySearch.value.trim().toLowerCase()
 return jobRecords.value.filter(job=>`${job.materialLabel} ${job.title} ${job.accountLabel} ${platformNames[job.platform]} ${job.stage} ${job.message}`.toLowerCase().includes(query))
})
const loadJobHistory=async()=>{
 jobHistoryBusy.value=true;jobHistoryError.value=''
 try{jobRecords.value=(await http.get('/publishJobs',{}, {silentError:true})).data || []}
 catch(error){jobHistoryError.value=error?.response?.status===404 ? '任务记录功能需要重启软件后台后生效；旧版本未保存的任务无法补录。' : '任务记录读取失败，请检查本机后台后重试'}
 finally{jobHistoryBusy.value=false}
}
const openJobHistory=()=>{jobHistoryVisible.value=true;void loadJobHistory()}
const jobRecordTime=value=>value ? new Date(value*1000).toLocaleString('zh-CN',{hour12:false}) : '—'

const historyManualAccount=ref(null)
const publishHistory=ref([])
const bilibiliHistoryBusy=ref(false)
const syncBilibiliHistory=async(force=false)=>{
  if(bilibiliHistoryBusy.value || !accountStore.accounts.some(account=>account.platform==='B站'))return
  bilibiliHistoryBusy.value=true
  try{
    const response=await http.post('/publishHistory',{action:'sync_bilibili',force},{headers:{'X-OmniPost-Local':'1'},silentError:true,timeout:180000})
    await loadPublishHistory()
    const data=response.data || {}
    if(data.errors?.length)ElMessage.warning('部分B站账号同步失败，请检查登录状态或网络；原有标记已保留')
    else if(force && data.busy)ElMessage.info('B站同步正在进行，请稍后查看')
    else if(force)ElMessage.success(`B站同步完成，匹配${(data.accounts || []).reduce((sum,item)=>sum+item.matched,0)}集`)
  }catch(error){ElMessage.warning('B站发布记录同步失败，原有标记已保留，可稍后重试')}
  finally{bilibiliHistoryBusy.value=false}
}
const libraryPublicationMarks = material => materialPublications(material, publishHistory.value)
const historyStatusLabels={pending:'任务在途 / 待核对',submitted:'已提交 · 待核对',published:'已发布',needs_review:'结果待核对',failed:'未发布 · 可重试',cleared:'已解除拦截'}
const historyAccountLabel=row=>`${platformNames[row.platform] || row.platform} · ${accountStore.accounts.find(account=>account.filePath===row.account)?.name || '账号已移除'}`
const historyCurrentFiles=computed(()=>{
  const tab=tabs.find(item=>item.name===activeTab.value)
  return tab && !isArticleTab(tab) ? tab.fileList.map(file=>file.name).join('、') : ''
})
const filteredPublishHistory=computed(()=>{
  const query=historySearch.value.trim().toLowerCase()
  return publishHistory.value.filter(row=>`${row.series} ${row.episode ? `第${row.episode}集` : ''} ${row.filename} ${historyAccountLabel(row)}`.toLowerCase().includes(query))
})
const loadPublishHistory=async()=>{
  historyBusy.value=true
  try{publishHistory.value=(await http.get('/publishHistory')).data || []}finally{historyBusy.value=false}
}
const openPublishHistory=()=>{historyVisible.value=true;loadPublishHistory().catch(()=>{});syncBilibiliHistory()}
const recordManualPublication=async()=>{
  const tab=tabs.find(item=>item.name===activeTab.value)
  if(!historyManualAccount.value || !tab?.fileList.length || isArticleTab(tab))return
  const account=accountStore.accounts.find(item=>item.id===historyManualAccount.value)
  try{
    await ElMessageBox.confirm(`确认“${historyCurrentFiles.value}”已经发布到 ${account.platform} · ${account.name}？`,'补记已发布',{confirmButtonText:'确认补记',cancelButtonText:'取消'})
    historyBusy.value=true
    await http.post('/publishHistory',{action:'manual',accountId:account.id,fileList:tab.fileList.map(file=>file.path),title:tab.title},{headers:{'X-OmniPost-Local':'1'}})
    ElMessage.success('已补记，下次提交会提醒重复');await loadPublishHistory()
  }catch(error){if(!['cancel','close'].includes(error))console.error(error)}finally{historyBusy.value=false}
}
const reconcilePublication=async(row,status)=>{
  try{
    await ElMessageBox.confirm(status==='published' ? '确认该账号的这一集已经发布？' : '确认这一集没有发布，并允许再次提交？','核对发布记录',{confirmButtonText:'确认',cancelButtonText:'取消'})
    historyBusy.value=true
    await http.post('/publishHistory',{id:row.id,status},{headers:{'X-OmniPost-Local':'1'}});await loadPublishHistory()
  }catch(error){if(!['cancel','close'].includes(error))console.error(error)}finally{historyBusy.value=false}
}

// API base URL
const episodeSourceLabel=tab=>{const file=materials.value.find(file=>file.file_path===tab.episodeSourceVideoPath && (file.section_id || 0)===(tab.episodeSectionId || 0));return file ? `${file.section_name || librarySections.value.find(section=>section.id===file.section_id)?.name || '未分区'} / ${file.folder_name}` : ''}
const referenceAiEnabled=tab=>tab.selectedPlatform===6 ? tab.bilibiliCreationStatement===1 : Boolean(tab.aiGenerated)
const setReferenceAi=(tab,value)=>{if(tab.selectedPlatform===6)tab.bilibiliCreationStatement=value ? 1 : null;else tab.aiGenerated=value}
const publishConfigurationReady=tab=>Boolean(tab.selectedAccounts.length && tab.title.trim() && (isArticleTab(tab) ? tab.articleBody.trim() : tab.fileList.length))
const platformIconPaths={1:'/platform-icons/xiaohongshu.svg',3:'/platform-icons/tiktok.svg',4:'/platform-icons/kuaishou.svg',6:'/platform-icons/bilibili.svg',2:'/platform-icons/channels.svg'}
const allPickerAccountsSelected=tab=>accountPlatformGroups.value.length>0 && accountPlatformGroups.value.every(platform=>platform.accounts.every(account=>tab.selectedAccounts.includes(account.id)))
const togglePublishAccount=(tab,id,checked)=>{tab.selectedAccounts=checked ? [...new Set([...tab.selectedAccounts,id])] : tab.selectedAccounts.filter(key=>key!==id);onAccountsChange(tab)}
const toggleAllPublishAccounts=(tab,checked)=>{tab.selectedAccounts=checked ? accountPlatformGroups.value.flatMap(platform=>platform.accounts.map(account=>account.id)) : [];onAccountsChange(tab)}
const pickCoverReplacement=event=>event.currentTarget.closest('.video-cover-card')?.querySelector('input[type=file]')?.click()
const setSelectedVideoMetadata=(file,event)=>{const video=event.target;file.videoWidth=video.videoWidth;file.videoHeight=video.videoHeight;file.videoDuration=Number.isFinite(video.duration) ? video.duration : 0}
const videoDurationLabel=seconds=>`${Math.floor(seconds/60).toString().padStart(2,'0')}:${Math.floor(seconds%60).toString().padStart(2,'0')}`
const openLibraryForTab=tab=>{currentUploadTab.value=tab;selectMaterialLibrary()}
const platformColors = {1:'#ed4564',2:'#f29925',3:'#272c36',4:'#f47d31',5:'#4778d5',6:'#ee669d',7:'#e74747',8:'#e6ad27',9:'#2577dc'}
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'

// Authorization headers
const authHeaders = computed(() => ({
  'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
}))

// 当前激活的tab
const activeTab = ref('tab1')

// tab计数器
let tabCounter = 1

// 获取应用状态管理
const appStore = useAppStore()

// 上传相关状态
const uploadOptionsVisible = ref(false)
const localUploadVisible = ref(false)
const materialLibraryVisible = ref(false)
const currentUploadTab = ref(null)
const selectedMaterials = ref([])
const materials = computed(() => appStore.materials)
const libraryFolder = ref('__all__')
const librarySections = ref([])
const librarySectionId = ref(0)
const librarySectionMaterials = computed(()=>materials.value.filter(file=>(file.section_id || 0) === librarySectionId.value))
const libraryCoverIds = ref({landscape:'',portrait:'',recommendation:''})
const libraryFolders = computed(()=>episodeFolders(librarySectionMaterials.value,publishHistory.value))
const librarySectionSearch=ref('')
const librarySearch=ref('')
const libraryFilter=ref('all')
const libraryOnlyUnfinished=ref(false)
const libraryManualMode=ref(false)
const pickerCoverLabels={landscape:'16:9',portrait:'3:4',recommendation:'4:3'}
const pickerFilters=[{value:'all',label:'全部'},{value:'unpublished',label:'无已发布记录'},{value:'published',label:'有已发布记录'}]
const pickerSections=computed(()=>[{id:0,name:'未分区'},...librarySections.value].map(section=>({...section,count:materials.value.filter(file=>(file.section_id || 0)===section.id).length})).filter(section=>section.name.includes(librarySectionSearch.value.trim())))
const pickerSectionName=computed(()=>librarySections.value.find(section=>section.id===librarySectionId.value)?.name || '未分区')
const filteredLibraryFolders=computed(()=>libraryFolders.value.filter(folder=>{
 const matches=!librarySearch.value.trim() || `${folder.name} ${folder.files.map(file=>file.filename).join(' ')}`.toLowerCase().includes(librarySearch.value.trim().toLowerCase())
 const published=folder.publications.some(record=>record.status==='published')
 return matches && (!libraryOnlyUnfinished.value || !published) && (libraryFilter.value==='all' || (libraryFilter.value==='published' ? published : !published))
}))
const pickerSelectedFolder=computed(()=>libraryFolders.value.find(folder=>folder.name===libraryFolder.value))
const pickerNeedsVersion=computed(()=>!selectedMaterials.value.length || libraryVideos.value.length>1 || pickerCoverKinds.some(kind=>libraryCoverOptions(kind).length>1))
const pickerNeedsCoverSelection=computed(()=>pickerCoverKinds.some(kind=>libraryCoverOptions(kind).length>1 && !libraryCoverIds.value[kind]))
const manualLibraryVideos=computed(()=>librarySectionMaterials.value.filter(isVideoMaterial).filter(file=>!libraryOnlyUnfinished.value || unfinishedMaterial(file,publishHistory.value)).filter(file=>!librarySearch.value.trim() || file.filename.toLowerCase().includes(librarySearch.value.trim().toLowerCase())))
const selectPickerSection=id=>{librarySectionId.value=id;libraryFolder.value='__all__';selectedMaterials.value=[];libraryManualMode.value=false;librarySearch.value='';libraryFilter.value='all';onLibraryFolderChange()}
const selectEpisodeFolder=folder=>{libraryManualMode.value=false;libraryFolder.value=folder.name;onLibraryFolderChange()}
const toggleManualLibrary=()=>{libraryManualMode.value=!libraryManualMode.value;libraryFolder.value='__all__';onLibraryFolderChange()}
const createPickerSection=async()=>{
 try{
  const {value}=await ElMessageBox.prompt('输入新的剧集分区名称','新建分区',{inputValidator:value=>Boolean(value?.trim()) && value.trim().length<=60 || '请输入1至60字的分区名称',confirmButtonText:'创建',cancelButtonText:'取消'})
  const response=await materialApi.createSection(value.trim())
  librarySections.value=(await materialApi.getSections()).data || []
  const section=librarySections.value.find(section=>section.name===value.trim())
  if(section)selectPickerSection(section.id)
 }catch(error){if(!['cancel','close'].includes(error))ElMessage.warning(error.response?.data?.msg || error.message || '创建分区失败')}
}
const libraryFolderFiles = computed(() => libraryFolder.value === '__all__' ? librarySectionMaterials.value : librarySectionMaterials.value.filter(file=>file.folder_name===libraryFolder.value))
const libraryVideos = computed(() => libraryFolderFiles.value.filter(isVideoMaterial))
const libraryCoverOptions = kind => distinctCoverChoices(libraryFolderFiles.value.filter(file=>file.available!==false && file.material_role===`${kind}_cover`))
const onLibraryFolderChange = () => {
  const preferred=libraryFolder.value !== '__all__' ? selectDefaultVideo(libraryVideos.value) : null
  selectedMaterials.value = preferred ? [preferred.id] : []
  libraryCoverIds.value = Object.fromEntries(pickerCoverKinds.map(kind=>[kind,libraryCoverOptions(kind).length===1 ? libraryCoverOptions(kind)[0].id : '']))
}

// 批量发布相关状态
const batchPublishing = ref(false)
const batchPublishMessage = ref('')
const batchPublishType = ref('info')

// 平台列表 - 对应后端type字段
const platforms = [
  { key: 3, name: '抖音' },
  { key: 4, name: '快手' },
  { key: 1, name: '小红书' },
  { key: 6, name: 'B站' },
  { key: 2, name: '视频号' },
  { key: 5, name: '百家号' },
  { key: 7, name: '今日头条' },
  { key: 8, name: '搜狐' },
  { key: 9, name: '知乎' }
]

const defaultTabInit = {
  name: 'tab1',
  label: '发布1',
  fileList: [], // 后端返回的文件名列表
  displayFileList: [], // 用于显示的文件列表
  selectedAccounts: [], // 选中的账号ID列表
  selectedPlatform: 3, // 默认选中抖音（单选）
  selectedPlatforms: [3],
  platformSettings: {},
  collections: {},
  collectionCatalogs: {},
  accountPlatforms: [],
  videoCovers: {},
  episodeSourceVideoPath: null,
  destinationResults: [],
  title: '',
  productLink: '', // 商品链接
  productTitle: '', // 商品名称
  selectedTopics: [], // 话题列表（不带#号）
  scheduleEnabled: false, // 定时发布开关
  videosPerDay: 1, // 每天发布视频数量
  dailyTimes: ['10:00'], // 每天发布时间点列表
  startDays: 0, // 从今天开始计算的发布天数，0表示明天，1表示后天
  publishStatus: null, // 发布状态，包含message和type
  autoPublish: false,
  automationActive: false,
  automationMessage: '',
  automationGeneration: 0,
  publishing: false, // 发布状态，用于控制按钮loading效果
  isDraft: false, // 是否保存为草稿，仅视频号平台可见
  isOriginal: false, // 视频号原创声明由用户主动勾选
  preflighting: false,
  xhsManual: false,
  aiGenerated: true, // 抖音/快手/小红书/视频号 AI 内容声明（默认勾选）
  // B站创作声明：null=不传；-1无需标注；1=AI；2=虚构演绎；3=营销；4=个人观点
  bilibiliCreationStatement: 1,
  bilibiliCategory:21,
  dryRun: false, // 仅预览不发布：默认关闭；B站走 CLI，勾选后会直接跳过上传
  contentType: 'video', // 今日头条：video | article
  articleBody: '', // 今日头条文章正文
  // 今日头条图文封面：single=单图，none=无封面
  coverMode: 'single',
  coverImage: '', // 后端 videoFile 下文件名（单图平台）
  coverImages: [], // 搜狐多图封面：[{ path, name, previewUrl }]
  coverPreviewUrl: '',
  coverFileName: '',
  // 今日头条图文作品声明（单选；空字符串=不声明）
  // 搜狐号复用该字段表示「信息来源」，默认「无特别声明」
  // 知乎复用该字段表示「创作声明」，默认「无声明」
  workStatement: ''
}

// B站创作声明选项（creation_statement.id）
const bilibiliCreationOptions = [
  { label: '含 AI 生成内容', value: 1 },
  { label: '含虚构演绎内容', value: 2 },
  { label: '内容含营销信息', value: 3 },
  { label: '个人观点，仅供参考', value: 4 },
  { label: '内容无需标注', value: -1 }
]

// 支持「视频 / 图文文章」两种内容类型的平台：5=百家号，7=今日头条；8=搜狐 / 9=知乎（仅图文）
const articleCapablePlatforms = [5, 7, 8, 9]
const articleOnlyPlatforms = [8, 9]

const onContentTypeChange = (tab) => {
  if (articleOnlyPlatforms.includes(tab.selectedPlatform)) {
    tab.contentType = 'article'
  }
}

const onPlatformChange = (tab) => {
  if (articleOnlyPlatforms.includes(tab.selectedPlatform)) {
    tab.contentType = 'article'
    // 搜狐默认信息来源 / 知乎默认创作声明
    if (tab.selectedPlatform === 8) {
      if (!sohuInfoSourceOptions.includes(tab.workStatement)) {
        tab.workStatement = '无特别声明'
      }
    } else if (tab.selectedPlatform === 9) {
      if (!zhihuCreationStatementOptions.includes(tab.workStatement)) {
        tab.workStatement = '无声明'
      }
    } else if (
      sohuInfoSourceOptions.includes(tab.workStatement) ||
      zhihuCreationStatementOptions.includes(tab.workStatement)
    ) {
      tab.workStatement = ''
    }
  } else if (tab.selectedPlatform === 7) {
    // 切回头条时，若之前是搜狐/知乎选项则清空
    if (
      sohuInfoSourceOptions.includes(tab.workStatement) ||
      zhihuCreationStatementOptions.includes(tab.workStatement)
    ) {
      tab.workStatement = ''
    }
  } else if (
    sohuInfoSourceOptions.includes(tab.workStatement) ||
    zhihuCreationStatementOptions.includes(tab.workStatement)
  ) {
    tab.workStatement = ''
  }
}

const switchPlatformSettings = (tab, next) => {
  if (tab.selectedPlatform) tab.platformSettings[tab.selectedPlatform] = takePlatformSettings(tab)
  tab.selectedPlatform = next
  Object.assign(tab, tab.platformSettings[next] || takePlatformSettings(defaultTabInit))
  onPlatformChange(tab)
}

const onAccountsChange = tab => {
  tab.selectedPlatforms = platformsWithSelectedAccounts(tab.selectedPlatforms,tab.selectedAccounts,accountStore.accounts)
  tab.accountPlatforms = [...tab.selectedPlatforms]
  if (!tab.selectedPlatforms.includes(tab.selectedPlatform)) switchPlatformSettings(tab,tab.selectedPlatforms[0] || null)
  loadSelectedCollections(tab)
}
const onPlatformsChange = (tab) => {
  const added = tab.selectedPlatforms.filter(key => !tab.accountPlatforms.includes(key))
  if (!tab.selectedPlatforms.includes(tab.selectedPlatform)) {
    switchPlatformSettings(tab, tab.selectedPlatforms[0] || null)
  }
  tab.selectedAccounts = tab.selectedAccounts.filter(id => {
    const account = accountStore.accounts.find(item => item.id === id)
    return tab.selectedPlatforms.some(key => platformNames[key] === account?.platform)
  })
  for (const account of accountStore.accounts) {
    if (added.some(key => platformNames[key] === account.platform) && !tab.selectedAccounts.includes(account.id)) tab.selectedAccounts.push(account.id)
  }
  tab.accountPlatforms = [...tab.selectedPlatforms]
  loadSelectedCollections(tab)
}

// 当前 tab 是否处于图文文章模式
const isArticleTab = (tab) =>
  articleCapablePlatforms.includes(tab.selectedPlatform) && tab.contentType === 'article'

// 今日头条图文「作品声明」选项
const toutiaoWorkStatementOptions = [
  '取材网络',
  '引用站内',
  '个人观点，仅供参考',
  '引用AI',
  '虚构演绎，故事经历',
  '投资观点，仅供参考',
  '健康医疗分享，仅供参考'
]

// 搜狐号图文「信息来源」选项
const sohuInfoSourceOptions = [
  '无特别声明',
  '引用声明',
  '包含AI创作内容',
  '包含虚构创作'
]

// 知乎图文「创作声明」选项（写文章页下拉）
const zhihuCreationStatementOptions = [
  '包含剧透',
  '包含医疗建议',
  '虚构创作',
  '包含理财内容',
  '包含 AI 辅助创作 作者对内容负责',
  '无声明'
]

// helper to create a fresh deep-copied tab from defaultTabInit
const makeNewTab = () => {
  // prefer structuredClone when available (newer browsers/node), fallback to JSON
  try {
    return typeof structuredClone === 'function' ? structuredClone(defaultTabInit) : JSON.parse(JSON.stringify(defaultTabInit))
  } catch (e) {
    return JSON.parse(JSON.stringify(defaultTabInit))
  }
}

// tab页数据 - 默认只有一个tab (use deep copy to avoid shared refs)
const tabs = reactive([
  makeNewTab()
])

const restoredDrafts=loadPublishDraft(localStorage)
const restoredTasks=loadTaskSnapshot(localStorage).length ? loadTaskSnapshot(localStorage) : loadTaskSnapshot(sessionStorage)
if(restoredDrafts.length || restoredTasks.length){
 const names=[...new Set([...restoredDrafts,...restoredTasks].map(tab=>tab.name))]
 tabs.splice(0,tabs.length,...names.map(name=>{
  const draft=restoredDrafts.find(tab=>tab.name===name)
  const task=restoredTasks.find(tab=>tab.name===name)
  const tab={...makeNewTab(),...draft,name,destinationResults:task?.results || []}
  tab.displayFileList=tab.fileList.map(file=>({name:file.name,url:file.url}))
  return tab
 }))
 activeTab.value=tabs[0].name
 tabCounter=Math.max(...tabs.map(tab=>Number(tab.name.slice(3)) || 1))
}
watch(tabs,saved=>{savePublishDraft(localStorage,saved);saveTaskSnapshot(localStorage,saved);saveTaskSnapshot(sessionStorage,saved)},{deep:true})

// 账号相关状态
const accountDialogVisible = ref(false)
const tempSelectedAccounts = ref([])
const statusCollapsed = ref(true)
// Measure the visible dock boundary so navigation size and browser zoom do not
// leave a gap or put settings behind the fixed publishing buttons.
const sizePublishSettings=()=>{
 const main=document.querySelector('#app .el-main')
 const dock=document.querySelector('.action-buttons')
 if(!main || !dock || window.innerWidth<=930)return
 for(const grid of document.querySelectorAll('.publish-grid')){
  if(!grid.getClientRects().length)continue
  const top=grid.getBoundingClientRect().top+main.scrollTop
  grid.style.setProperty('--settings-panel-height',`${Math.max(240,dock.getBoundingClientRect().top-top-8)}px`)
 }
}
const schedulePublishSettings=()=>requestAnimationFrame(sizePublishSettings)
watch(activeTab,schedulePublishSettings,{flush:'post'})
onMounted(()=>{schedulePublishSettings();window.addEventListener('resize',schedulePublishSettings)})
onBeforeUnmount(()=>window.removeEventListener('resize',schedulePublishSettings))
const expandedTaskRows=reactive({})
const floatingResults = computed(()=>tabs.flatMap(tab=>tab.destinationResults.map(result=>({...result,tabName:tab.name,tabLabel:tab.label}))))
const taskPlatformIcon=result=>{const names={'快手':'kuaishou','抖音':'tiktok','小红书':'xiaohongshu','B站':'bilibili','视频号':'channels'};const name=names[result.label?.split(' · ')[0]];return name ? `/platform-icons/${name}.svg` : null}
const taskSummary=computed(()=>summarizeTasks(floatingResults.value))
const finishedTaskPercent=computed(()=>taskSummary.value.progress)
const statusTaskFilter=ref('all')
const taskStatusFilters=[{value:'all',label:'全部'},{value:'active',label:'执行 / 排队'},{value:'attention',label:'需要处理'}]
const filteredStatusTasks=computed(()=>visibleTaskStatuses(floatingResults.value,statusTaskFilter.value))
const statusFloatRef=ref(null)
const statusFloatPosition=ref(null)
const statusDragging=ref(false)
const statusFloatStyle=computed(()=>statusFloatPosition.value ? {left:`${statusFloatPosition.value.x}px`,top:`${statusFloatPosition.value.y}px`,right:'auto',bottom:'auto'} : {})
let statusDragOrigin=null
const clampStatusPosition=(x,y)=>{
 const box=statusFloatRef.value?.getBoundingClientRect()
 return {x:Math.max(12,Math.min(x,window.innerWidth-(box?.width || 410)-12)),y:Math.max(12,Math.min(y,window.innerHeight-(box?.height || 400)-76))}
}
const moveStatusDrag=event=>{
 if(!statusDragOrigin)return
 statusFloatPosition.value=clampStatusPosition(statusDragOrigin.x+event.clientX-statusDragOrigin.clientX,statusDragOrigin.y+event.clientY-statusDragOrigin.clientY)
}
const stopStatusDrag=()=>{statusDragging.value=false;statusDragOrigin=null;window.removeEventListener('pointermove',moveStatusDrag);window.removeEventListener('pointerup',stopStatusDrag);window.removeEventListener('pointercancel',stopStatusDrag)}
const startStatusDrag=event=>{
 if(event.button!==0 || event.target.closest('button'))return
 const box=statusFloatRef.value?.getBoundingClientRect();if(!box)return
 event.preventDefault();statusDragOrigin={x:box.left,y:box.top,clientX:event.clientX,clientY:event.clientY};statusDragging.value=true
 window.addEventListener('pointermove',moveStatusDrag);window.addEventListener('pointerup',stopStatusDrag);window.addEventListener('pointercancel',stopStatusDrag)
}
const resizeStatusCard=()=>{if(statusFloatPosition.value)statusFloatPosition.value=clampStatusPosition(statusFloatPosition.value.x,statusFloatPosition.value.y)}
onMounted(()=>window.addEventListener('resize',resizeStatusCard))
onBeforeUnmount(()=>{stopStatusDrag();window.removeEventListener('resize',resizeStatusCard)})
const currentTab = ref(null)

// 获取账号状态管理
const accountStore = useAccountStore()

const accountPlatformGroups = computed(() => platforms.map(platform => ({...platform,
  accounts: accountStore.accounts.filter(account => account.platform === platform.name)
})).filter(platform => platform.accounts.length))

const catalogQueue = []
let activeCatalogLoads = 0
const drainCatalogQueue = () => {
  while (activeCatalogLoads < 2 && catalogQueue.length) {
    const run = catalogQueue.shift()
    activeCatalogLoads++
    void run().finally(() => { activeCatalogLoads--; drainCatalogQueue() })
  }
}

const loadAccountCollections = (tab, accountId, refresh = false) => {
  if(manualXhsEnabled(tab,1) && accountStore.accounts.find(account=>account.id===accountId)?.platform==='小红书')return
  if (tab.collectionCatalogs[accountId]?.loading) return
  if (!refresh && tab.collectionCatalogs[accountId]) return
  tab.collectionCatalogs[accountId] = {loading:true, status:'loading', items:[], message:'', selectionInvalid:!!tab.collectionCatalogs[accountId]?.selectionInvalid}
  catalogQueue.push(async () => {
    if(manualXhsEnabled(tab,1) && accountStore.accounts.find(account=>account.id===accountId)?.platform==='小红书'){tab.collectionCatalogs[accountId]={loading:false,items:[],status:'manual',message:'半自动模式：请在官方页面选择合集'};return}
    try {
      const response = await http.get('/accountCollections', {accountId, refresh:refresh ? '1' : undefined})
      const catalog = response.data
      tab.collectionCatalogs[accountId] = {...catalog, loading:false, selectionInvalid:!!tab.collectionCatalogs[accountId]?.selectionInvalid}
      if (tab.collections[accountId] === undefined) {
        const account=accountStore.accounts.find(item=>item.id===accountId)
        const remembered=restoreCollectionPreference(localStorage,account,catalog.items || [])
        if (remembered !== undefined) tab.collections[accountId]=remembered
      }
      const selectedCollection=(catalog.items || []).find(item=>item.value===tab.collections[accountId] && !item.disabled)
      if (selectedCollection) applyCollectionTitle(tab,selectedCollection.name)
      if (tab.collections[accountId] && !(catalog.items || []).some(option => option.value === tab.collections[accountId] && !option.disabled)) {
        tab.collections[accountId] = ''
        tab.collectionCatalogs[accountId].selectionInvalid = true
        tab.collectionCatalogs[accountId].message += '；原选合集不可用，请重新选择或确认不加入合集'
      }
    } catch (error) {
      tab.collectionCatalogs[accountId] = {loading:false, status:'unavailable', items:[], selectionInvalid:!!tab.collectionCatalogs[accountId]?.selectionInvalid, message:error?.response?.data?.msg || '合集读取失败，请稍后刷新'}
      if (tab.collections[accountId]) {
        tab.collections[accountId] = ''
        tab.collectionCatalogs[accountId].selectionInvalid = true
      }
    }
  })
  drainCatalogQueue()
}

const onXhsManualChange=tab=>{
 for(const account of accountStore.accounts.filter(account=>account.platform==='小红书')){
  if(tab.xhsManual)tab.collectionCatalogs[account.id]={loading:false,items:[],status:'manual',message:'半自动模式：请在官方页面选择合集'}
  else if(tab.selectedAccounts.includes(account.id))loadAccountCollections(tab,account.id,true)
 }
}

const loadSelectedCollections = (tab) => {
  for (const id of tab.selectedAccounts) loadAccountCollections(tab, id)
}

const acknowledgeCollection = (tab, id) => {
  saveCollectionPreference(localStorage,accountStore.accounts.find(item=>item.id===id),tab.collections[id])
  const selected=(tab.collectionCatalogs[id]?.items || []).find(item=>item.value===tab.collections[id] && !item.disabled)
  if (selected) applyCollectionTitle(tab,selected.name)
  if (tab.collectionCatalogs[id]) tab.collectionCatalogs[id].selectionInvalid = false
}

const initializeTabAccounts = (tab) => {
  const selected = defaultAccountSelection(accountStore.accounts)
  tab.selectedPlatforms = selected.platforms
  tab.selectedAccounts = selected.accountIds
  tab.accountPlatforms = [...selected.platforms]
  if (!selected.platforms.includes(tab.selectedPlatform)) switchPlatformSettings(tab, selected.platforms[0] || null)
  loadSelectedCollections(tab)
}

// 页面加载时获取账号列表
onMounted(async () => {
  if (accountStore.accounts.length === 0) {
    try {
      const res = await accountApi.getAccounts()
      if (res.code === 200 && res.data) {
        accountStore.setAccounts(res.data)
      }
    } catch (error) {
      console.error('获取账号数据失败:', error)
    }
  }
  for (const tab of tabs) initializeTabAccounts(tab)
  await loadPublishHistory().catch(()=>{})
})

// 根据选择的平台获取可用账号列表
const availableAccounts = computed(() => {
  const platformMap = {
    3: '抖音',
    2: '视频号',
    1: '小红书',
    4: '快手',
    5: '百家号',
    6: 'B站',
    7: '今日头条',
    8: '搜狐',
    9: '知乎'
  }
  const selected = currentTab.value?.selectedPlatforms || []
  return accountStore.accounts.filter(acc => selected.some(key => platformMap[key] === acc.platform))
})

// 话题相关状态
const topicDialogVisible = ref(false)
const customTopic = ref('')

// 推荐话题池（面具 / 道具 / 工艺相关）
const recommendedTopics = [
  '树脂面具', '艺术面具', '创意面具', '仿真面具', '人脸面具', '立体面具', '装饰面具', '收藏面具',
  '树脂工艺', '树脂制品', '树脂艺术', '树脂创作', '树脂手工', '树脂模型', '树脂雕塑',
  '手工制作', '手工艺术', '手工工艺', '匠心制作', '工艺美术', '工艺品制作', '艺术创作',
  '原创设计', '创意设计', '造型设计', '产品设计',
  '道具设计', '道具制作', '手工道具', '创意道具', '仿真道具', '艺术道具', '展示道具',
  '拍摄道具', '摄影道具', '影视道具', '电影道具', '电视剧道具', '短剧道具', '广告道具',
  '舞台道具', '演出道具', '戏剧道具', '剧场道具', '表演道具', '角色道具', '人物道具',
  '场景道具', '陈列道具', '展览道具', '橱窗道具',
  '影视制作', '电影制作', '短剧制作', '视频制作', '广告拍摄', '创意拍摄',
  '影视美术', '电影美术', '剧组道具', '片场道具', '道具师', '美术道具', '影视置景', '场景搭建',
  '舞台美术', '舞台造型', '人物造型', '角色造型', '造型艺术',
  '特效化妆', '影视特效', '化妆特效', '人物特效',
  '仿真艺术', '写实艺术', '雕塑艺术', '雕刻艺术',
  '模型制作', '人物模型', '角色模型', '艺术模型', '静物模型', '创意模型',
  '手办制作', '艺术手办', '收藏模型', '艺术摆件', '创意摆件', '家居摆件', '桌面摆件',
  '空间装饰', '艺术装饰', '陈列设计', '展示设计',
  '视觉设计', '视觉艺术', '视觉创意', '美学设计', '艺术美学', '静物美学', '细节美学', '质感美学',
  '小众美学', '高级感', '氛围感', '设计感', '艺术感', '创意感',
  '产品展示', '产品拍摄', '产品细节', '细节展示', '质感展示', '工艺展示',
  '制作过程', '手工过程', '创作过程', '幕后制作', '制作日常', '工作室日常', '手作日常', '匠人日常',
  '创意短片', '创意视频', '艺术短片', '产品短片', '短视频创作', '定格动画', '视觉实验',
  '光影艺术', '色彩艺术', '创意灵感', '设计灵感', '艺术灵感', '手工灵感',
  '审美分享', '好物分享', '小众好物', '创意好物', '艺术好物', '设计好物',
  '特色工艺品', '个性化设计', '创意定制', '道具定制', '面具定制', '模型定制', '艺术定制',
  '原创作品', '手工作品', '艺术作品', '设计作品',
  '匠心工艺', '精细工艺', '细节工艺', '传统工艺', '现代工艺', '创意工艺',
  '道具艺术', '面具艺术', '面具文化', '面具造型', '面具收藏', '面具设计', '面具制作',
  '角色扮演道具', '舞台表演', '剧场艺术', '戏剧艺术', '表演艺术',
  '艺术生活', '生活美学', '让艺术走进生活', '发现创意', '创意无限', '灵感记录',
  '作品分享', '每日创作', '艺术分享', '设计分享', '手作分享',
  '中国制造', '中国手工', '创意制造', '工艺制造'
]

// 各平台随机抽取话题数量：固定值 或 [min, max]
const platformTopicCount = {
  3: 5,           // 抖音：5 个
  6: [6, 7],      // B站：6~7 个
  4: 4,           // 快手：4 个
  1: [7, 8],      // 小红书：7~8 个
  2: 5,           // 视频号：默认 5 个
  5: 5,           // 百家号：默认 5 个
  7: 5,           // 今日头条：默认 5 个
  8: 5            // 搜狐：默认 5 个
}

const getTopicCountForPlatform = (platform) => {
  const conf = platformTopicCount[platform]
  if (Array.isArray(conf)) {
    const [min, max] = conf
    return min + Math.floor(Math.random() * (max - min + 1))
  }
  return conf || 5
}

const getTopicCountHint = (platform) => {
  const conf = platformTopicCount[platform]
  if (Array.isArray(conf)) return `（随机 ${conf[0]}~${conf[1]} 个）`
  if (conf) return `（随机 ${conf} 个）`
  return '（随机 5 个）'
}

// Fisher-Yates 洗牌后取前 n 个
const sampleTopics = (pool, n) => {
  const arr = [...pool]
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[arr[i], arr[j]] = [arr[j], arr[i]]
  }
  return arr.slice(0, Math.min(n, arr.length))
}

// 添加新tab
const addTab = () => {
  tabCounter++
  const newTab = makeNewTab()
  newTab.name = `tab${tabCounter}`
  newTab.label = `发布${tabCounter}`
  initializeTabAccounts(newTab)
  tabs.push(newTab)
  activeTab.value = newTab.name
}

// 删除tab
const removeTab = (tabName) => {
  const index = tabs.findIndex(tab => tab.name === tabName)
  if (index > -1) {
    tabs.splice(index, 1)
    // 如果删除的是当前激活的tab，切换到第一个tab
    if (activeTab.value === tabName && tabs.length > 0) {
      activeTab.value = tabs[0].name
    }
  }
}

// 处理文件上传成功
const handleUploadSuccess = (response, file, tab) => {
  if (response.code === 200) {
    // 获取文件路径
    const filePath = response.data.path || response.data
    // 从路径中提取文件名
    const filename = filePath.split('/').pop()

    // 保存文件信息到fileList，包含文件路径和其他信息
    const fileInfo = {
      name: file.name,
      url: materialApi.getMaterialPreviewUrl(filename), // 使用getMaterialPreviewUrl生成预览URL
      path: filePath,
      size: file.size,
      type: file.type
    }

    // 添加到文件列表
    tab.fileList.push(fileInfo)

    // 更新显示列表
    tab.displayFileList = [...tab.fileList.map(item => ({
      name: item.name,
      url: item.url
    }))]

    ElMessage.success('文件上传成功')
  } else {
    ElMessage.error(response.msg || '上传失败')
  }
}

// 图文封面：上传前校验
// 百家号 5MB JPEG/PNG；搜狐/知乎 10MB jpg/jpeg/png；其它 20MB JPEG/PNG
const getCoverMaxSize = (tab) => {
  if (tab?.selectedPlatform === 5) return 5 * 1024 * 1024
  if (tab?.selectedPlatform === 8 || tab?.selectedPlatform === 9) return 10 * 1024 * 1024
  return 20 * 1024 * 1024
}

const readImageSize = (file) => new Promise((resolve, reject) => {
  const url = URL.createObjectURL(file)
  const img = new Image()
  img.onload = () => {
    const size = { width: img.width, height: img.height }
    URL.revokeObjectURL(url)
    resolve(size)
  }
  img.onerror = () => {
    URL.revokeObjectURL(url)
    reject(new Error('无法读取图片尺寸'))
  }
  img.src = url
})

const beforeCoverUpload = async (file, tab) => {
  const isSohu = tab?.selectedPlatform === 8
  const isImage = isSohu
    ? (file.type === 'image/jpeg' || file.type === 'image/png' || file.type === 'image/jpg'
      || /\.(jpe?g|png)$/i.test(file.name || ''))
    : (file.type === 'image/jpeg' || file.type === 'image/png' || file.type === 'image/jpg'
      || /\.(jpe?g|png)$/i.test(file.name || ''))
  if (!isImage) {
    ElMessage.error(isSohu ? '封面仅支持 jpg、jpeg、png 格式' : '封面仅支持 JPEG、PNG 格式')
    return false
  }
  const maxMb = tab?.selectedPlatform === 5 ? 5 : ((tab?.selectedPlatform === 8 || tab?.selectedPlatform === 9) ? 10 : 20)
  const maxSize = getCoverMaxSize(tab)
  if (file.size > maxSize) {
    ElMessage.error(`单张封面最大支持 ${maxMb}MB`)
    return false
  }
  if (isSohu) {
    if (Array.isArray(tab.coverImages) && tab.coverImages.length >= 1) {
      ElMessage.error('搜狐号封面最多 1 张')
      return false
    }
    try {
      const { width, height } = await readImageSize(file)
      if (width <= 450 || height <= 300) {
        ElMessage.error(`搜狐封面尺寸需大于 450×300，当前 ${width}×${height}`)
        return false
      }
    } catch (e) {
      ElMessage.error('无法校验封面尺寸，请更换图片后重试')
      return false
    }
  }
  return true
}

const beforeVideoCoverUpload = async (file) => {
  if (!/\.(jpe?g|png|webp|bmp)$/i.test(file.name || '')) {
    ElMessage.error('请选择 JPG、PNG、WebP 或 BMP 图片'); return false
  }
  try { await readImageSize(file) }
  catch { ElMessage.error('无法读取图片，请更换图片后重试'); return false }
  return true
}

const handleVideoCoverSuccess = (response, file, tab, kind) => {
  if (response?.code !== 200) { ElMessage.error(response?.msg || '封面上传失败'); return }
  const path = response.data?.path || response.data
  const filename = String(path || '').split('/').pop()
  tab.videoCovers[kind] = {path, name:file.name, previewUrl:materialApi.getMaterialPreviewUrl(filename)}
  ElMessage.success(kind === 'recommendation' ? '封面上传成功，将用于B站推荐页' : '封面上传成功，将按平台分配')
}

const handleCoverUploadSuccess = (response, file, tab) => {
  if (response?.code === 200) {
    const filePath = response.data?.path || response.data
    const filename = String(filePath || '').split('/').pop()
    tab.coverImage = filePath
    tab.coverFileName = file?.name || filename
    tab.coverPreviewUrl = materialApi.getMaterialPreviewUrl(filename)
    tab.coverMode = 'single'
    ElMessage.success('封面上传成功')
  } else {
    ElMessage.error(response?.msg || '封面上传失败')
  }
}

const handleSohuCoverUploadSuccess = (response, file, tab) => {
  if (response?.code === 200) {
    const filePath = response.data?.path || response.data
    const filename = String(filePath || '').split('/').pop()
    if (!Array.isArray(tab.coverImages)) tab.coverImages = []
    tab.coverImages.push({
      path: filePath,
      name: file?.name || filename,
      previewUrl: materialApi.getMaterialPreviewUrl(filename)
    })
    // 兼容旧字段：首图写入 coverImage
    tab.coverImage = tab.coverImages[0]?.path || ''
    tab.coverFileName = tab.coverImages.map(i => i.name).join(', ')
    tab.coverPreviewUrl = tab.coverImages[0]?.previewUrl || ''
    tab.coverMode = 'single'
    ElMessage.success('封面上传成功')
  } else {
    ElMessage.error(response?.msg || '封面上传失败')
  }
}

const removeSohuCover = (tab, index) => {
  if (!Array.isArray(tab.coverImages)) return
  tab.coverImages.splice(index, 1)
  tab.coverImage = tab.coverImages[0]?.path || ''
  tab.coverFileName = tab.coverImages.map(i => i.name).join(', ')
  tab.coverPreviewUrl = tab.coverImages[0]?.previewUrl || ''
  ElMessage.success('已删除该封面')
}

const handleCoverUploadError = (error) => {
  let message = ''
  try { message = JSON.parse(error?.message || '{}').msg || '' } catch {}
  ElMessage.error(message ? `封面上传失败：${message}` : '封面上传失败，请检查本地服务连接后重试')
}

const clearArticleCover = (tab) => {
  tab.coverImage = ''
  tab.coverImages = []
  tab.coverPreviewUrl = ''
  tab.coverFileName = ''
  ElMessage.success('已清除封面')
}

const previewArticleCover = (tab) => {
  if (tab.coverPreviewUrl) {
    window.open(tab.coverPreviewUrl, '_blank')
  }
}

// 处理文件上传失败
const handleUploadError = (error) => {
  let message = ''
  try { message = JSON.parse(error?.message || '{}').msg || '' } catch {}
  if (!message && error?.status === 413) message = '文件被服务端大小限制拦截，请检查服务配置'
  ElMessage.error(message ? `文件上传失败：${message}` : '文件上传失败，请检查本地服务、磁盘剩余空间后重试')
}

// 删除已上传文件
const removeFile = (tab, index) => {
  // 从文件列表中删除
  tab.fileList.splice(index, 1)

  // 更新显示列表
  tab.displayFileList = [...tab.fileList.map(item => ({
    name: item.name,
    url: item.url
  }))]

  ElMessage.success('文件删除成功')
}

// 话题相关方法
// 按当前平台数量，从话题池随机抽取并覆盖已选话题
const randomPickTopics = (tab) => {
  const count = getTopicCountForPlatform(tab.selectedPlatform)
  tab.selectedTopics = sampleTopics(recommendedTopics, count)
  ElMessage.success(`已随机抽取 ${tab.selectedTopics.length} 个话题`)
}

// 打开添加话题弹窗
const openTopicDialog = (tab) => {
  currentTab.value = tab
  topicDialogVisible.value = true
}

// 添加自定义话题
const addCustomTopic = () => {
  if (!customTopic.value.trim()) {
    ElMessage.warning('请输入话题内容')
    return
  }
  if (currentTab.value && !currentTab.value.selectedTopics.includes(customTopic.value.trim())) {
    currentTab.value.selectedTopics.push(customTopic.value.trim())
    customTopic.value = ''
    ElMessage.success('话题添加成功')
  } else {
    ElMessage.warning('话题已存在')
  }
}

// 切换推荐话题
const toggleRecommendedTopic = (topic) => {
  if (!currentTab.value) return

  const index = currentTab.value.selectedTopics.indexOf(topic)
  if (index > -1) {
    currentTab.value.selectedTopics.splice(index, 1)
  } else {
    currentTab.value.selectedTopics.push(topic)
  }
}

// 删除话题
const removeTopic = (tab, index) => {
  tab.selectedTopics.splice(index, 1)
}

// 确认添加话题
const confirmTopicSelection = () => {
  topicDialogVisible.value = false
  customTopic.value = ''
  currentTab.value = null
  ElMessage.success('添加话题完成')
}

// 账号选择相关方法
// 打开账号选择弹窗
const openAccountDialog = (tab) => {
  currentTab.value = tab
  tempSelectedAccounts.value = [...tab.selectedAccounts]
  accountDialogVisible.value = true
}

// 确认账号选择
const confirmAccountSelection = () => {
  if (currentTab.value) {
    currentTab.value.selectedAccounts = [...tempSelectedAccounts.value]
  }
  accountDialogVisible.value = false
  currentTab.value = null
  ElMessage.success('账号选择完成')
}

// 删除选中的账号
const removeAccount = (tab, index) => {
  tab.selectedAccounts.splice(index, 1)
}

// 获取账号显示名称
const getAccountDisplayName = (accountId) => {
  const account = accountStore.accounts.find(acc => acc.id === accountId)
  return account ? account.name : accountId
}

const getAccountPlatformName = (id) => accountStore.accounts.find(account => account.id === id)?.platform || ''

// 取消发布
const cancelPublish = (tab) => {
  ElMessage.info('已取消发布')
}

// 确认发布
const buildPublishData = (tab) => {
  // 数据验证
  const isArticle = isArticleTab(tab)
  if (!isArticle && tab.episodeSourceVideoPath && Object.keys(tab.videoCovers || {}).length && tab.fileList.some(file => file.path !== tab.episodeSourceVideoPath)) {
    throw new Error('本任务的封面由整集素材导入，请为其他视频新建任务，或先移除共用封面，避免误用上一集封面')
  }
  const isToutiaoArticle = tab.selectedPlatform === 7 && isArticle
  const isBaijiahaoArticle = tab.selectedPlatform === 5 && isArticle
  const isSohuArticle = tab.selectedPlatform === 8 && isArticle
  const isZhihuArticle = tab.selectedPlatform === 9 && isArticle
  if (!isArticle && tab.fileList.length === 0) {
    ElMessage.error('请先上传视频文件')
    throw new Error('请先上传视频文件')
  }
  if (isArticle && !(tab.articleBody || '').trim()) {
    ElMessage.error('请输入文章正文')
    throw new Error('请输入文章正文')
  }
  // 百家号图文标题下限 2 字：前置拦截，避免后端补字导致标题与预期不一致
  if (isBaijiahaoArticle && tab.title.trim().length < 2) {
    ElMessage.error('百家号图文标题至少 2 个字')
    throw new Error('百家号图文标题至少 2 个字')
  }
  if (isSohuArticle) {
    const sohuTitleLen = tab.title.trim().length
    if (sohuTitleLen < 5 || sohuTitleLen > 72) {
      ElMessage.error('搜狐号文章标题需 5-72 个字')
        throw new Error('搜狐号文章标题需 5-72 个字')
    }
  }
  if (isZhihuArticle) {
    const zhihuTitleLen = tab.title.trim().length
    if (!zhihuTitleLen) {
      ElMessage.error('请输入知乎文章标题')
        throw new Error('请输入知乎文章标题')
    }
    if (zhihuTitleLen > 100) {
      ElMessage.error('知乎文章标题最多 100 个字')
        throw new Error('知乎文章标题最多 100 个字')
    }
  }
  if (isBaijiahaoArticle && (!tab.coverImage || tab.coverMode !== 'single')) {
    ElMessage.error('百家号图文必须上传展示封面')
    throw new Error('百家号图文必须上传展示封面')
  }
  // 小红书（1）、视频号（2）、抖音（3）、快手（4）标题非必填，其它平台仍必填
  if (tab.selectedPlatform !== 1 && tab.selectedPlatform !== 2 && tab.selectedPlatform !== 3 && tab.selectedPlatform !== 4 && !tab.title.trim()) {
    ElMessage.error('请输入标题')
    throw new Error('请输入标题')
  }
  if (!tab.selectedPlatform) {
    ElMessage.error('请选择发布平台')
    throw new Error('请选择发布平台')
  }
  if (tab.selectedAccounts.length === 0) {
    ElMessage.error('请选择发布账号')
    throw new Error('请选择发布账号')
  }

  // 构造发布数据，符合后端API格式
  const publishData = {
    type: tab.selectedPlatform,
    collectionName: tab.collectionName || '',
    title: tab.title,
    tags: tab.selectedTopics, // 不带#号的话题列表
    fileList: isArticle ? [] : tab.fileList.map(file => file.path), // 只发送文件路径
    accountList: tab.selectedAccounts.map(accountId => {
      const account = accountStore.accounts.find(acc => acc.id === accountId)
      return account ? account.filePath : accountId
    }), // 发送账号的文件路径
    enableTimer: tab.scheduleEnabled ? 1 : 0,
    videosPerDay: tab.scheduleEnabled ? tab.videosPerDay || 1 : 1,
    dailyTimes: tab.scheduleEnabled ? tab.dailyTimes || ['10:00'] : ['10:00'],
    startDays: tab.scheduleEnabled ? tab.startDays || 0 : 0,
    category: tab.selectedPlatform === 6 ? (tab.bilibiliCategory || 21) : (tab.isOriginal ? 1 : 0), // 1表示原创，0表示非原创
    productLink: tab.productLink.trim() || '',
    productTitle: tab.productTitle.trim() || '',
    isDraft: tab.isDraft,
    aiGenerated: (tab.selectedPlatform === 1 || tab.selectedPlatform === 2 || tab.selectedPlatform === 3 || tab.selectedPlatform === 4) ? !!tab.aiGenerated : false,
    // B站创作声明 id；null/undefined 表示不传 extra-fields
    bilibiliCreationStatement: tab.selectedPlatform === 6 && tab.bilibiliCreationStatement !== null && tab.bilibiliCreationStatement !== undefined && tab.bilibiliCreationStatement !== ''
      ? Number(tab.bilibiliCreationStatement)
      : null,
    // B站 dryRun 只跳过上传，不会打开预览浏览器。
    dryRun: !!tab.dryRun,
    // 百家号 / 今日头条 / 搜狐 / 知乎：视频/图文文章（搜狐/知乎强制 article）
    contentType: articleOnlyPlatforms.includes(tab.selectedPlatform)
      ? 'article'
      : (articleCapablePlatforms.includes(tab.selectedPlatform) ? (tab.contentType || 'video') : 'video'),
    articleBody: isArticle ? (tab.articleBody || '') : '',
    // 图文封面；搜狐支持多图 coverImages；知乎走单图 thumbnail
    coverImage: isArticle && tab.coverMode === 'single'
      ? (tab.selectedPlatform === 8
          ? (tab.coverImages?.[0]?.path || tab.coverImage || '')
          : (tab.coverImage || ''))
      : (tab.selectedPlatform === 5 && tab.coverImage ? tab.coverImage : ''),
    coverImages: isArticle && tab.selectedPlatform === 8 && tab.coverMode === 'single'
      ? (tab.coverImages || []).map(i => i.path).filter(Boolean)
      : [],
    thumbnail: isArticle && tab.coverMode === 'single'
      ? (tab.selectedPlatform === 8
          ? (tab.coverImages?.[0]?.path || tab.coverImage || '')
          : (tab.coverImage || ''))
      : (tab.selectedPlatform === 5 && tab.coverImage ? tab.coverImage : ''),
    // 今日头条作品声明 / 搜狐信息来源 / 知乎创作声明（复用 workStatement）
    workStatement: (isToutiaoArticle || isSohuArticle || isZhihuArticle) ? (tab.workStatement || '') : '',
    // 兼容旧字段：后端仍接受列表，单选时最多传一项
    workStatements: (isToutiaoArticle || isSohuArticle || isZhihuArticle) && tab.workStatement ? [tab.workStatement] : []
  }

  if (!isArticle) Object.assign(publishData, videoCoverPayload(tab.selectedPlatform, tab.videoCovers))
  return publishData
}

watch(()=>tabs.map(tab=>tab.fileList.map(file=>file.path)),()=>{
  for(const tab of tabs){
    const names=[...new Set(tab.selectedAccounts.map(id=>tab.collectionCatalogs[id]?.items?.find(item=>item.value===tab.collections[id])?.name).filter(Boolean))]
    if(names.length===1)applyCollectionTitle(tab,names[0])
  }
},{deep:true})

const nextEpisodePrompted = new WeakSet()
const nextEpisodeLoading=ref(null)
let nextEpisodePromptBusy=false
const stopAutomation = (tab,message='自动化已停止，已提交的任务继续执行') => {
  tab.automationActive=false;tab.autoPublish=false;tab.automationGeneration++
  tab.automationMessage=message
  if(tab.destinationResults.length)nextEpisodePrompted.add(tab.destinationResults)
}
const prepareNextEpisode = async (tab,automatic=false) => {
  const response=await materialApi.getAllMaterials()
  const files=Array.isArray(response.data) ? response.data : []
  appStore.setMaterials(files)
  if(automatic && !automationNextAvailable(files,tab.fileList[0].path,tab.episodeSectionId))return false
  const next=nextEpisodeFiles(files,tab.fileList[0].path,tab.episodeSectionId)
  let chosen
  try { chosen=buildEpisodeImport(next.files) }
  catch(error){
    if(automatic)throw error
    currentUploadTab.value=tab;librarySectionId.value=next.sectionId;libraryFolder.value=next.folder
    librarySections.value=(await materialApi.getSections()).data || []
    selectedMaterials.value=[];libraryCoverIds.value={landscape:'',portrait:'',recommendation:''};libraryManualMode.value=false;librarySearch.value='';libraryFilter.value='all';materialLibraryVisible.value=true
    ElMessage.warning(`第${next.number}集需要选择视频或封面版本：${error.message}`)
    return
  }
  if(automatic && ['landscape','portrait','recommendation'].some(kind=>!chosen[kind]))throw new Error('下一集缺少三种比例封面，自动化已暂停，请补齐素材')
  if(automatic && !tab.automationActive)return false
  tab.fileList=[{name:chosen.video.filename,path:chosen.video.file_path,url:materialApi.getMaterialPreviewUrl(chosen.video.file_path),size:chosen.video.filesize*1024*1024,type:'video/mp4',episode_number:chosen.video.episode_number,episode_unit:chosen.video.episode_unit}]
  tab.displayFileList=tab.fileList.map(file=>({name:file.name,url:file.url}))
  tab.episodeSourceVideoPath=chosen.video.file_path;tab.episodeSectionId=next.sectionId
  tab.videoCovers={}
  for(const kind of ['landscape','portrait','recommendation']){
    const cover=chosen[kind]
    if(cover)tab.videoCovers[kind]={path:cover.file_path,name:cover.filename,previewUrl:materialApi.getMaterialPreviewUrl(cover.file_path)}
  }
  tab.destinationResults=[];tab.publishStatus=null
  const collectionNames=[...new Set(tab.selectedAccounts.map(id=>tab.collectionCatalogs[id]?.items?.find(item=>item.value===tab.collections[id])?.name).filter(Boolean))]
  tab.title=collectionNames.length===1 ? collectionEpisodeTitle(tab,collectionNames[0]) : chosen.video.filename.replace(/\.[^.]+$/,'')
  tab.autoCollectionTitle=collectionNames.length===1 ? tab.title : ''
  activeTab.value=tab.name
  if(!automatic)ElMessage.success(`已准备第${next.number}集视频和封面，请检查后点击发布`)
  return true
}
// 视频素材卡片上的「下一集」：手动载入素材库同一分区的下一集视频与封面
const loadNextEpisode=async tab=>{
  if(nextEpisodeLoading.value || isArticleTab(tab))return
  if(tab.publishing){ElMessage.warning('正在发布，请等待完成后再切换下一集');return}
  if(tab.automationActive){ElMessage.warning('自动连续发布进行中，无需手动切换下一集');return}
  if(tab.destinationResults.some(result=>['running','queued','awaiting_confirmation'].includes(result.status))){ElMessage.warning('有发布任务仍在进行，请完成后再切换下一集');return}
  if(tab.fileList.length!==1){ElMessage.warning('请先用「素材库」导入本集视频（只保留一个视频文件），再切换下一集');return}
  nextEpisodeLoading.value=tab.name
  try{
    const loaded=await prepareNextEpisode(tab)
    if(loaded===false)ElMessage.info('已到素材库最后一集，没有可切换的下一集素材')
  }catch(error){
    const message=error?.message || '下一集素材读取失败'
    if(/无法确定当前剧集分区/.test(message))ElMessage.warning('当前视频不是从素材库按集导入的，请先用「素材库」选择本集素材')
    else if(/未找到第\d+/.test(message))ElMessage.info(`已到素材库最后一集：${message}`)
    else ElMessage.warning(message)
  }finally{nextEpisodeLoading.value=null}
}
watch(()=>tabs.map(tab=>[tab.publishing,tab.automationActive,...tab.destinationResults.map(result=>[result.status,result.collectionTask?.status,result.windowVisible])]),async()=>{
  if(nextEpisodePromptBusy)return
  for(const tab of tabs){
    const results=tab.destinationResults
    if(tab.publishing || !results.length || nextEpisodePrompted.has(results) || isArticleTab(tab) || tab.fileList.length!==1)continue
    if(tab.automationActive){
      const outcome=automationOutcome(results)
      if(outcome==='paused'){stopAutomation(tab,'自动化已暂停：有错误、待确认或需要处理的任务');nextEpisodePrompted.add(results);continue}
      if(outcome!=='next')continue
      nextEpisodePrompted.add(results);nextEpisodePromptBusy=true
      const generation=tab.automationGeneration
      try{
        const ready=await prepareNextEpisode(tab,true)
        if(!tab.automationActive || tab.automationGeneration!==generation)continue
        if(!ready){stopAutomation(tab,'自动连续发布已完成：已到素材库最后一集');continue}
        tab.automationMessage='自动连续发布中，当前集完成后继续下一集'
        await confirmPublish(tab,true)
      }catch(error){stopAutomation(tab,`自动化已暂停：${error.message || '下一集准备失败'}`)}
      finally{nextEpisodePromptBusy=false}
      continue
    }
    if(!results.every(result=>result.status==='completed') || results.some(result=>!result.jobId))continue
    if(results.some(result=>result.submissionPayload?.dryRun || result.submissionPayload?.isDraft))continue
    nextEpisodePrompted.add(results);nextEpisodePromptBusy=true
    try{
      await ElMessageBox.confirm('本集所有账号任务已结束。\n是否准备下一集？\n\n自动载入同一分区的下一集视频与封面，确认后仍需手动提交发布。','继续上传下一集',{customClass:'next-episode-card',confirmButtonText:'准备下一集',cancelButtonText:'暂不继续',type:'success',closeOnClickModal:false})
      await prepareNextEpisode(tab)
    }catch(error){if(!['cancel','close'].includes(error))ElMessage.warning(error.message || '下一集素材读取失败')}
    finally{nextEpisodePromptBusy=false}
  }
},{deep:true})

let pollingStopped = false
onBeforeUnmount(() => { pollingStopped = true })
const togglePublishWindow = async (result) => {
  if(result.windowChanging)return
  result.windowChanging=true
  try {
    const response=await http.post('/publishWindow',{id:result.jobId,visible:!result.windowVisible},{headers:{'X-OmniPost-Local':'1'},silentError:true})
    result.windowAvailable=response.data.windowAvailable===true
    result.windowVisible=response.data.windowVisible===true
  } catch(error){ElMessage.warning(error.response?.data?.msg || '页面显示状态切换失败，请稍后重试')}
  finally{result.windowChanging=false}
}

const pollDestination = async (result) => {
  for (let attempt = 0; attempt < 360 && !pollingStopped; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 5000))
    if (pollingStopped) return
    try {
      const response = await http.get('/publishJob', { id: result.jobId }, { silentError: true })
      result.status = response.data.status
      result.message = response.data.message
      result.progress = response.data.progress ?? (result.status==='completed' ? 100 : result.progress || 0)
      result.stage = response.data.stage || ''
      result.resultUncertain = response.data.resultUncertain === true
      result.phases = response.data.phases || {}
      result.uploadWaiting = response.data.uploadWaiting === true
      result.uploadPercent = response.data.uploadPercent ?? null
      result.collectionTask = response.data.collectionTask || null
      result.videoSubmitted = response.data.videoSubmitted === true
      result.windowAvailable = response.data.windowAvailable === true
      result.windowVisible = response.data.windowVisible === true
      if (['completed', 'failed'].includes(result.status) && !['running','waiting'].includes(result.collectionTask?.status)) {void loadPublishHistory().catch(()=>{});return}
    } catch (error) {
      if (error.response?.status === 404) {
        result.status = 'failed'
        result.resultUncertain = true
        result.stage = '发布结果待核对'
        result.message = '服务已重启，原任务已中断，发布结果未知。请先到平台核对；确认未发布后再点击重试。'
        return
      }
      result.message = '与本地后台连接中断，正在尝试恢复状态查询；请勿重复提交'
      continue
    }
  }
  result.message = '任务仍在执行或等待平台操作，请检查后端日志'
}

onMounted(()=>{
 if(restoredTasks.length)for(const tab of tabs)for(const result of tab.destinationResults){
  if(result.jobId && (['running','queued'].includes(result.status) || ['running','waiting'].includes(result.collectionTask?.status)))void pollDestination(result)
 }
})

const originalDestination = item => tabs.find(tab=>tab.name===item.tabName)?.destinationResults.find(result=>result.accountId===item.accountId)
const cancelRepeatUpload = item => {
  const result=originalDestination(item)
  if(result?.status!=='awaiting_confirmation')return
  result.status='cancelled';result.stage='已取消';result.message='已取消本账号上传，发布记录保留';delete result.repeatPayload
}
const copyManualText=async result=>{
 try{await navigator.clipboard.writeText(manualXhsText(result.submissionPayload));ElMessage.success('标题和话题已复制')}catch{ElMessage.warning('无法访问剪贴板，请从文案框手动复制')}
}
const copyManualPath=async path=>{
 try{await navigator.clipboard.writeText(path);ElMessage.success('路径已复制')}catch{ElMessage.warning(`请手动复制路径：${path}`)}
}
const openManualMaterial=async path=>{
 try{await http.post('/local/materials/reveal',{path},{headers:{'X-OmniPost-Local':'1'}})}catch(error){ElMessage.warning(error?.response?.status===404 ? '打开文件夹功能需重启软件后台后生效，可先复制素材路径' : error?.response?.data?.msg || '打开文件夹失败，请复制路径手动打开')}
}
const confirmManualXhs=async item=>{
 const result=originalDestination(item)
 if(!result?.manualXhs || result.status!=='awaiting_confirmation' || result.manualSaving)return
 try{
  await ElMessageBox.confirm(`确认「${result.materialLabel}」已手动发布到 ${result.label}？`,'确认手动发布完成',{confirmButtonText:'确认已发布',cancelButtonText:'尚未发布'})
  result.manualSaving=true
  await http.post('/publishHistory',{action:'manual',accountId:result.accountId,fileList:result.submissionPayload.fileList,title:result.submissionPayload.title},{headers:{'X-OmniPost-Local':'1'}})
  result.status='completed';result.progress=100;result.stage='人工确认已发布';result.message='已由用户确认完成发布，发布记录已保存'
  await loadPublishHistory().catch(()=>{})
 }catch(error){if(!['cancel','close'].includes(error))ElMessage.warning(error?.response?.data?.msg || error.message || '保存发布记录失败')}
 finally{result.manualSaving=false}
}

const continueRepeatUpload = async item => {
  const result=originalDestination(item)
  if(result?.status!=='awaiting_confirmation' || !result.repeatPayload)return
  const payload={...result.repeatPayload,requestId:crypto.randomUUID(),confirmRepeat:true}
  result.submissionPayload=JSON.parse(JSON.stringify(payload))
  result.status='queued';result.progress=0;result.jobId=null;result.stage='正在提交';result.message='已确认继续上传，正在提交任务'
  try{
    const response=await http.post('/postVideo',payload,{silentError:true})
    result.jobId=response.data.jobId;delete result.repeatPayload
    result.message='任务已提交，正在后台执行（不代表发布成功）'
    void pollDestination(result)
  }catch(error){
    result.status='failed';result.submissionRejected=Boolean(error?.response);result.stage='提交失败';result.message=error?.response?.data?.msg || error.message || '提交失败'
  }
}

const retryCollection = async item => {
  const result=originalDestination(item)
  if(!result?.collectionTask || result.collectionChanging)return
  result.collectionChanging=true
  try{
    const response=await http.post('/retryKuaishouCollection',{id:result.collectionTask.id},{headers:{'X-OmniPost-Local':'1'},silentError:true})
    result.collectionTask=response.data
    void pollDestination(result)
  }catch(error){ElMessage.error(error?.response?.data?.msg || '重试加入合集失败')}
  finally{result.collectionChanging=false}
}
const retryFailedUpload = async item => {
  if(item.videoSubmitted){await retryCollection(item);return}

  const result=originalDestination(item)
  if(result?.status!=='failed' || !result.submissionPayload)return
  if(result.resultUncertain){
    try{await ElMessageBox.confirm('该任务的发布结果尚未确认。请先到平台核对；只有确认未发布后才重新提交。','核对发布结果',{confirmButtonText:'已核对，确认未发布',cancelButtonText:'取消'})}catch{return}
  }
  const payload=retrySubmissionPayload(result,crypto.randomUUID())
  result.submissionPayload=JSON.parse(JSON.stringify(payload))
  result.status='queued';result.progress=0;result.jobId=null;result.stage='重新提交';result.message='正在重试此账号'
  try{
    const response=await http.post('/postVideo',payload,{silentError:true})
    result.jobId=response.data.jobId
    result.message='重试任务已提交，正在后台执行（不代表发布成功）'
    void pollDestination(result)
  }catch(error){
    if(error?.response?.data?.data?.confirmRepeatRequired){
      result.status='awaiting_confirmation';result.stage='重复发布提醒';result.message=error.response.data.msg
      result.repeatPayload=payload;statusCollapsed.value=false
    }else{
      result.status='failed';result.submissionRejected=Boolean(error?.response);result.stage='提交失败';result.message=error?.response?.data?.msg || error.message || '提交失败'
    }
  }
}

const confirmPublish = async (tab,automatic=false) => {
  if(automatic && !tab.automationActive)return
  if(tab.autoPublish && !automatic){
    if(isArticleTab(tab) || tab.fileList.length!==1)throw new Error('自动连续发布仅支持素材库中单集视频')
    const materials=(await materialApi.getAllMaterials()).data || []
    automationNextAvailable(materials,tab.fileList[0].path,tab.episodeSectionId)
  }
  if (tab.publishing) throw new Error('正在提交任务，请稍候')
  if (tab.destinationResults.some(result => ['queued','running','awaiting_confirmation'].includes(result.status))) {
    ElMessage.warning('已有任务正在执行或等待确认，请在任务状态中处理')
    throw new Error('已有任务正在执行或等待确认')
  }
  tab.platformSettings[tab.selectedPlatform] = takePlatformSettings(tab)
  let destinations
  let prepared
  try {
    destinations = buildDestinations(tab.selectedPlatforms, tab.selectedAccounts, accountStore.accounts)
    // Validate every destination before any external task can start.
    prepared = destinations.map(({platform, account}) => {
      if (!manualXhsEnabled(tab,platform) && tab.collectionCatalogs[account.id]?.selectionInvalid) throw new Error(`${account.name}的原选合集已失效，请重新选择或确认不加入合集`)
      const collectionName = (tab.collections[account.id] || '').trim()
      if (platform === 6 && collectionName && !/^[1-9][0-9]*$/.test(collectionName)) throw new Error('B站请填写数字合集 ID')
      if (collectionName && ![1,2,3,4,5,6].includes(platform)) throw new Error(`${platformNames[platform]}尚未接入合集，请留空`)
      const settings = tab.platformSettings[platform] || takePlatformSettings(defaultTabInit)
      const snapshot = { ...tab, ...settings, selectedPlatform: platform, selectedAccounts: [account.id], collectionName }
      if (articleOnlyPlatforms.includes(platform)) snapshot.contentType = 'article'
      if (collectionName && isArticleTab(snapshot)) throw new Error('合集目前仅支持视频，请清空合集或切换视频')
      const payload=buildPublishData(snapshot)
      payload.requestId=crypto.randomUUID()
      payload.materialLabel=describeTaskMaterial(payload,tab.fileList,librarySections.value.find(section=>section.id===tab.episodeSectionId)?.name || materials.value.find(file=>file.file_path===tab.fileList[0]?.path)?.section_name || '')
      payload.accountLabel=`${platformNames[platform]} · ${account.name}`
      return {platform, account, manual:manualXhsEnabled(tab,platform), payload}
    })
  } catch (error) {
    ElMessage.error(error.message)
    throw error
  }
  tab.publishing=true;tab.preflighting=true
  try{await runPublishPreflight(prepared,automatic)}finally{tab.preflighting=false;tab.publishing=false}
  if(tab.autoPublish && prepared.some(item=>item.manual))throw new Error('小红书半自动发布需要人工确认，请关闭自动连续发布后提交')
  if(tab.autoPublish){
    if(prepared.some(item=>item.payload.dryRun || item.payload.isDraft))throw new Error('预览或草稿模式不能自动连续发布')
    tab.automationActive=true
    tab.automationMessage='自动连续发布中，遇到错误或待确认任务将暂停'
  }
  tab.publishing = true
  tab.destinationResults = []
  let submitted = 0
  try {
    for (const {platform, account, payload, manual} of prepared) {
      const result = reactive({accountId: account.id, label: `${platformNames[platform]} · ${account.name}`, status: 'queued', message: '正在提交', jobId: null, phases:{precheck:{status:'completed',message:'本地预检通过'}}, submissionPayload:JSON.parse(JSON.stringify(payload)), materialLabel:describeTaskMaterial(payload,tab.fileList,librarySections.value.find(section=>section.id===tab.episodeSectionId)?.name || materials.value.find(file=>file.file_path===tab.fileList[0]?.path)?.section_name || '')})
      if(manual){
        tab.destinationResults.push({...createManualXhsTask(account.id,result.label,payload,result.materialLabel),phases:{precheck:{status:'completed',message:'本地预检通过；请在官方页面核对登录账号'}}})
        statusCollapsed.value=false;submitted++;continue
      }
      tab.destinationResults.push(result)
      try {
        if(automatic && !tab.automationActive){result.status='cancelled';result.message='自动化已停止';continue}
        let response
        try {
          response = await http.post('/postVideo', payload, {silentError:true})
        } catch (error) {
          if (!error?.response?.data?.data?.confirmRepeatRequired) throw error
          result.status='awaiting_confirmation'
          result.stage='重复发布提醒'
          result.message=error.response.data.msg
          result.repeatPayload=JSON.parse(JSON.stringify(payload))
          statusCollapsed.value=false
          continue
        }
        result.jobId = response.data.jobId
        result.message = '任务已提交，正在后台执行（不代表发布成功）'
        submitted++
        void pollDestination(result)
      } catch (error) {
        result.status = 'failed'
        result.submissionRejected = Boolean(error?.response)
        result.message = error?.response?.data?.msg || error.message || '提交失败'
      }
    }
    tab.publishStatus = {type: submitted === prepared.length ? 'info' : 'warning', message: `${submitted}/${prepared.length} 个账号任务已准备${prepared.some(item=>item.manual) ? '，小红书请在任务状态中手动发布并确认完成' : '，请查看各账号任务结果'}`}

    return {submitted, total: prepared.length}
    // Keep source files, metadata and account choices for inspection after partial failure.
  } finally {
    tab.publishing = false
  }
}

// 显示上传选项
const showUploadOptions = (tab) => {
  currentUploadTab.value = tab
  uploadOptionsVisible.value = true
}

// 选择本地上传
const selectLocalUpload = () => {
  uploadOptionsVisible.value = false
  localUploadVisible.value = true
}

// 选择素材库
const selectMaterialLibrary = async () => {
  uploadOptionsVisible.value = false

  // Always refresh: newly uploaded episodes must appear in the picker.
  {
    try {
      const [response,sectionsResponse,historyResponse] = await Promise.all([materialApi.getAllMaterials(),materialApi.getSections(),http.get('/publishHistory', {}, {silentError:true}).catch(()=>null)])
      publishHistory.value = historyResponse?.data || []
      if (!historyResponse) ElMessage.warning('发布记录读取失败，暂不能标记已发布集数')
      librarySections.value = Array.isArray(sectionsResponse.data) ? sectionsResponse.data : []
      librarySectionId.value = librarySections.value.some(section=>section.id===librarySectionId.value) ? librarySectionId.value : (librarySections.value[0]?.id || 0)
      if (response.code === 200) {
        appStore.setMaterials(response.data)
      } else {
        ElMessage.error('获取素材列表失败')
        return
      }
    } catch (error) {
      console.error('获取素材列表出错:', error)
      ElMessage.error('获取素材列表失败')
      return
    }
  }

  libraryFolder.value = '__all__'
  libraryCoverIds.value = {landscape:'',portrait:'',recommendation:''}
  selectedMaterials.value = []
  libraryManualMode.value=false;librarySearch.value='';librarySectionSearch.value='';libraryFilter.value='all'
  // 素材库弹窗展开时自动收起发布任务状态浮窗，避免遮挡选择面板
  statusCollapsed.value = true
  materialLibraryVisible.value = true
  syncBilibiliHistory()
}

// 确认素材选择
const confirmMaterialSelection = () => {
  if (libraryFolder.value !== '__all__') {
    try {
      if (selectedMaterials.value.length !== 1) throw new Error('请选择一个要发布的视频版本')
      const chosen = buildEpisodeImport(libraryFolderFiles.value, selectedMaterials.value[0], libraryCoverIds.value)
      const target = currentUploadTab.value
      if (!target) throw new Error('当前发布任务不可用，请重新打开素材库')
      if (target.fileList.length && !window.confirm('导入本集将替换当前任务的视频和封面，是否继续？')) return
      target.fileList = [{name:chosen.video.filename, path:chosen.video.file_path,
        url:materialApi.getMaterialPreviewUrl(chosen.video.file_path), size:chosen.video.filesize*1024*1024, type:'video/mp4',episode_number:chosen.video.episode_number,episode_unit:chosen.video.episode_unit}]
      target.displayFileList = target.fileList.map(file=>({name:file.name,url:file.url}))
      target.videoCovers = {}
      target.episodeSourceVideoPath = chosen.video.file_path
      target.episodeSectionId = librarySectionId.value
      const names=[...new Set(target.selectedAccounts.map(id=>target.collectionCatalogs[id]?.items?.find(item=>item.value===target.collections[id])?.name).filter(Boolean))]
      if(names.length===1)applyCollectionTitle(target,names[0])
      for (const kind of ['landscape','portrait','recommendation']) {
        const cover = chosen[kind]
        if (cover) target.videoCovers[kind] = {path:cover.file_path,name:cover.filename,previewUrl:materialApi.getMaterialPreviewUrl(cover.file_path)}
      }
      materialLibraryVisible.value = false
      selectedMaterials.value = []
      currentUploadTab.value = null
      ElMessage.success(`已导入${libraryFolder.value}的视频与封面`)
    } catch (error) { ElMessage.warning(error.message) }
    return
  }
  if (librarySectionId.value === null) { ElMessage.warning('请先选择分区'); return }
  if (selectedMaterials.value.length === 0) {
    ElMessage.warning('请选择至少一个素材')
    return
  }

  if (currentUploadTab.value) {
    // 将选中的素材添加到当前tab的文件列表
    selectedMaterials.value.forEach(materialId => {
      const material = materials.value.find(m => m.id === materialId)
      if (material) {
        const fileInfo = {
          name: material.filename,
          url: materialApi.getMaterialPreviewUrl(material.file_path),
          path: material.file_path,
          size: material.filesize * 1024 * 1024, // 转换为字节
          type: 'video/mp4'
        }

        // 检查是否已存在相同文件
        const exists = currentUploadTab.value.fileList.some(file => file.path === fileInfo.path)
        if (!exists) {
          currentUploadTab.value.fileList.push(fileInfo)
        }
      }
    })

    // 更新显示列表
    currentUploadTab.value.displayFileList = [...currentUploadTab.value.fileList.map(item => ({
      name: item.name,
      url: item.url
    }))]
  }

  const addedCount = selectedMaterials.value.length
  materialLibraryVisible.value = false
  selectedMaterials.value = []
  currentUploadTab.value = null
  ElMessage.success(`已添加 ${addedCount} 个素材`)
}

// 批量发布对话框状态
const batchPublishDialogVisible = ref(false)
const currentPublishingTab = ref(null)
const publishProgress = ref(0)
const publishResults = ref([])
const isCancelled = ref(false)

// 取消批量发布
const cancelBatchPublish = () => {
  isCancelled.value = true
  ElMessage.info('正在取消发布...')
}

// 批量发布方法
const batchPublish = async () => {
  if (batchPublishing.value) return

  batchPublishing.value = true
  currentPublishingTab.value = null
  publishProgress.value = 0
  publishResults.value = []
  isCancelled.value = false
  batchPublishDialogVisible.value = true

  try {
    for (let i = 0; i < tabs.length; i++) {
      if (isCancelled.value) {
        publishResults.value.push({
          label: tabs[i].label,
          status: 'cancelled',
          message: '已取消'
        })
        continue
      }

      const tab = tabs[i]
      currentPublishingTab.value = tab
      publishProgress.value = Math.floor((i / tabs.length) * 100)

      try {
        const submission = await confirmPublish(tab)
        publishResults.value.push({
          label: tab.label,
          status: submission.submitted === submission.total ? 'success' : 'error',
          message: `${submission.submitted}/${submission.total} 个账号任务已提交，请查看各账号执行结果`
        })
      } catch (error) {
        publishResults.value.push({
          label: tab.label,
          status: 'error',
          message: error.message
        })
        // 不立即返回，继续显示发布结果
      }
    }

    publishProgress.value = 100

    // 统计发布结果
    const successCount = publishResults.value.filter(r => r.status === 'success').length
    const failCount = publishResults.value.filter(r => r.status === 'error').length
    const cancelCount = publishResults.value.filter(r => r.status === 'cancelled').length

    if (isCancelled.value) {
      ElMessage.warning(`已停止后续提交：${successCount}个Tab全部提交，${failCount}个Tab提交失败或部分失败，${cancelCount}个未执行`)
    } else if (failCount > 0) {
      ElMessage.error(`提交结束：${successCount}个Tab全部提交，${failCount}个Tab提交失败或部分失败；已提交任务可能仍在执行`)
    } else {
      ElMessage.info('所有Tab任务已提交，请查看各账号执行结果及平台审核状态')
      setTimeout(() => {
        batchPublishDialogVisible.value = false
      }, 1000)
    }

  } catch (error) {
    console.error('批量发布出错:', error)
    ElMessage.error('批量发布出错，请重试')
  } finally {
    batchPublishing.value = false
    isCancelled.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;
.account-platform-grid {display:flex; flex-wrap:wrap; gap:12px; margin-top:12px}
.account-platform-card {flex:1 1 160px; min-width:0; padding:12px 16px; border:1px solid var(--el-border-color-light); border-radius:8px; background:var(--el-fill-color-extra-light)}
.account-platform-card :deep(.el-checkbox-group) {display:flex; flex-wrap:wrap; gap:4px 12px; margin-top:6px}
.account-platform-card :deep(.el-checkbox) {margin-right:0; max-width:100%}
.account-platform-card :deep(.el-checkbox__label) {overflow:hidden; text-overflow:ellipsis}
.platform-settings-tabs {margin-top:8px; display:flex; flex-wrap:wrap; gap:6px}
.video-cover-section {margin:24px 0}
.video-cover-grid {display:flex; flex-wrap:wrap; gap:20px; margin:14px 0}
.video-cover-card {flex:1 1 260px; min-width:0; padding:16px; border:1px solid var(--el-border-color-light); border-radius:8px}
.video-cover-upload {margin-top:12px}
.video-cover-upload :deep(.el-upload) {border:1px dashed var(--el-border-color); border-radius:8px; background:var(--el-fill-color-light); overflow:hidden; width:240px; max-width:100%; aspect-ratio:16 / 9}
.video-cover-upload.portrait :deep(.el-upload) {width:140px; aspect-ratio:3 / 4}
.video-cover-upload img {width:100%; height:100%; object-fit:contain}


.publish-center {
  display: flex;
  flex-direction: column;
  height: 100%;

  // Tab管理区域
  .tab-management {
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
    padding: 15px 20px;

    .tab-header {
      display: flex;
      align-items: flex-start;
      gap: 15px;

      .tab-list {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        flex: 1;
        min-width: 0;

        .tab-item {
           display: flex;
           align-items: center;
           gap: 6px;
           padding: 6px 12px;
           background-color: #f5f7fa;
           border: 1px solid #dcdfe6;
           border-radius: 4px;
           cursor: pointer;
           transition: all 0.3s;
           font-size: 14px;
           height: 32px;

           &:hover {
             background-color: #ecf5ff;
             border-color: #b3d8ff;
           }

           &.active {
             background-color: #409eff;
             border-color: #409eff;
             color: #fff;

             .close-icon {
               color: #fff;

               &:hover {
                 background-color: rgba(255, 255, 255, 0.2);
               }
             }
           }

           .close-icon {
             padding: 2px;
             border-radius: 2px;
             cursor: pointer;
             transition: background-color 0.3s;
             font-size: 12px;

             &:hover {
               background-color: rgba(0, 0, 0, 0.1);
             }
           }
         }
       }

      .tab-actions {
        display: flex;
        gap: 10px;
        flex-shrink: 0;

        .add-tab-btn,
        .batch-publish-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          height: 32px;
          padding: 6px 12px;
          font-size: 14px;
          white-space: nowrap;
        }
      }
    }
  }

  // 批量发布进度对话框样式
  .publish-progress {
    padding: 20px;

    .current-publishing {
      margin: 15px 0;
      text-align: center;
      color: #606266;
    }

    .publish-results {
      margin-top: 20px;
      border-top: 1px solid #EBEEF5;
      padding-top: 15px;
      max-height: 300px;
      overflow-y: auto;

      .result-item {
        display: flex;
        align-items: center;
        padding: 8px 0;
        color: #606266;

        .el-icon {
          margin-right: 8px;
        }

        .label {
          margin-right: 10px;
          font-weight: 500;
        }

        .message {
          color: #909399;
        }

        &.success {
          color: #67C23A;
        }

        &.error {
          color: #F56C6C;
        }

        &.cancelled {
          color: #909399;
        }
      }
    }
  }

  .dialog-footer {
    text-align: right;
  }

  // 内容区域
  .publish-content {
    flex: 1;
    background-color: #fff;
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    padding: 20px;

    .tab-content-wrapper {
      display: flex;
      justify-content: center;

      .tab-content {
        width: 100%;
        max-width: 800px;

        h3 {
          font-size: 16px;
          font-weight: 500;
          color: $text-primary;
          margin: 0 0 10px 0;
        }

        .upload-section,
        .account-section,
        .platform-section,
        .content-type-section,
        .article-body-section,
        .article-cover-section,
        .work-statement-section,
        .title-section,
        .product-section,
        .topic-section,
        .schedule-section {
          margin-bottom: 30px;
        }

        .content-type-section {
          .content-type-radios {
            display: flex;
            gap: 16px;
          }
        }

        .article-body-section {
          .article-body-input {
            width: 100%;
          }
        }

        .article-cover-section {
          .cover-mode-radios {
            display: flex;
            gap: 16px;
            margin-bottom: 12px;
          }

          .article-cover-upload-wrap {
            display: flex;
            flex-wrap: wrap;
            align-items: flex-start;
            gap: 12px;

            &.sohu-multi-cover {
              flex-direction: column;
              width: 100%;
            }

            .sohu-cover-list {
              display: flex;
              flex-wrap: wrap;
              align-items: flex-start;
              gap: 12px;
            }

            .sohu-cover-item {
              border: 1px dashed #d9d9d9;
              border-radius: 6px;
              overflow: hidden;

              .cover-preview-mask span {
                cursor: pointer;
              }
            }
          }

          .article-cover-upload {
            :deep(.el-upload) {
              border: 1px dashed #d9d9d9;
              border-radius: 6px;
              cursor: pointer;
              overflow: hidden;
              transition: border-color 0.2s;
            }

            :deep(.el-upload:hover) {
              border-color: #409eff;
            }
          }

          .cover-plus-box,
          .cover-preview-box {
            width: 148px;
            height: 148px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #fafafa;
            color: #8c939d;
            position: relative;
          }

          .cover-preview-box {
            .cover-preview-img {
              width: 100%;
              height: 100%;
              object-fit: cover;
              display: block;
            }

            .cover-preview-mask {
              position: absolute;
              inset: 0;
              display: none;
              align-items: center;
              justify-content: center;
              background: rgba(0, 0, 0, 0.45);
              color: #fff;
              font-size: 13px;
            }

            &:hover .cover-preview-mask {
              display: flex;
            }
          }

          .cover-side-actions {
            display: flex;
            flex-direction: column;
            gap: 4px;
            padding-top: 4px;
          }

          .cover-tip {
            width: 100%;
            font-size: 12px;
            color: #909399;
            line-height: 1.5;
          }

          .cover-file-name {
            width: 100%;
            font-size: 12px;
            color: #606266;
          }
        }

        .work-statement-section {
          .work-statement-group {
            display: flex;
            flex-wrap: wrap;
            gap: 8px 18px;

            :deep(.el-radio) {
              margin-right: 0;
              height: auto;
              white-space: normal;
            }
          }
        }

        .product-section {
          .product-name-input,
          .product-link-input {
            margin-bottom: 5px;
          }
        }

        .video-upload {
          width: 100%;

          :deep(.el-upload-dragger) {
            width: 100%;
            height: 180px;
          }
        }

        .account-input {
          max-width: 400px;
        }

        .platform-buttons {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;

          .platform-btn {
            min-width: 80px;
          }
        }

        .title-input {
          max-width: 600px;
        }

        .optional-hint {
          margin-left: 4px;
          font-size: 12px;
          font-weight: normal;
          color: #909399;
        }

        .topic-display {
          display: flex;
          flex-direction: column;
          gap: 12px;

          .topic-actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
          }

          .selected-topics {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            min-height: 32px;

            .topic-tag {
              font-size: 14px;
            }
          }

          .select-topic-btn {
            align-self: flex-start;
          }
        }

        .schedule-controls {
          display: flex;
          flex-direction: column;
          gap: 15px;

          .schedule-settings {
            margin-top: 15px;
            padding: 15px;
            background-color: #f5f7fa;
            border-radius: 4px;

            .schedule-item {
              display: flex;
              align-items: center;
              margin-bottom: 15px;

              &:last-child {
                margin-bottom: 0;
              }

              .label {
                min-width: 120px;
                margin-right: 10px;
              }

              .el-time-select {
                margin-right: 10px;
              }

              .el-button {
                margin-left: 10px;
              }
            }
          }
        }

        .action-buttons {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          margin-top: 30px;
          padding-top: 20px;
          border-top: 1px solid #ebeef5;
        }

        .draft-section {
          margin: 20px 0;

          .draft-checkbox {
            display: block;
            margin: 10px 0;
          }
        }

        .original-section {
          margin: 10px 0 20px;

          .original-checkbox {
            display: block;
            margin: 10px 0;
          }
        }

        .ai-declaration-section {
          margin: 10px 0 20px;

          .ai-declaration-checkbox {
            display: block;
            margin: 10px 0;
          }
        }

        .bilibili-creation-section {
          margin: 10px 0 20px;

          h3 {
            margin-bottom: 10px;
          }

          .bilibili-creation-select {
            width: 100%;
            max-width: 360px;
          }

          .optional-hint {
            margin-top: 8px;
            font-size: 12px;
            color: #909399;
          }
        }

        .dry-run-section {
          margin: 10px 0 20px;

          .dry-run-checkbox {
            display: block;
            margin: 10px 0;
          }
        }
      }
    }
  }

  // 已上传文件列表样式
  .uploaded-files {
    margin-top: 20px;

    h4 {
      font-size: 16px;
      font-weight: 500;
      margin-bottom: 12px;
      color: #303133;
    }

    .file-list {
      display: flex;
      flex-direction: column;
      gap: 10px;

      .file-item {
        display: flex;
        align-items: center;
        padding: 10px 15px;
        background-color: #f5f7fa;
        border-radius: 4px;

        .el-link {
          margin-right: 10px;
          max-width: 300px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .file-size {
          color: #909399;
          font-size: 13px;
          margin-right: auto;
        }
      }
    }
  }

  // 添加话题弹窗样式
  .topic-dialog {
    .topic-dialog-content {
      .custom-topic-input {
        display: flex;
        gap: 12px;
        margin-bottom: 24px;

        .custom-input {
          flex: 1;
        }
      }

      .recommended-topics {
        h4 {
          margin: 0 0 16px 0;
          font-size: 16px;
          font-weight: 500;
          color: #303133;
        }

        .topic-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
          gap: 12px;

          .topic-btn {
            height: 36px;
            font-size: 14px;
            border-radius: 6px;
            min-width: 100px;
            padding: 0 12px;
            white-space: nowrap;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;

            &.el-button--primary {
              background-color: #409eff;
              border-color: #409eff;
              color: white;
            }
          }
        }
      }
    }

    .dialog-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
  }
}
</style>
<style src="../styles/publish-workbench.css"></style>

<style scoped>
.library-history-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:10px 0;color:#87909c;font-size:12px}.material-publication-marks{display:flex;flex-wrap:wrap;gap:5px;margin:5px 0}.material-has-history{border-left:3px solid #91bda1;padding-left:10px}.video-cover-upload.recommendation :deep(.el-upload){aspect-ratio:4 / 3}
</style>

<style>
.el-select-dropdown__item.episode-folder-option{height:auto;min-height:34px;display:flex;align-items:center;justify-content:space-between;gap:16px;padding-top:6px;padding-bottom:6px}.episode-folder-marks{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;max-width:65%}
#app .publish-center .file-item .video-item-actions .next-episode-action{color:#0f7a4a;border-color:#7fb398;background:#f2fbf6;font-weight:500}
#app .publish-center .file-item .video-item-actions .next-episode-action:hover{color:#fff;border-color:#0f7a4a;background:#0f7a4a}
</style>

<style>
.el-message-box.next-episode-card{width:360px!important;max-width:calc(100vw - 32px);padding:24px!important;border-radius:16px!important;box-sizing:border-box;box-shadow:0 18px 60px #00000020!important}.next-episode-card .el-message-box__header{padding:0 22px 16px 0}.next-episode-card .el-message-box__title{font-size:17px;line-height:1.5}.next-episode-card .el-message-box__content{padding:0}.next-episode-card .el-message-box__container{display:flex;align-items:flex-start;gap:10px}.next-episode-card .el-message-box__status{position:static!important;transform:none!important;flex-shrink:0;margin-top:3px;font-size:22px!important}.next-episode-card .el-message-box__message{padding:0!important;min-width:0;white-space:pre-line;font-size:13px;line-height:1.8;color:#606774}.next-episode-card .el-message-box__btns{display:flex;justify-content:flex-end;gap:10px;flex-wrap:wrap;padding:22px 0 0}.next-episode-card .el-message-box__btns .el-button{margin:0!important;height:36px;padding:0 16px;border-radius:7px}
</style>

<style scoped>
.automation-message{max-width:240px;font-size:12px;color:#7b8494;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
</style>
