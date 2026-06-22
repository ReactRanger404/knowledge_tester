<template>
  <div class="container">
    <div v-if="!paper" class="empty-state">
      <div class="icon">📄</div>
      <h3>试卷不存在</h3>
      <router-link to="/generate" class="btn btn-primary">去生成</router-link>
    </div>

    <template v-else>
      <div class="card" style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <h2>{{ paper.title }}</h2>
          <span style="color:var(--gray-500);font-size:.85rem;">{{ paper.questions.length }} 题 · 已答 {{ answered }}/{{ paper.questions.length }}</span>
        </div>
        <button class="btn btn-success" @click="submit" :disabled="submitting">{{ submitting ? '提交中…' : '📤 提交' }}</button>
      </div>

      <div v-for="(q, i) in paper.questions" :key="i" class="question">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
          <span class="question-label">第{{ i+1 }}题 · <span :class="'tag '+typeTag(q.type)">{{ typeLabel(q.type) }}</span></span>
          <span class="tag" style="background:var(--gray-100);color:var(--gray-500);">{{ diffLabel(q.difficulty) }}</span>
        </div>
        <div class="question-text">{{ q.stem }}</div>

        <!-- 选择题 -->
        <div v-if="q.type==='choice'" class="options">
          <div v-for="(opt,oi) in q.options" :key="oi" class="option" :class="{selected:answers[i]===String(oi)}" @click="answers[i]=String(oi)">
            <span class="option-letter">{{ 'ABCDEFGH'[oi] }}</span><span>{{ opt }}</span>
          </div>
        </div>

        <!-- 判断题 -->
        <div v-if="q.type==='judgment'" class="options" style="flex-direction:row;">
          <div class="option" :class="{selected:answers[i]==='true'}" @click="answers[i]='true'" style="flex:1"><span class="option-letter">✓</span> 正确</div>
          <div class="option" :class="{selected:answers[i]==='false'}" @click="answers[i]='false'" style="flex:1"><span class="option-letter">✗</span> 错误</div>
        </div>

        <!-- 填空/简答/论述 -->
        <textarea v-if="q.type==='fill_blank'||q.type==='short_answer'||q.type==='essay'"
          v-model="answers[i]" :placeholder="'输入'+(q.type==='fill_blank'?'答案':'回答')+'…'"
          style="width:100%;padding:.75rem;border:1px solid var(--gray-300);border-radius:8px;font-family:inherit;font-size:1rem;"
          :rows="q.type==='essay'?6:2">
        </textarea>
      </div>

      <div style="text-align:center;padding:2rem 0;">
        <button class="btn btn-success" @click="submit" :disabled="submitting" style="font-size:1.1rem;padding:1rem 3rem;">
          {{ submitting ? '提交中…' : '📤 提交全部答案' }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { submitAnswers } from '../api.js'

const route = useRoute(); const router = useRouter()
const paper = ref(null); const answers = ref({}); const submitting = ref(false)

onMounted(() => {
  const exams = JSON.parse(localStorage.getItem('kt_exams') || '{}')
  paper.value = exams[route.params.id] || null
})

const answered = computed(() => paper.value ? paper.value.questions.filter((_,i)=>answers.value[i]!==undefined && answers.value[i]!=='').length : 0)

function typeLabel(t) { return {choice:'选择题',judgment:'判断题',fill_blank:'填空题',short_answer:'简答题',essay:'论述题'}[t]||t }
function typeTag(t) { return {choice:'tag-choice',judgment:'tag-judgment',fill_blank:'tag-fill',short_answer:'tag-short',essay:'tag-essay'}[t]||'' }
function diffLabel(d) { return {easy:'简单',medium:'中等',hard:'困难'}[d]||d }

async function submit() {
  submitting.value = true
  const ans = []
  for (let i = 0; i < (paper.value?.questions?.length||0); i++) {
    ans.push({ exam_id: route.params.id, question_index: i, question_type: paper.value.questions[i].type, answer_text: answers.value[i]||'' })
  }
  try {
    const result = await submitAnswers(route.params.id, ans)
    const results = JSON.parse(localStorage.getItem('kt_results')||'{}')
    results[route.params.id] = result
    localStorage.setItem('kt_results', JSON.stringify(results))
    router.push(`/results/${route.params.id}`)
  } finally { submitting.value = false }
}
</script>
