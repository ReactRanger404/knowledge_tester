<template>
  <div class="container container-wide">
    <div v-if="!result" class="empty-state">
      <div class="icon">📊</div>
      <h3>还没有答题结果</h3>
      <p>完成答题后才能查看</p>
      <router-link :to="'/exam/'+id" class="btn btn-primary">去答题</router-link>
    </div>

    <template v-else>
      <div class="result-hero">
        <h2>{{ paper?.title||'答题结果' }}</h2>
        <p class="sub">{{ report.correct_count }}/{{ report.total_questions }} 题正确</p>
        <div :class="'score-ring '+(passed?'pass':'fail')">
          <span class="num">{{ score }}</span>
          <span class="unit">分</span>
        </div>
        <div class="stat-row">
          <span class="stat-pill green">✓ 正确 {{ report.correct_count }}</span>
          <span class="stat-pill red">✗ 错误 {{ report.total_questions - report.correct_count }}</span>
          <span class="stat-pill gray">📄 共 {{ report.total_questions }} 题</span>
        </div>
      </div>

      <div v-if="analysis?.knowledge_explanations?.length" class="card">
        <h3 class="card-title">知识点讲解</h3>
        <div v-for="(ke, i) in analysis.knowledge_explanations" :key="i" class="explanation-item">
          <div class="title">第 {{ ke.question_index+1 }} 题 · {{ ke.knowledge_point }}</div>
          <div class="body">{{ ke.explanation }}</div>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">逐题回顾</h3>
        <div v-for="(q,i) in paper?.questions||[]" :key="i"
          :class="'review-item '+(report.results[i]?.is_correct?'correct':'wrong')">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.35rem;flex-wrap:wrap;gap:.3rem;">
            <span style="font-weight:600;font-size:.9rem;">
              第 {{ i+1 }} 题 · <span :class="'tag '+typeTag(q.type)">{{ typeLabel(q.type) }}</span>
            </span>
            <span class="status-tag">
              {{ report.results[i]?.is_correct ? '✓ 正确' : '✗ 错误' }}
            </span>
          </div>
          <div style="font-size:.9rem;line-height:1.7;">{{ q.stem }}</div>
          <div v-if="report.results[i]?.feedback" class="feedback">
            <strong>反馈：</strong>{{ report.results[i].feedback }}
          </div>
        </div>
      </div>

      <div style="text-align:center;padding:0 0 3rem;">
        <router-link to="/generate" class="btn btn-primary">再出一套</router-link>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute(); const id = route.params.id
const paper = ref(null); const result = ref(null)

onMounted(() => {
  const exams = JSON.parse(localStorage.getItem('kt_exams')||'{}')
  paper.value = exams[id] || null
  const results = JSON.parse(localStorage.getItem('kt_results')||'{}')
  result.value = results[id] || null
})

const report = computed(() => result.value?.grading_report||{})
const analysis = computed(() => result.value?.error_analysis||null)
const score = computed(() => report.value?.max_total_score ? Math.round((report.value.total_score/report.value.max_total_score)*100) : 0)
const passed = computed(() => score.value>=60)

function typeLabel(t) { return {choice:'选择题',judgment:'判断题',fill_blank:'填空题',short_answer:'简答题',essay:'论述题'}[t]||t }
function typeTag(t) { return {choice:'tag-choice',judgment:'tag-judgment',fill_blank:'tag-fill',short_answer:'tag-short',essay:'tag-essay'}[t]||'' }
</script>
