export function publishBusyState(tab) {
  const running=Boolean(tab.publishing || tab.preflighting) || (tab.destinationResults || []).some(result=>['queued','running'].includes(result.status))
  const waiting=(tab.destinationResults || []).some(result=>result.status==='awaiting_confirmation')
  return {disabled:running || waiting,loading:running,label:tab.preflighting ? '检查素材中，请稍候…' : running ? '发布中，请稍候…' : waiting ? '等待任务确认…' : `提交到 ${tab.selectedAccounts.length} 个账号`}
}
