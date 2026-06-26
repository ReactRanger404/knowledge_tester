<template>
  <div class="container container-wide">
    <div v-if="!paper" class="empty-state">
      <div class="icon">📋</div>
      <h3>试卷不存在</h3>
      <p>链接可能已过期，请重新生成一份</p>
      <router-link to="/generate" class="btn btn-primary">去生成</router-link>
    </div>

    <template v-else>
      <div class="card" style="display:flex;justify-content:space-between;align-items:center;padding:1.25rem 1.75rem;">
        <div>
          <div style="font-weight:600;font-size:1.05rem;">{{ paper.title }}</div>
          <div style="color:var(--text-secondary);font-size:.82rem;margin-top:.15rem;">
            {{ paper.questions.length }} 题 · 已答 {{ answered }}/{{ paper.questions.length }}
          </div>
        </div>
        <button class="btn btn-success" @click="submit" :disabled="submitting">
          {{ submitting ? '提交中…' : '提交全部' }}
        </button>
      </div>

      <div v-for="(q, i) in paper.questions" :key="i" class="question">
        <div class="question-header">
          <span class="question-number">第 {{ i+1 }} 题 · <span :class="'tag '+typeTag(q.type)">{{ typeLabel(q.type) }}</span></span>
          <span class="tag" style="background:var(--bg);color:var(--text-secondary);">{{ diffLabel(q.difficulty) }}</span>
        </div>
        <div class="question-stem">{{ q.stem }}</div>

        <div v-if="q.type==='choice'" class="options">
          <div v-for="(opt,oi) in q.options" :key="oi"
            class="option" :class="{selected:answers[i]===String(oi)}"
            @click="answers[i]=String(oi)">
            <span class="option-letter">{{ 'ABCDEFGH'[oi] }}</span>
            <span>{{ opt }}</span>
          </div>
        </div>

        <div v-if="q.type==='judgment'" class="options options-row">
          <div class="option" :class="{selected:answers[i]==='true'}" @click="answers[i]='true'">
            <span class="option-letter">✓</span> 正确
          </div>
          <div class="option" :class="{selected:answers[i]==='false'}" @click="answers[i]='false'">
            <span class="option-letter">✗</span> 错误
          </div>
        </div>

        <textarea v-if="q.type==='fill_blank'||q.type==='short_answer'||q.type==='essay'"
          v-model="answers[i]"
          :placeholder="'输入'+(q.type==='fill_blank'?'答案':'回答')+'…'"
          style="width:100%;padding:.75rem;border:1.5px solid var(--border);border-radius:var(--radius);font-family:inherit;font-size:.925rem;transition:border-color var(--transition);"
          :rows="q.type==='essay'?5:2"
          @focus="$el.style.borderColor='var(--accent)'">
        </textarea>
      </div>

      <div style="text-align:center;padding:1.5rem 0 3rem;">
        <button class="btn btn-success" @click="submit" :disabled="submitting" style="font-size:1rem;padding:.85rem 2.5rem;">
          {{ submitting ? '提交中…' : '提交全部答案' }}
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

const answered = computed(() =>
  paper.value
    ? paper.value.questions.filter((_,i) => answers.value[i]!==undefined && answers.value[i]!=='').length
    : 0
)

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
