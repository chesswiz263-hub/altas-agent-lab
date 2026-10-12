/* UI for the public, read-only, browser-only ATLAS demo. */
(function () {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const corpus = globalThis.AtlasCorpus;
  const factory = globalThis.AtlasDemoEngine;
  const engine = factory && corpus ? factory.createEngine(corpus) : null;
  const repoBase = 'https://github.com/chesswiz263-hub/altas-agent-lab/blob/main/';
  let lastReport = null;
  const titles = { workbench: 'Agent workbench', knowledge: 'Knowledge base', evaluation: 'Evaluation lab' };

  function el(tag, className, content) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (content !== undefined) item.textContent = String(content);
    return item;
  }
  function renderError(message) { $('#form-error').textContent = message; }
  function percent(value) { return `${Math.round(value * 100)}%`; }
  function linkToSource(path) { return repoBase + path.split('/').map(encodeURIComponent).join('/'); }

  function switchTab(name) {
    if (!Object.hasOwn(titles, name)) return;
    document.querySelectorAll('[data-tab]').forEach(btn => {
      const active = btn.dataset.tab === name;
      btn.classList.toggle('active', active);
      if (active) btn.setAttribute('aria-current', 'page');
      else btn.removeAttribute('aria-current');
    });
    Object.keys(titles).forEach(key => $(`#view-${key}`).classList.toggle('hidden', key !== name));
    $('#breadcrumb-tab').textContent = titles[name];
  }

  function renderTrace(report) {
    const list = $('#trace-list');
    list.replaceChildren();
    report.trace.forEach(stage => {
      const item = el('li');
      item.append(el('div','trace-label',stage.label), el('div','trace-detail',stage.detail));
      list.append(item);
    });
    const state = $('#trace-state');
    state.textContent = 'COMPLETE';
    state.classList.add('done');
  }

  function renderReport(report) {
    const body = $('#report-body');
    body.replaceChildren();
    body.className = 'report-text';
    const status = el('div','report-status' + (report.isAbstention ? ' warn' : ''),report.isAbstention ? '◇ NOT ENOUGH EVIDENCE' : '✓ SOURCE-BASED EXCERPTS');
    body.append(status);
    if (report.isAbstention) {
      body.append(el('p','report-entry','I could not find a supporting passage in the three example documents. Try a question about agent safeguards, MCP, or document retrieval.'));
    } else {
      report.evidence.forEach(item => {
        const p = el('p','report-entry',item.quote);
        const citation = el('span','citation-tag',` [${item.index}]`);
        p.append(citation);
        body.append(p);
      });
    }
    $('#report-foot').textContent = `Query term coverage: ${percent(report.coverage)} · ${report.evidence.length} exact excerpts verified · No live AI model used`;
    $('#copy-report').disabled = false;
  }

  function renderEvidence(report) {
    const wrapper = $('#evidence-list');
    wrapper.replaceChildren();
    if (report.isAbstention) {
      wrapper.append(el('div','evidence-empty','No supporting passages were selected. This public sandbox abstains when its limited corpus does not support a question.'));
      return;
    }
    report.evidence.forEach(item => {
      const card = el('article','evidence-card');
      const title = el('div','evidence-title');
      title.append(el('div','',item.title),el('span','',`[${item.index}] VERIFIED`));
      card.append(title,el('p','',item.quote));
      const link = el('a','','View source document ↗');
      link.href = linkToSource(item.source);
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      card.append(link);
      wrapper.append(card);
    });
  }

  function runTask(question) {
    if (!engine) { renderError('The demo files could not be loaded. Reload the page.'); return; }
    try {
      renderError('');
      const result = engine.run(question);
      lastReport = result;
      renderTrace(result);
      renderReport(result);
      renderEvidence(result);
    } catch (err) { renderError(err.message || 'Unable to run the demo'); }
  }

  function renderKnowledge() {
    if (!engine) return;
    const root = $('#knowledge-list');
    root.replaceChildren();
    engine.getDocuments().forEach((doc, i) => {
      const card = el('details','doc-card');
      const summary = el('summary');
      const icon = el('span','doc-index',String(i+1).padStart(2,'0'));
      const text = el('div');
      text.append(el('div','doc-name',doc.title),el('div','doc-sub',`${doc.chunks.length} passages · Public example`));
      summary.append(icon,text,el('span','doc-expand','+'));
      card.append(summary);
      const body = el('div','doc-body');
      doc.chunks.forEach(chunk => body.append(el('p','',chunk.text)));
      const source = el('a','','Inspect original Markdown on GitHub ↗');
      source.href = linkToSource(doc.source); source.target='_blank'; source.rel='noopener noreferrer';
      body.append(source);
      card.append(body);
      root.append(card);
    });
  }

  function renderEvaluation() {
    if (!engine) return;
    const result = engine.evaluate();
    const root = $('#eval-output');
    root.replaceChildren();
    const cards = el('div','eval-stats');
    [['Recall @3', result.recallAt3],['Citation presence',result.citationPresence]].forEach(([label, value]) => {
      const stat=el('div','eval-stat');
      stat.append(el('strong','',percent(value)),el('span','',label.toUpperCase()));
      cards.append(stat);
    });
    root.append(cards);
    const table = el('table','eval-table');
    const thead = el('thead'); const header = el('tr');
    ['Prompt','Top-3 document match','Exact source citation'].forEach(t=>header.append(el('th','',t)));
    thead.append(header); table.append(thead);
    const tbody=el('tbody');
    result.cases.forEach(item=>{
      const tr=el('tr');
      tr.append(el('td','',item.question),el('td',item.hit?'pass':'fail',item.hit?'PASS':'MISS'),el('td',item.citationValid?'pass':'fail',item.citationValid?'VALID':'NO EVIDENCE'));
      tbody.append(tr);
    });
    table.append(tbody); root.append(table);
    root.append(el('p','eval-disclaimer',result.disclaimer));
  }

  document.querySelectorAll('[data-tab]').forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
  document.querySelectorAll('[data-question]').forEach(btn => btn.addEventListener('click', () => {
    $('#question').value = btn.dataset.question;
    $('#char-count').textContent = `${$('#question').value.length} / ${factory.MAX_QUERY}`;
    switchTab('workbench');
    $('#question').focus();
  }));
  $('#question').addEventListener('input', event => {
    $('#char-count').textContent = `${event.target.value.length} / ${factory.MAX_QUERY}`;
    renderError('');
  });
  $('#prompt-form').addEventListener('submit', event => {
    event.preventDefault();
    runTask($('#question').value);
  });
  $('#run-eval').addEventListener('click', renderEvaluation);
  $('#copy-report').addEventListener('click', async () => {
    if (!lastReport) return;
    const lines = [lastReport.question,'',lastReport.status,'',...lastReport.evidence.map(i => `[${i.index}] ${i.quote} — ${i.title} (${i.source})`),'',lastReport.note];
    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      $('#copy-report').textContent='Copied ✓';
    } catch (_) { $('#copy-report').textContent='Copy unavailable'; }
  });
  renderKnowledge();
  if (!engine) renderError('The demo engine did not load. Check the demo files.');
})();
