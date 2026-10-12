'use strict';
const test=require('node:test'); const assert=require('node:assert/strict');
const vm=require('node:vm'); const fs=require('node:fs'); const path=require('node:path');
const root=path.resolve(__dirname,'../..');
const ctx={globalThis:{}}; vm.runInNewContext(fs.readFileSync(path.join(root,'docs/demo/corpus.js'),'utf8'),ctx);
const engine=require('../../docs/demo/engine.js').createEngine(ctx.globalThis.AtlasCorpus);
test('Aharonov Bohm lexical false-positive correctly abstains',()=>{
 const o=engine.run('How does the Aharonov-Bohm effect demonstrate the importance of electromagnetic potentials in quantum mechanics?');
 assert.equal(o.isAbstention,true); assert.equal(o.evidence.length,0);
});
test('quantum vector lexical false-positive correctly abstains',()=>{
 const o=engine.run('Explain the relationship between quantum wavefunctions, magnetic flux, and electromagnetic vector potentials.');
 assert.equal(o.isAbstention,true); assert.ok(o.relevance.unmatchedTerms.length>=2);
});
test('Einstein out of domain abstains',()=>assert.equal(engine.run('What was Albert Einstein greatest contribution to physics?').isAbstention,true));
test('MCP and retrieval queries retain on-domain evidence',()=>{
 for(const q of ['How does MCP expose tools to AI applications?','Why does a citation not prove an answer is correct?']) {
  const o=engine.run(q); assert.equal(o.isAbstention,false,q); assert.ok(o.audit.valid);
 }
});
test('dossier refuses ungrounded comparison and labels mathematical audit as not run',()=>{
 const o=engine.dossier('Compare dark matter and MOND using verified observational evidence',['Lambda CDM','MOND']);
 assert.equal(o.disposition,'INSUFFICIENT_EVIDENCE'); assert.equal(o.sources.length,0);
 assert.ok(o.hypotheses.every(h=>h.assessment==='NOT_ASSESSED'));
 assert.equal(o.mathematicalAudit.status,'NOT_RUN');
});
test('dossier retains exact provenance for supported queries',()=>{
 const o=engine.dossier('What safeguards make tool-using agents reliable?');
 assert.equal(o.disposition,'EXCERPTS_AVAILABLE'); assert.ok(o.sources.length); assert.ok(o.sources.every(s=>s.exactQuoteVerified));
});
test('dossier has bounded hypothesis input',()=>{
 assert.throws(()=>engine.dossier('foo',Array(7).fill('a')),/six/);
});
