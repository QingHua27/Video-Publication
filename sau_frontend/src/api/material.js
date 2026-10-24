import { http } from '@/utils/request'

// 素材管理API
export const materialApi = {
  deleteSection: sectionId => http.post('/materialSections/delete',{sectionId},{headers:{'X-OmniPost-Local':'1'},silentError:true}),
  linkDirectory: (path,sectionId,kind) => http.post('/local/materials/directories',{path,sectionId,kind},{headers:{'X-OmniPost-Local':'1'},timeout:120000}),
  deleteFolderRecords: data => http.post('/local/materials/delete-folders',data,{headers:{'X-OmniPost-Local':'1'},silentError:true}),
  getSections: () => http.get('/materialSections'),
  createSection: name => http.post('/materialSections',{name},{headers:{'X-OmniPost-Local':'1'}}),
  moveFolders: data => http.post('/materialSections/move',data,{headers:{'X-OmniPost-Local':'1'},silentError:true}),
  pickLocal: kind => http.post('/local/materials/pick',{kind},{headers:{'X-OmniPost-Local':'1'},timeout:620000}),
  registerLocal: (paths,sectionId) => http.post('/local/materials/register',{paths,sectionId},{headers:{'X-OmniPost-Local':'1'}}),
  // 获取所有素材
  getAllMaterials: () => {
    return http.get('/getFiles')
  },
  
  // 上传素材
  uploadMaterial: (formData, onUploadProgress) => {
    // 使用http.upload方法，它已经配置了正确的Content-Type
    return http.upload('/uploadSave', formData, onUploadProgress)
  },
  
  // 删除素材
  deleteMaterial: (id) => {
    return http.get(`/deleteFile?id=${id}`)
  },
  
  // 下载素材
  downloadMaterial: (filePath) => {
    return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'}/getFile?filename=${encodeURIComponent(filePath)}&download=1`
  },
  
  // 获取素材预览URL
  getMaterialPreviewUrl: (filename) => {
    return `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5409'}/getFile?filename=${encodeURIComponent(filename)}`
  }
}
