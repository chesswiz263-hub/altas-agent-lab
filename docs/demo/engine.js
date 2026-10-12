/* ATLAS Public Demo — deterministic, extractive retrieval engine.
 * Zero API calls, zero credentials, zero personal data persistence.
 * This is NOT a language model or the private ATLAS backend.
 */
(function (root) {
  'use strict';

  const STOP = new Set('a an and are as at be by can could do does for from had has have how i in into is it its of on or our should the their them these this to using was were what when where which who why with would you your we about that all make makes making build building work works working explain explaining describe describing outline outlining demonstrate demonstrating importance between handle handles handled handling help helps helped helping run runs running avoid avoids avoided avoiding improve improves improving protect protects protecting protected'.split(' '));
  // A tiny documented set of vocabulary equivalences for this *fixed* demo corpus.
  // This is not a semantic model: unknown domain terminology must still abstain.
  const EQUIVALENTS = Object.freeze({
    reliable: 'reliability', robust: 'reliability', robustness: 'reliability',
    safety: 'safeguard', safe: 'safeguard', safely: 'safeguard',
    proof: 'prove'
  });
  const MAX_QUERY = 320;
  const BENCHMARK = Object.freeze([
    { question: 'What safeguards make tool-using agents reliable?', doc: 'agent_reliability_playbook' },
    { question: 'How should agents handle prompt injection and untrusted retrieved content?', doc: 'agent_reliability_playbook' },
    { question: 'What does MCP provide to an AI application?', doc: 'mcp_integration_guide' },
    { question: 'How should credentials be handled for MCP tools?', doc: 'mcp_integration_guide' },
    { question: 'What does ATLAS use SQLite FTS5 and BM25 for?', doc: 'retrieval_guide' },
    { question: 'Why is a citation not proof of a correct answer?', doc: 'retrieval_guide' }
  ]);

  function stem(word) {
    if (word.length > 6 && word.endsWith('ing')) return word.slice(0, -3);
    if (word.length > 5 && word.endsWith('ies')) return word.slice(0, -3) + 'y';
    if (word.length > 4 && word.endsWith('s') && !word.endsWith('ss')) return word.slice(0, -1);
    return word;
  }

  function tokenize(input) {
    return (String(input).toLowerCase().match(/[a-z0-9]+/g) || [])
      .filter(w => w.length > 1 && !STOP.has(w))
      .map(stem).map(w => EQUIVALENTS[w] || w);
  }

  function splitSentences(text) {
    // All bundled sample paragraphs are declarative English sentences.
    return String(text).match(/[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$/g)?.map(s => s.trim()).filter(Boolean) || [];
  }

  function createEngine(corpus) {
    if (!Array.isArray(corpus) || !corpus.length) throw new Error('Public demo corpus not loaded');
    const docs = corpus.map(doc => ({ ...doc, chunks: doc.chunks.map(chunk => ({ ...chunk })) }));
    const chunks = docs.flatMap(doc => doc.chunks.map(chunk => ({
      ...chunk, docId: doc.id, title: doc.title, source: doc.source,
      words: tokenize(chunk.text).concat(tokenize(doc.title)),
      bodyWords: tokenize(chunk.text), titleWords: tokenize(doc.title)
    })));
    if (!chunks.length) throw new Error('The public corpus is empty');
    const avgLength = chunks.reduce((acc, c) => acc + c.words.length, 0) / chunks.length;
    const frequency = new Map();
    chunks.forEach(chunk => new Set(chunk.words).forEach(t => frequency.set(t, (frequency.get(t) || 0) + 1)));
    const total = chunks.length;

    function search(question, limit = 3) {
      const query = [...new Set(tokenize(question))];
      if (!query.length) return [];
      return chunks.map(chunk => {
        const count = new Map();
        chunk.words.forEach(w => count.set(w, (count.get(w) || 0) + 1));
        let score = 0;
        let hits = 0;
        query.forEach(t => {
          const tf = count.get(t) || 0;
          if (!tf) return;
          hits += 1;
          const df = frequency.get(t) || 0;
          const idf = Math.log(1 + (total - df + .5) / (df + .5));
          score += idf * (tf * 2.2) / (tf + 1.2 * (.25 + .75 * chunk.words.length / avgLength));
        });
        return { id: chunk.id, docId: chunk.docId, title: chunk.title, source: chunk.source,
          text: chunk.text, score, hits, coverage: hits / query.length };
      }).filter(c => c.score > 0).sort((a,b) => b.hits - a.hits || b.score - a.score || a.id.localeCompare(b.id)).slice(0, limit);
    }

    function relevanceGate(question, results) {
      const terms = [...new Set(tokenize(question))];
      const available = terms.filter(t => frequency.has(t));
      const missing = terms.filter(t => !frequency.has(t));
      const candidate = results[0] || null;
      const coverage = terms.length ? available.length / terms.length : 0;
      const passageCoverage = candidate ? candidate.coverage : 0;
      // Out-of-corpus concepts (gravity, quantum, etc.) cannot be validated
      // merely because unrelated parts of the question match a document.
      // Query verbs and function words are excluded by STOP; the remaining
      // unmatched terms are treated conservatively as unsupported concepts.
      const unknownConcepts = missing.filter(t => t.length >= 4);

      // Require multiple independent lexical anchors for multi-term queries.
      // A lone shared word (such as "vector" or "effect") is never enough.
      const minimumHits = terms.length <= 1 ? 1 : 2;
      const minCoverage = terms.length <= 2 ? 0.5 : 0.46;
      let reason = null;
      if (!candidate) reason = 'No matching source passages';
      else if (available.length < minimumHits || candidate.hits < minimumHits)
        reason = 'Insufficient distinct query terms supported by a single source passage';
      else if (unknownConcepts.length)
        reason = 'Unrecognized topic-specific terminology: ' + unknownConcepts.join(', ');
      else if (coverage < minCoverage || passageCoverage < Math.min(minCoverage, 0.5))
        reason = 'Insufficient important-term coverage for reliable retrieval';
      return { accepted: reason === null, reason: reason || 'Minimum lexical relevance checks passed',
        matchedTerms: available, unmatchedTerms: missing, corpusCoverage: coverage,
        topPassageCoverage: passageCoverage, topScore: candidate?.score || 0,
        disclaimer: 'Lexical diagnostics only; passing does not prove semantic relevance, entailment or factual truth.' };
    }

    function selectEvidence(question, results, maxItems = 3) {
      const q = new Set(tokenize(question));
      const sentences = [];
      // Exclude weakly matched passages to reduce off-topic extractive answers.
      const minimumScore = (results[0]?.score || 0) * 0.45;
      results.filter(hit => hit.score >= minimumScore).forEach(hit => {
        splitSentences(hit.text).forEach(sentence => {
          const words = new Set(tokenize(sentence));
          const overlap = [...q].filter(t => words.has(t)).length;
          // A sentence must share substantive terms with the question.
          // A title may establish a second anchor (e.g. Reliability Playbook
          // for a question about reliable agents). Still require actual body
          // overlap so a title alone never supplies an unsupported quotation.
          const titleOverlap = [...q].filter(t => tokenize(hit.title).includes(t)).length;
          if (overlap >= Math.min(2, q.size) ||
              (overlap === 1 && titleOverlap >= 1 && hit.hits >= 2 &&
               [...q].filter(t => words.has(t) || tokenize(hit.title).includes(t)).length >= 2))
            sentences.push({ sentence, overlap, source: hit });
        });
      });
      sentences.sort((a,b) => b.overlap - a.overlap || b.source.score - a.source.score || a.sentence.localeCompare(b.sentence));
      const seen = new Set();
      return sentences.filter(item => {
        if (seen.has(item.sentence)) return false;
        seen.add(item.sentence);
        return true;
      }).slice(0, maxItems).map((item, i) => ({
        index: i + 1, quote: item.sentence, docId: item.source.docId, chunkId: item.source.id,
        title: item.source.title, source: item.source.source, overlap: item.overlap
      }));
    }

    function audit(evidence) {
      const checks = evidence.map(item => {
        const chunk = chunks.find(c => c.id === item.chunkId && c.docId === item.docId);
        return { index: item.index, supported: Boolean(chunk && chunk.text.includes(item.quote)) };
      });
      return { valid: checks.every(check => check.supported), checked: checks.length, checks };
    }

    function route(question) {
      const words = new Set(tokenize(question));
      if (['mcp','protocol','tool','adapter'].some(w => words.has(w))) return { label:'Tooling & integration', reason:'Matched integration/tool terminology' };
      if (['citation','bm25','retrieval','fts5','search','index'].some(w => words.has(w))) return { label:'Retrieval & evidence', reason:'Matched retrieval/evidence terminology' };
      return { label:'Reliability research', reason:'Using the general research route' };
    }

    function run(question) {
      if (typeof question !== 'string') throw new TypeError('Question must be text');
      const clean = question.trim();
      if (!clean) throw new Error('Enter a question to begin.');
      if (clean.length > MAX_QUERY) throw new Error(`Keep your question under ${MAX_QUERY} characters.`);
      const routeResult = route(clean);
      const results = search(clean, 4);
      // No snippets at all means decline rather than fabricate an answer.
      const relevance = relevanceGate(clean, results);
      const evidence = relevance.accepted ? selectEvidence(clean, results) : [];
      const validation = audit(evidence);
      const found = evidence.length > 0 && validation.valid;
      const status = !found ? 'No sufficiently relevant passage in the sample documents' : 'Source excerpts found';
      const relevantWords = new Set(results.flatMap(r => tokenize(r.text)));
      const queryWords = new Set(tokenize(clean));
      const overlap = [...queryWords].filter(w => relevantWords.has(w)).length;
      const coverage = queryWords.size ? overlap / queryWords.size : 0;
      const trace = [
        { label: 'Route question', detail: `${routeResult.label} · ${routeResult.reason}` },
        { label: 'Search documents', detail: `Ran local BM25 over ${chunks.length} public passages · ${results.length} matching results` },
        { label: 'Check evidence', detail: `${relevance.reason} · ${validation.checked} exact quote checks · ${validation.valid ? 'valid source matches' : 'source mismatch'}` },
        { label: 'Assemble report', detail: found ? `Returned ${evidence.length} verbatim source passages · no generative model` : 'Abstained rather than invent an answer' }
      ];
      return {
        question: clean, status, route: routeResult, results, relevance,
        evidence: found ? evidence : [], audit: validation, coverage,
        trace, isAbstention: !found,
        note: 'This demo returns exact excerpts from a limited sample corpus. It is not a live AI model and does not verify external facts.'
      };
    }

    // An extractive research dossier: organizes source material, never invents
    // claims, references or mathematical conclusions. No LLM runs here.
    function dossier(question, hypotheses = []) {
      const outcome = run(question);
      if (!Array.isArray(hypotheses) || hypotheses.length > 6 ||
          hypotheses.some(h => typeof h !== 'string' || h.length > 120))
        throw new Error('Provide up to six short hypothesis labels.');
      return {
        title: `Evidence dossier: ${outcome.question}`,
        question: outcome.question,
        scope: 'Offline extractive report based exclusively on the three bundled example documents',
        disposition: outcome.isAbstention ? 'INSUFFICIENT_EVIDENCE' : 'EXCERPTS_AVAILABLE',
        relevance: outcome.relevance,
        sources: outcome.evidence.map(item => ({citation: `[${item.index}]`, quotation: item.quote,
          document: item.title, path: item.source, exactQuoteVerified: outcome.audit.checks.find(c=>c.index===item.index)?.supported === true})),
        hypotheses: hypotheses.map(name => ({ name, assessment: 'NOT_ASSESSED',
          explanation: 'No theory comparison without theory-specific evidence and independent reasoning.' })),
        mathematicalAudit: { status: 'NOT_RUN', reason: 'Browser demo does not evaluate equations or symbolic derivations.' },
        limitations: ['Exact quotation proves text provenance only, not factual correctness.',
          'No independent source verification, source credibility evaluation, semantic entailment, or web research.',
          'No autonomous AI or generated scientific conclusions.']
      };
    }

    function evaluate() {
      const cases = BENCHMARK.map(entry => {
        const result = run(entry.question);
        return { question: entry.question, expected: entry.doc,
          hit: result.results.slice(0, 3).some(r => r.docId === entry.doc),
          citationValid: result.audit.valid && result.evidence.length > 0 };
      });
      return {
        cases, recallAt3: cases.filter(c => c.hit).length / cases.length,
        citationPresence: cases.filter(c => c.citationValid).length / cases.length,
        disclaimer: 'Six hand-authored questions on three sample documents. This is a retrieval smoke test, not a factuality or general intelligence benchmark.'
      };
    }

    return { run, search, audit, route, evaluate, dossier, getDocuments: () => docs.map(d => ({ ...d, chunks: d.chunks.map(c => ({...c})) })) };
  }

  const exports = { tokenize, createEngine, BENCHMARK, MAX_QUERY };
  if (typeof module !== 'undefined' && module.exports) module.exports = exports;
  else root.AtlasDemoEngine = exports;
})(typeof globalThis === 'object' ? globalThis : this);
