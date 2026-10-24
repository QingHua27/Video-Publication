<template>
 <button class="theme-navigation-button" type="button" aria-label="切换主题" :title="`当前主题：${current.name}`" @click="visible=true">
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1-3.7c-.7-.4-.4-1.6.5-1.6H17a4 4 0 0 0 4-4A9 9 0 0 0 12 3Z"/><circle cx="7.5" cy="10" r=".8"/><circle cx="11" cy="6.8" r=".8"/><circle cx="16" cy="8" r=".8"/></svg>
  <span v-if="!collapsed">主题外观</span>
 </button>
 <el-dialog v-model="visible" title="主题外观" width="640px" class="theme-picker-dialog" append-to-body top="8vh">
  <p class="theme-picker-intro">选择适合你的创作空间，主题会自动保存。</p>
  <div class="theme-choice-grid"><button v-for="theme in themes" :key="theme.id" type="button" class="theme-choice" :class="{'is-selected':modelValue===theme.id}" :aria-pressed="modelValue===theme.id" @click="select(theme.id)">
   <div class="theme-preview" :class="`preview-${theme.preview}`" :style="{'--preview-surface':theme.surface,'--preview-accent':theme.accent}" aria-hidden="true"><div class="preview-navigation"><i/><i/><i/></div><div class="preview-content"><i/><div><i/><i/></div></div><img v-if="theme.artwork" :src="theme.artwork" alt=""/></div>
   <div class="theme-choice-title"><strong>{{ theme.name }}</strong><span v-if="modelValue===theme.id" class="theme-selected-mark">✓ 已启用</span></div><p>{{ theme.description }}</p>
  </button></div>
  <template #footer><el-button @click="visible=false">完成</el-button></template>
 </el-dialog>
</template>
<script setup>
import {ref,computed} from 'vue'
import {themes} from '@/utils/themes.mjs'
const props=defineProps({modelValue:{type:String,required:true},collapsed:Boolean})
const emit=defineEmits(['update:modelValue'])
const visible=ref(false)
const current=computed(()=>themes.find(theme=>theme.id===props.modelValue)||themes[0])
const select=id=>emit('update:modelValue',id)
</script>
