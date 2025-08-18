async function askQuestion() {
  const btn = document.getElementById('askBtn');
  const q = document.getElementById('query').value.trim();
  const answerCard = document.getElementById('answerCard');
  const answer = document.getElementById('answer');
  const sql = document.getElementById('sql');
  const raw = document.getElementById('raw');
  const fallback = document.getElementById('fallback');

  if (!q) return;
  btn.disabled = true; answerCard.hidden = false; answer.textContent = 'Thinking...';
  sql.textContent = ''; raw.textContent = ''; fallback.hidden = true; fallback.textContent = '';

  try {
    const res = await fetch('/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q })
    });
    const data = await res.json();
    if (data.status === 'ok') {
      if (data.result !== undefined) {
        answer.textContent = String(data.result);
      } else if (data.agent_output) {
        answer.textContent = String(data.agent_output).split('\n').slice(-1)[0] || String(data.agent_output);
      } else {
        answer.textContent = 'Done.';
      }
      if (data.sql) sql.textContent = data.sql;
      raw.textContent = JSON.stringify(data, null, 2);
    } else {
      fallback.hidden = false;
      fallback.textContent = data.message || 'Sorry, unable to answer at this point in time.';
      answer.textContent = '';
    }
  } catch (e) {
    fallback.hidden = false;
    fallback.textContent = 'Network error. Please try again.';
    answer.textContent = '';
  } finally {
    btn.disabled = false;
  }
}

document.getElementById('askBtn').addEventListener('click', askQuestion);

document.getElementById('query').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
    askQuestion();
  }
});
