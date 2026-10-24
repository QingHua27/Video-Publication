<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="name==='home'"><path d="m3 10 9-7 9 7v10H6V10"/><path d="M10 20v-7h4v7"/></template>
    <template v-else-if="name==='account'"><circle cx="12" cy="7" r="4"/><path d="M4 21v-3a8 8 0 0 1 16 0v3Z"/></template>
    <template v-else-if="name==='materials'"><path d="M6 3h9l4 4v14H6zM15 3v5h4"/><path d="m9 16 3-3 4 4M9 10h1"/></template>
    <template v-else-if="name==='publish'"><path d="m3 10 18-7-7 18-3-8-8-3ZM11 13 21 3"/></template>
    <template v-else-if="name==='data'"><rect x="4" y="11" width="3" height="10" rx="1"/><rect x="10.5" y="4" width="3" height="17" rx="1"/><rect x="17" y="8" width="3" height="13" rx="1"/></template>
    <template v-else-if="name==='exit'"><path d="M10 4H4v16h6M9 12h12m-4-4 4 4-4 4"/></template>
    <template v-else><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/></template>
  </svg>
</template>
<script setup>
defineProps({name:{type:String,required:true}})
</script>
