<template>
  <div class="container">
    <div class="card">
      <h2 class="card-title">📝 生成试卷</h2>

      <!-- 知识库选择 -->
      <div class="form-group">
        <label>选择教材 <span style="color:var(--gray-500);font-weight:400;">（从知识库加载）</span></label>
        <div style="display:flex;gap:.5rem;">
          <select v-model="selectedKb" @change="loadKb" style="flex:1;padding:.75rem;border:1px solid var(--gray-300);border-radius:8px;font-size:1rem;">
            <option value="">-- 不使用知识库，手动输入 --</option>
            <option v-for="e in kbList" :key="e.name" :value="e.name">{{ e.name }} ({{ e.char_count }} 字符)</option>
          </select>
          <button class="btn btn-sm btn-secondary" @click="fetchKbList">🔄</button>
        </div>
      </div>

      <div class="form-group">
        <label>原始资料</label>
        <textarea v-model="source" placeholder="输入知识点内容或文档文本..." :disabled="!!selectedKb"></textarea>
        <div v-if="selectedKb" style="font-size:.85rem;color:var(--green);margin-top:.25rem;">✅ 已加载「{{ selectedKb }}」</div>
      </div>

      <div class="form-group">
        <label>题目类型</label>
        <div class="checkbox-group">
          <label v-for="t in allTypes" :key="t.value">
            <input type="checkbox" :value="t.value" v-model="types">
            <span>{{ t.label }}</span>
          </label>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>题目数量</label>
          <input type="number" v-model.number="count" min="1" max="50">
        </div>
      </div>

      <p v-if="err" style="color:var(--red)">{{ err }}</p>
      <button class="btn btn-primary" @click="generate" :disabled="loading || !source.trim() || types.length===0">
        <span v-if="loading" class="spinner" style="width:16px;height:16px;"></span>
        {{ loading ? '生成中…' : '🚀 生成试卷' }}
      </button>
    </div>

    <div v-if="kbList.length" class="card" style="background:var(--gray-50);">
      <h3 class="card-title">📚 知识库</h3>
      <div v-for="e in kbList" :key="e.name" style="padding:.5rem 0;border-bottom:1px solid var(--gray-200);display:flex;justify-content:space-between;align-items:center;">
        <span>{{ e.name }}</span>
        <span style="color:var(--gray-500);font-size:.85rem;">{{ e.char_count }} 字符 · {{ e.pages }} 页</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { generateExam } from '../api.js'

const router = useRouter()
const source = ref('')
const selectedKb = ref('')
const kbList = ref([])
const types = ref(['choice', 'judgment'])
const count = ref(5)
const loading = ref(false)
const err = ref('')
const allTypes = [
  { value: 'choice', label: '选择题' },
  { value: 'judgment', label: '判断题' },
  { value: 'fill_blank', label: '填空题' },
  { value: 'short_answer', label: '简答题' },
  { value: 'essay', label: '论述题' },
]

onMounted(fetchKbList)

async function fetchKbList() {
  try {
    const r = await fetch('/api/kb')
    kbList.value = await r.json()
  } catch {}
}

async function loadKb() {
  if (!selectedKb.value) { source.value = ''; return }
  try {
    const r = await fetch(`/api/kb/${selectedKb.value}?preview=false`)
    const data = await r.json()
    source.value = data.text || ''
  } catch {}
}

async function generate() {
  loading.value = true; err.value = ''
  try {
    const body = { source_material: source.value, question_types: types.value, total_count: count.value }
    if (selectedKb.value) body.kb_name = selectedKb.value
    const paper = await generateExam(body)
    const exams = JSON.parse(localStorage.getItem('kt_exams') || '{}')
    exams[paper.id] = paper
    localStorage.setItem('kt_exams', JSON.stringify(exams))
    router.push(`/exam/${paper.id}`)
  } catch (e) { err.value = e.message }
  finally { loading.value = false }
}
</script>
