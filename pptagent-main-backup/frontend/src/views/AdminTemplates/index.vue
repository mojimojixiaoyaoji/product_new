<template>
  <div class="admin-templates-page">
    <!-- Passkey Gate -->
    <div v-if="!isAuthenticated" class="passkey-gate">
      <div class="passkey-card">
        <h2>模板管理</h2>
        <p>输入密码访问</p>
        <input
          v-model="passkeyInput"
          type="password"
          placeholder="输入密码..."
          @keyup.enter="verifyPasskey"
        />
        <button @click="verifyPasskey">解锁</button>
        <p v-if="authError" class="error">{{ authError }}</p>
      </div>
    </div>

    <!-- Main Content -->
    <div v-else class="admin-content">
      <div class="header">
        <div class="header-left">
          <a href="/" class="logo-link">
            <span class="logo-icon">🏠</span>
            <span class="logo-text">PPT智能体</span>
          </a>
          <div class="title-section">
            <h1>模板管理</h1>
            <span class="template-count" v-if="templates.length > 0">
              共 {{ templates.length }} 个模板
            </span>
          </div>
        </div>
        <div class="header-actions">
          <button class="icon-btn" @click="fetchTemplates" title="刷新">
            <span>🔄</span>
          </button>
          <ThemeToggle />
          <button class="create-btn" @click="openCreateDialog">
            <span>✨</span> 创建模板
          </button>
          <button class="logout-btn" @click="logout">登出</button>
        </div>
      </div>

      <!-- Templates Grid -->
      <div class="templates-grid">
        <div v-for="template in templates" :key="template.id" class="template-card">
          <div class="cover-preview">
            <img v-if="template.cover" :src="template.cover" :alt="template.name" />
            <div v-else class="no-cover">No Cover</div>
          </div>
          <div class="template-info">
            <h4>{{ template.name }}</h4>
            <p class="meta">ID: {{ template.id }}</p>
            <p class="meta">创建: {{ template.created_at || 'N/A' }}</p>
            <p class="meta">更新: {{ template.updated_at || 'N/A' }}</p>
          </div>
          <div class="template-actions">
            <button class="edit-btn" @click="openEditModal(template)">编辑</button>
            <button class="delete-btn" @click="deleteTemplate(template.id)">删除</button>
          </div>
        </div>
      </div>

      <p v-if="templates.length === 0" class="empty">No templates yet</p>
    </div>

    <!-- Create Dialog -->
    <div v-if="showCreateDialog" class="modal-overlay" @click.self="closeCreateDialog">
      <div class="modal create-modal">
        <h3>✨ 创建模板</h3>
        <div class="form-stack">
          <div class="form-row">
            <label>名称</label>
            <div class="input-wrapper">
              <input v-model="newTemplate.name" type="text" placeholder="输入模板名称..." :disabled="isCreating" />
            </div>
          </div>
          <div class="form-row">
            <label>JSON 文件</label>
            <div class="file-drop" :class="{ 'has-file': newTemplate.jsonFile }" @click="isCreating ? null : triggerJsonUpload()">
              <input ref="jsonInput" type="file" accept=".json" @change="handleTemplateFileChange" @click.stop :disabled="isCreating" />
              <span v-if="!newTemplate.jsonFile" class="drop-hint">
                <span class="icon">📄</span>
                <span>点击上传 JSON</span>
              </span>
              <span v-else class="file-info">
                <span class="icon">✅</span>
                <span class="filename">{{ newTemplate.jsonFile.name }}</span>
              </span>
            </div>
          </div>
          <div class="form-row">
            <label>封面图片</label>
            <div class="file-drop" :class="{ 'has-file': newTemplate.coverFile }" @click="isCreating ? null : triggerCoverUpload()">
              <input ref="coverInput" type="file" accept="image/*" @change="handleCoverFileChange" @click.stop :disabled="isCreating" />
              <span v-if="!newTemplate.coverFile" class="drop-hint">
                <span class="icon">🖼️</span>
                <span>点击上传封面</span>
              </span>
              <span v-else class="file-info">
                <span class="icon">✅</span>
                <span class="filename">{{ newTemplate.coverFile.name }}</span>
              </span>
            </div>
          </div>
        </div>
        <div class="cover-preview-create" v-if="newTemplate.coverPreviewUrl">
          <img :src="newTemplate.coverPreviewUrl" alt="cover preview" />
        </div>
        <p v-if="createError" class="error">{{ createError }}</p>
        <div class="modal-actions">
          <button @click="closeCreateDialog" :disabled="isCreating">取消</button>
          <button @click="handleCreate" :disabled="!canCreate || isCreating">
            <span v-if="isCreating" class="spinner"></span>
            <span v-else>创建</span>
          </button>
        </div>
        <!-- Upload Loading Overlay -->
        <div v-if="isCreating" class="upload-overlay">
          <div class="upload-progress">
            <div class="spinner-large"></div>
            <p>正在上传...</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="showEditModal" class="modal-overlay" @click.self="closeEditModal">
      <div class="modal edit-modal">
        <h3>✨ 编辑模板</h3>
        <div class="form-stack">
          <div class="form-row">
            <label>名称</label>
            <div class="input-wrapper">
              <input v-model="editData.name" type="text" placeholder="输入模板名称..." :disabled="isUpdating" />
            </div>
          </div>
          <div class="form-row">
            <label>JSON 文件</label>
            <div class="file-drop" :class="{ 'has-file': editData.jsonFile }" @click="isUpdating ? null : triggerEditJsonUpload()">
              <input ref="editJsonInput" type="file" accept=".json" @change="handleEditTemplateFileChange" @click.stop :disabled="isUpdating" />
              <span v-if="!editData.jsonFile" class="drop-hint">
                <span class="icon">📄</span>
                <span>点击替换 JSON</span>
              </span>
              <span v-else class="file-info">
                <span class="icon">✅</span>
                <span class="filename">{{ (editData.jsonFile as File).name }}</span>
              </span>
            </div>
          </div>
          <div class="form-row">
            <label>封面图片</label>
            <div class="file-drop" :class="{ 'has-file': editData.coverFile }" @click="isUpdating ? null : triggerEditCoverUpload()">
              <input ref="editCoverInput" type="file" accept="image/*" @change="handleEditCoverFileChange" @click.stop :disabled="isUpdating" />
              <span v-if="!editData.coverFile" class="drop-hint">
                <span class="icon">🖼️</span>
                <span>点击替换封面</span>
              </span>
              <span v-else class="file-info">
                <span class="icon">✅</span>
                <span class="filename">{{ (editData.coverFile as File).name }}</span>
              </span>
            </div>
          </div>
        </div>
        <div class="cover-preview-edit" v-if="editData.coverUrl">
          <img :src="editData.coverUrl" alt="cover preview" />
        </div>
        <p v-if="editError" class="error">{{ editError }}</p>
        <div class="modal-actions">
          <button @click="closeEditModal" :disabled="isUpdating">取消</button>
          <button @click="updateTemplate" :disabled="!editData.name || isUpdating">
            <span v-if="isUpdating" class="spinner"></span>
            <span v-else>保存</span>
          </button>
        </div>
        <!-- Upload Loading Overlay -->
        <div v-if="isUpdating" class="upload-overlay">
          <div class="upload-progress">
            <div class="spinner-large"></div>
            <p>正在更新...</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteDialog" class="modal-overlay" @click.self="cancelDelete">
      <div class="modal delete-modal">
        <div class="delete-icon">⚠️</div>
        <h3>确认删除</h3>
        <p>确定要删除模板 "<strong>{{ deleteTarget.name }}</strong>" 吗？</p>
        <p class="delete-hint">此操作不可撤销</p>
        <div class="modal-actions">
          <button @click="cancelDelete">取消</button>
          <button class="delete-confirm-btn" @click="confirmDelete">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue'
import message from '@/utils/message'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { useThemeStore } from '@/store/theme'

const themeStore = useThemeStore()

const SERVER_URL = '/api'
const PASSKEY_STORAGE_KEY = 'admin_templates_passkey'
const PASSKEY_EXPIRY_DAYS = 365

// Auth state
const isAuthenticated = ref(false)
const passkeyInput = ref('')
const authError = ref('')

// Check saved passkey on mount
onMounted(() => {
  const saved = localStorage.getItem(PASSKEY_STORAGE_KEY)
  if (saved) {
    try {
      const { passkey, expiry } = JSON.parse(saved)
      if (expiry > Date.now()) {
        passkeyInput.value = passkey
        verifyPasskey()
      } else {
        localStorage.removeItem(PASSKEY_STORAGE_KEY)
      }
    } catch {
      localStorage.removeItem(PASSKEY_STORAGE_KEY)
    }
  }
})

interface Template {
  id: string
  name: string
  cover: string
  json_filename: string
  cover_filename: string
  created_at: string
  updated_at: string
}

// Templates list
const templates = ref<Template[]>([])

// Create form state
const newTemplate = ref({
  name: '',
  jsonFile: null as File | null,
  coverFile: null as File | null,
  coverPreviewUrl: ''
})
const createError = ref('')
const showCreateDialog = ref(false)
const isCreating = ref(false)

// Edit modal state
const showEditModal = ref(false)
const editData = ref({
  id: '',
  name: '',
  jsonFile: null as File | null,
  coverFile: null as File | null,
  coverUrl: ''
})
const editError = ref('')
const isUpdating = ref(false)

// Delete confirmation modal state
const showDeleteDialog = ref(false)
const deleteTarget = ref({ id: '', name: '' })

const canCreate = computed(() => {
  return newTemplate.value.name && newTemplate.value.jsonFile
})

const passkeyHeaders = computed(() => ({
  'X-Passkey': passkeyInput.value
}))

const jsonInput = ref<HTMLInputElement | null>(null)
const coverInput = ref<HTMLInputElement | null>(null)
const editJsonInput = ref<HTMLInputElement | null>(null)
const editCoverInput = ref<HTMLInputElement | null>(null)

function triggerJsonUpload() {
  jsonInput.value?.click()
}

function triggerCoverUpload() {
  coverInput.value?.click()
}

function triggerEditJsonUpload() {
  editJsonInput.value?.click()
}

function triggerEditCoverUpload() {
  editCoverInput.value?.click()
}

function logout() {
  isAuthenticated.value = false
  passkeyInput.value = ''
  localStorage.removeItem(PASSKEY_STORAGE_KEY)
}

function openCreateDialog() {
  newTemplate.value = { name: '', jsonFile: null, coverFile: null, coverPreviewUrl: '' }
  createError.value = ''
  showCreateDialog.value = true
}

function closeCreateDialog() {
  showCreateDialog.value = false
}

async function handleCreate() {
  createError.value = ''
  isCreating.value = true

  if (!newTemplate.value.name || !newTemplate.value.jsonFile) {
    createError.value = '名称和JSON文件不能为空'
    isCreating.value = false
    return
  }

  const formData = new FormData()
  formData.append('name', newTemplate.value.name)
  formData.append('template_file', newTemplate.value.jsonFile)
  if (newTemplate.value.coverFile) {
    formData.append('cover_file', newTemplate.value.coverFile)
  }

  try {
    const res = await fetch(`${SERVER_URL}/admin/templates`, {
      method: 'POST',
      headers: { 'X-Passkey': passkeyInput.value },
      body: formData
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || '创建失败')
    }
    message.success('✨ 模板创建成功')
    closeCreateDialog()
    await fetchTemplates()
  } catch (err: any) {
    createError.value = err.message || '创建失败'
  } finally {
    isCreating.value = false
  }
}

async function verifyPasskey() {
  authError.value = ''
  try {
    const res = await fetch(`${SERVER_URL}/admin/templates`, {
      headers: { 'X-Passkey': passkeyInput.value }
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Invalid passkey')
    }
    const data = await res.json()
    templates.value = data.data
    isAuthenticated.value = true
    // Save passkey to localStorage for 1 year
    const expiry = Date.now() + PASSKEY_EXPIRY_DAYS * 24 * 60 * 60 * 1000
    localStorage.setItem(PASSKEY_STORAGE_KEY, JSON.stringify({ passkey: passkeyInput.value, expiry }))
  } catch (err: any) {
    authError.value = err.message || 'Invalid passkey'
  }
}

async function fetchTemplates() {
  try {
    console.log('fetchTemplates called, current templates:', templates.value)
    const res = await fetch(`${SERVER_URL}/admin/templates`, {
      headers: { 'X-Passkey': passkeyInput.value }
    })
    const data = await res.json()
    console.log('fetchTemplates API response:', data)
    console.log('fetchTemplates data.data:', data.data)
    templates.value = data.data || []
    console.log('fetchTemplates after set, templates:', templates.value)
  } catch {
    message.error('Failed to fetch templates')
  }
}

function handleTemplateFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    newTemplate.value.jsonFile = input.files[0]
  }
}

function handleCoverFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    newTemplate.value.coverFile = input.files[0]
    newTemplate.value.coverPreviewUrl = URL.createObjectURL(input.files[0])
  }
}


function openEditModal(template: Template) {
  editData.value = {
    id: template.id,
    name: template.name,
    jsonFile: null,
    coverFile: null,
    coverUrl: template.cover || ''
  }
  editError.value = ''
  showEditModal.value = true
}

function closeEditModal() {
  showEditModal.value = false
}

function handleEditTemplateFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    editData.value.jsonFile = input.files[0]
  }
}

function handleEditCoverFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    editData.value.coverFile = input.files[0]
    editData.value.coverUrl = URL.createObjectURL(input.files[0])
  }
}

async function updateTemplate() {
  editError.value = ''
  isUpdating.value = true

  const formData = new FormData()
  formData.append('name', editData.value.name)
  if (editData.value.jsonFile) {
    formData.append('template_file', editData.value.jsonFile)
  }
  if (editData.value.coverFile) {
    formData.append('cover_file', editData.value.coverFile)
  }

  try {
    const res = await fetch(`${SERVER_URL}/admin/templates/${editData.value.id}`, {
      method: 'PUT',
      headers: { 'X-Passkey': passkeyInput.value },
      body: formData
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to update template')
    }
    closeEditModal()
    // 清空编辑数据
    editData.value = { id: '', name: '', jsonFile: null, coverFile: null, coverUrl: '' }
    // 重新获取所有模板确保数据最新
    await fetchTemplates()
    message.success('✨ 模板已更新')
  } catch (err: any) {
    editError.value = err.message || 'Failed to update template'
  } finally {
    isUpdating.value = false
  }
}

async function deleteTemplate(id: string) {
  const template = templates.value.find(t => t.id === id)
  if (!template) return
  deleteTarget.value = { id, name: template.name }
  showDeleteDialog.value = true
}

async function confirmDelete() {
  const id = deleteTarget.value.id
  try {
    const res = await fetch(`${SERVER_URL}/admin/templates/${id}`, {
      method: 'DELETE',
      headers: { 'X-Passkey': passkeyInput.value }
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to delete template')
    }
    showDeleteDialog.value = false
    fetchTemplates()
    message.success('Template deleted')
  } catch (err: any) {
    message.error(err.message || 'Failed to delete template')
  }
}

function cancelDelete() {
  showDeleteDialog.value = false
  deleteTarget.value = { id: '', name: '' }
}
</script>

<style lang="scss" scoped>
// Theme CSS Variables
.admin-templates-page {
  --bg-primary: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
  --bg-secondary: linear-gradient(145deg, #1e1e3f, #252550);
  --bg-card: #1e1e3f;
  --bg-input: #0f0f23;
  --bg-hover: rgba(215, 0, 15, 0.1);
  --bg-overlay: rgba(0, 0, 0, 0.5);
  --border-color: #2d3748;
  --border-dashed: #2d3748;
  --text-primary: #fff;
  --text-secondary: #a0aec0;
  --text-muted: #718096;
  --text-placeholder: #4a5568;
  --accent-primary: #D7000F;
  --accent-secondary: #ff4757;
  --accent-success: #10b981;
  --accent-error: #ff6b6b;
  --shadow-card: 0 4px 20px rgba(0, 0, 0, 0.3);
  --shadow-card-hover: 0 8px 30px rgba(215, 0, 15, 0.2);
  --shadow-modal: 0 8px 32px rgba(0, 0, 0, 0.5);
  --card-radius: 16px;
  --btn-radius: 8px;
  --modal-radius: 20px;

  min-height: 100vh;
  background: var(--bg-primary);
  padding: 20px;
}

[data-theme="light"] .admin-templates-page {
  --bg-primary: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 50%, #d1d5db 100%);
  --bg-secondary: linear-gradient(145deg, #ffffff, #f8f9fa);
  --bg-card: #ffffff;
  --bg-input: #f7f8fa;
  --bg-hover: rgba(215, 0, 15, 0.05);
  --bg-overlay: rgba(0, 0, 0, 0.3);
  --border-color: #e2e8f0;
  --border-dashed: #cbd5e0;
  --text-primary: #1a202c;
  --text-secondary: #4a5568;
  --text-muted: #a0aec0;
  --text-placeholder: #a0aec0;
  --accent-primary: #D7000F;
  --accent-secondary: #ff4757;
  --accent-success: #10b981;
  --accent-error: #e53e3e;
  --shadow-card: 0 4px 20px rgba(0, 0, 0, 0.08);
  --shadow-card-hover: 0 8px 30px rgba(215, 0, 15, 0.15);
  --shadow-modal: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.passkey-gate {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;

  .passkey-card {
    background: var(--bg-card);
    padding: 40px;
    border-radius: 12px;
    box-shadow: var(--shadow-modal);
    text-align: center;

    h2 {
      margin-bottom: 8px;
      color: var(--text-primary);
    }

    p {
      color: var(--text-secondary);
      margin-bottom: 20px;
    }

    input {
      display: block;
      width: 100%;
      padding: 12px;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      margin-bottom: 16px;
      font-size: 16px;
      background: var(--bg-input);
      color: var(--text-primary);

      &:focus {
        outline: none;
        border-color: var(--accent-primary);
      }
    }

    button {
      background: var(--accent-primary);
      color: white;
      border: none;
      padding: 12px 32px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 16px;

      &:hover {
        opacity: 0.9;
      }
    }

    .error {
      color: var(--accent-error);
      margin-top: 12px;
    }
  }
}

.admin-content {
  max-width: 1200px;
  margin: 0 auto;

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 16px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 20px;
    }

    .logo-link {
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      padding: 8px 12px;
      border-radius: 8px;
      transition: background 0.3s;

      &:hover {
        background: var(--bg-hover);
      }

      .logo-icon {
        font-size: 20px;
      }

      .logo-text {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .title-section {
      display: flex;
      align-items: baseline;
      gap: 12px;

      h1 {
        margin: 0;
        color: var(--text-primary);
        font-size: 24px;
        font-weight: 600;
      }

      .template-count {
        font-size: 13px;
        color: var(--text-muted);
      }
    }

    .header-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .icon-btn {
      background: var(--bg-input);
      border: 1px solid var(--border-color);
      padding: 8px 12px;
      border-radius: var(--btn-radius);
      cursor: pointer;
      transition: all 0.3s;

      &:hover {
        background: var(--bg-hover);
        border-color: var(--accent-primary);
      }
    }

    .create-btn {
      background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: var(--btn-radius);
      cursor: pointer;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.3s;
      box-shadow: 0 4px 15px rgba(215, 0, 15, 0.3);

      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(215, 0, 15, 0.4);
      }
    }

    .logout-btn {
      background: var(--bg-input);
      color: var(--text-secondary);
      border: 1px solid var(--border-color);
      padding: 10px 20px;
      border-radius: var(--btn-radius);
      cursor: pointer;
      transition: all 0.3s;

      &:hover {
        background: var(--bg-hover);
        border-color: var(--accent-primary);
        color: var(--text-primary);
      }
    }
  }
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 16px;

  .form-row {
    display: flex;
    align-items: center;
    gap: 16px;

    > label {
      flex: 0 0 100px;
      color: var(--text-secondary);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    &.form-row-btn {
      justify-content: flex-end;
    }
  }

  .input-wrapper {
    flex: 1;

    input {
      width: 100%;
      padding: 12px 16px;
      border: 2px solid var(--border-color);
      border-radius: 10px;
      background: var(--bg-input);
      color: var(--text-primary);
      font-size: 14px;
      transition: all 0.3s;
      box-sizing: border-box;

      &::placeholder {
        color: var(--text-placeholder);
      }

      &:focus {
        outline: none;
        border-color: var(--accent-primary);
        box-shadow: 0 0 15px rgba(215, 0, 15, 0.3);
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
    }
  }

  .file-drop {
    flex: 1;
    position: relative;
    padding: 12px 16px;
    border: 2px dashed var(--border-dashed);
    border-radius: 10px;
    background: var(--bg-input);
    text-align: center;
    cursor: pointer;
    transition: all 0.3s;
    box-sizing: border-box;

    input[type="file"] {
      display: none;
    }

    .drop-hint {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      color: var(--text-placeholder);
      font-size: 13px;

      .icon {
        font-size: 18px;
      }
    }

    .file-info {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      color: var(--accent-success);
      font-size: 13px;

      .icon {
        font-size: 16px;
      }

      .filename {
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    &:hover {
      border-color: var(--accent-primary);
      background: var(--bg-hover);
    }

    &.has-file {
      border-color: var(--accent-success);
      border-style: solid;
    }
  }
}

.cover-preview-create {
  width: 100%;
  height: 100px;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 16px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.template-card {
  background: var(--bg-secondary);
  border-radius: var(--card-radius);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  transition: all 0.3s;

  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-card-hover);
  }

  .cover-preview {
    height: 160px;
    background: var(--bg-input);
    display: flex;
    align-items: center;
    justify-content: center;
    border-bottom: 1px solid var(--border-color);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .no-cover {
      color: var(--text-muted);
      font-size: 14px;
    }
  }

  .template-info {
    padding: 16px;

    h4 {
      margin: 0 0 8px;
      color: var(--text-primary);
      font-size: 16px;
    }

    .meta {
      font-size: 11px;
      color: var(--text-muted);
      margin: 4px 0;
    }
  }

  .template-actions {
    padding: 0 16px 16px;
    display: flex;
    gap: 8px;

    button {
      flex: 1;
      padding: 8px;
      border: none;
      border-radius: 8px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
      transition: all 0.3s;
    }

    .edit-btn {
      background: linear-gradient(135deg, #3b82f6, #60a5fa);
      color: white;

      &:hover {
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
      }
    }

    .delete-btn {
      background: linear-gradient(135deg, #ef4444, #f87171);
      color: white;

      &:hover {
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
      }
    }
  }
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 40px;
  font-size: 16px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  position: relative;
  background: var(--bg-secondary);
  padding: 32px;
  border-radius: var(--modal-radius);
  width: 90%;
  max-width: 480px;
  box-shadow: var(--shadow-modal);

  h3 {
    margin-bottom: 20px;
    color: var(--text-primary);
  }

  input[type="text"] {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid var(--border-color);
    border-radius: 10px;
    margin-bottom: 16px;
    box-sizing: border-box;
    background: var(--bg-input);
    color: var(--text-primary);
    font-size: 14px;

    &:focus {
      outline: none;
      border-color: var(--accent-primary);
    }
  }

  .file-label {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: var(--bg-input);
    border: 2px dashed var(--border-dashed);
    border-radius: 10px;
    cursor: pointer;
    margin-bottom: 12px;
    color: var(--text-secondary);
    transition: all 0.3s;

    input[type="file"] {
      display: none;
    }

    &:hover {
      border-color: var(--accent-primary);
      color: var(--text-primary);
    }

    &.disabled {
      opacity: 0.5;
      cursor: not-allowed;
      pointer-events: none;
    }
  }

  .cover-preview-edit {
    width: 100%;
    height: 120px;
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 16px;
    background: var(--bg-input);
    border: 1px solid var(--border-color);

    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
  }

  .file-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;

    .file-label {
      margin-bottom: 0;
      flex: 1;
    }

    .file-name {
      font-size: 12px;
      color: var(--accent-success);
      max-width: 150px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .file-name-hint {
      font-size: 12px;
      color: var(--text-placeholder);
    }
  }

  .modal-actions {
    display: flex;
    gap: 12px;
    margin-top: 24px;

    button {
      flex: 1;
      padding: 12px;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.3s;

      &:first-child {
        background: var(--bg-input);
        color: var(--text-secondary);
        border: 1px solid var(--border-color);

        &:hover {
          background: var(--bg-hover);
          color: var(--text-primary);
        }
      }

      &:last-child {
        background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
        color: white;
        box-shadow: 0 4px 15px rgba(215, 0, 15, 0.3);

        &:disabled {
          background: var(--border-color);
          color: var(--text-placeholder);
          box-shadow: none;
        }

        &:hover:not(:disabled) {
          box-shadow: 0 6px 20px rgba(215, 0, 15, 0.5);
        }
      }
    }
  }

  .error {
    color: var(--accent-error);
    margin-top: 12px;
  }

  .success {
    color: var(--accent-success);
    margin-top: 12px;
  }
}

.upload-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--modal-radius);
  z-index: 10;

  .upload-progress {
    text-align: center;
    color: #fff;

    p {
      margin-top: 12px;
      font-size: 14px;
    }
  }
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-large {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.delete-modal {
  text-align: center;
  max-width: 400px;

  .delete-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  h3 {
    margin-bottom: 12px;
    color: var(--text-primary);
  }

  p {
    color: var(--text-secondary);
    margin-bottom: 8px;

    strong {
      color: var(--text-primary);
    }
  }

  .delete-hint {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 24px;
  }

  .delete-confirm-btn {
    background: linear-gradient(135deg, #ef4444, #f87171) !important;
    box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3) !important;

    &:hover {
      box-shadow: 0 6px 20px rgba(239, 68, 68, 0.5) !important;
    }
  }
}
</style>
