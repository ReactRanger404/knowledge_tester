import { createRouter, createWebHashHistory } from 'vue-router'
import GenerateExam from '../views/GenerateExam.vue'
import TakeExam from '../views/TakeExam.vue'
import ExamResults from '../views/ExamResults.vue'

const routes = [
  { path: '/', redirect: '/generate' },
  { path: '/generate', component: GenerateExam },
  { path: '/exam/:id', component: TakeExam },
  { path: '/results/:id', component: ExamResults },
]

export default createRouter({ history: createWebHashHistory(), routes })
