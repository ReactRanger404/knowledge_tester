const API = ''

export async function generateExam(config) {
  const r = await fetch(`${API}/api/exam/generate`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function submitAnswers(examId, answers) {
  const r = await fetch(`${API}/api/exam/${examId}/submit`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(answers),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
