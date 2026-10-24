const pathKey = value => String(value || '').replaceAll('\\','/').toLowerCase()
const parent = value => pathKey(value).split('/').slice(0,-1).join('/')
export const publicationLabels = {published:'已发布',submitted:'流程完成·待核对',pending:'发布中／待核对',needs_review:'结果待核对'}
export function materialPublications(material, records) {
  return records.filter(row => {
    if (!publicationLabels[row.status]) return false
    if (pathKey(row.source_path) === pathKey(material.file_path)) return true
    if (!material.episode_number || Number(row.episode) !== Number(material.episode_number)) return false
    if (material.section_id) return Number(row.material_section_id) === Number(material.section_id)
    return parent(material.file_path) !== '' && parent(row.source_path) === parent(material.file_path) && !row.material_section_id
  })
}
