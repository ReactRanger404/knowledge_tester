<template>
  <div class="container">
    <div v-if="!result" class="empty-state">
      <div class="icon">📊</div>
      <h3>还没有答题结果</h3>
      <router-link :to="'/exam/'+id" class="btn btn-primary">去答题</router-link>
    </div>

    <template v-else>
      <div class="card result-header">
        <h2>{{ paper?.title||'答题结果' }}</h2>
        <div :class="'score-circle '+(passed?'pass':'fail')">{{ score }}<span style="font-size:1rem;">分</span></div>
        <div class="stat-row">
          <div class="stat-card"><div class="num" style="color:var(--green)">{{ report.correct_count }}</div><div class="label">正确</div></div>
          <div class="stat-card"><div class="num" style="color:var(--red)">{{ report.total_questions - report.correct_count }}</div><div class="label">错误</div></div>
          <div class="stat-card"><div class="num">{{ report.total_questions }}</div><div class="label">总题</div></div>
        </div>
      </div>

      <!-- 错题分析 -->
      <div v-if="analysis" class="card">
        <h3 class="card-title">📋 错题分析</h3>
        <p style="margin-bottom:1rem">{{ analysis.summary }}</p>

        <div v-if="analysis.weak_concepts?.length" style="margin-bottom:1.5rem">
          <h4 style="font-size:.9rem;margin-bottom:.5rem;color:var(--gray-700)">薄弱知识点</h4>
          <div v-for="wc in analysis.weak_concepts" :key="wc.concept" class="weak-concept">
            <span style="flex:0 0 120px;font-weight:500">{{ wc.concept }}</span>
            <div class="weak-bar"><div :class="'weak-bar-fill '+masteryCls(wc.mastery_ratio)" :style="{width:(wc.mastery_ratio*100)+'%'}"></div></div>
            <span style="flex:0 0 60px;font-size:.85rem;color:var(--gray-500)">{{ Math.round(wc.mastery_ratio*100) }}%</span>
          </div>
        </div>

        <div v-if="analysis.error_patterns?.length">
          <h4 style="font-size:.9rem;margin-bottom:.5rem;color:var(--gray-700)">错误模式</h4>
          <div v-for="ep in analysis.error_patterns" :key="ep.pattern_name" style="padding:.5rem 0;border-bottom:1px solid var(--gray-100);display:flex;justify-content:space-between">
            <span>• {{ ep.pattern_name }}</span><span style="color:var(--gray-500);font-size:.85rem">{{ ep.frequency }} 次</span>
          </div>
        </div>

        <div v-if="analysis.suggestion" style="margin-top:1.5rem;padding:1rem;background:var(--gray-50);border-radius:8px;font-size:.9rem">
          <strong>💡 学习建议：</strong> {{ analysis.suggestion }}
        </div>
      </div>

      <!-- 逐题回顾 -->
      <div class="card">
        <h3 class="card-title">📖 逐题回顾</h3>
        <div v-for="(q,i) in paper?.questions||[]" :key="i" :class="'review-item '+(report.results[i]?.is_correct?'correct':'wrong')">
          <div style="display:flex;justify-content:space-between;margin-bottom:.5rem">
            <span style="font-weight:500">第{{ i+1 }}题 · <span :class="'tag '+typeTag(q.type)">{{ typeLabel(q.type) }}</span></span>
            <span class="status-tag">{{ report.results[i]?.is_correct?'✓ 正确':'✗ 错误' }}</span>
          </div>
          <div style="margin-bottom:.25rem">{{ q.stem }}</div>
          <div v-if="report.results[i]?.feedback" style="font-size:.85rem;color:var(--gray-700);margin-top:.25rem">
            <strong>反馈：</strong>{{ report.results[i].feedback }}
          </div>
        </div>
      </div>

      <div style="text-align:center;padding:0 0 2rem">
        <router-link to="/generate" class="btn btn-primary">📝 再出一套</router-link>
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
function masteryCls(r) { return r>=0.7?'mastery-high':r>=0.4?'mastery-mid':'mastery-low' }
</script>
