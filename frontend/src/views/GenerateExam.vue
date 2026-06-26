<template>
  <div class="container">
    <div class="card">
      <h2 class="card-title">生成试卷</h2>
      <p class="card-subtitle">选择教材和题型，系统将自动生成一份定制试卷</p>

      <div class="form-group">
        <label>选择教材</label>
        <select v-model="selectedKb" @change="loadKb">
          <option value="" disabled>— 请选择教材 —</option>
          <option v-for="e in kbList" :key="e.name" :value="e.name">{{ e.name }}（{{ e.char_count.toLocaleString() }} 字符）</option>
        </select>
        <div v-if="selectedKb" style="font-size:.8rem;color:var(--green);margin-top:.3rem;font-weight:500;">
          已加载「{{ selectedKb }}」— {{ source.length.toLocaleString() }} 字符
        </div>
      </div>

      <div class="form-group">
        <label>题目类型</label>
        <div class="type-grid">
          <div v-for="t in allTypes" :key="t.value"
            class="type-chip" :class="{active:types.includes(t.value)}"
            @click="toggleType(t.value)">
            <input type="checkbox" :checked="types.includes(t.value)">
            <span>{{ t.label }}</span>
          </div>
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>题目数量</label>
          <input type="number" v-model.number="count" min="1" max="50">
        </div>
      </div>

      <p v-if="err" class="err-msg">{{ err }}</p>
      <button class="btn btn-primary" @click="generate" :disabled="loading || !selectedKb || types.length===0">
        <span v-if="loading" class="spinner" style="width:16px;height:16px;"></span>
        {{ loading ? '生成中…' : '生成试卷' }}
      </button>
    </div>

    <div v-if="kbList.length" class="card" style="background:var(--bg);">
      <h3 class="card-title">教材列表</h3>
      <div v-for="e in kbList" :key="e.name" class="kb-item">
        <span class="name">{{ e.name }}</span>
        <span class="meta">{{ e.char_count.toLocaleString() }} 字符 · {{ e.chunks }} 块</span>
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

function toggleType(val) {
  const i = types.value.indexOf(val)
  if (i >= 0) types.value.splice(i, 1)
  else types.value.push(val)
}

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
    const paper = await generateExam({ kb_name: selectedKb.value, source_material: source.value, question_types: types.value, total_count: count.value })
    const exams = JSON.parse(localStorage.getItem('kt_exams') || '{}')
    exams[paper.id] = paper
    localStorage.setItem('kt_exams', JSON.stringify(exams))
    router.push(`/exam/${paper.id}`)
  } catch (e) { err.value = e.message }
  finally { loading.value = false }
}
</script>
