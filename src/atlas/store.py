"""SQLite-backed knowledge base, FTS5 search, runs, and audit events."""
import hashlib
import importlib.util
import json
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from atlas.config import database_path
from atlas.embeddings import Encoder, EmbeddingUnavailable, SentenceEncoder, cosine, model_name, normalize
from atlas.hybrid import grams, reciprocal_rank_fuse, similarity, vectorize


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def chunk_text(text: str, size: int = 820, overlap: int = 120) -> list[str]:
    """Whitespace-aware chunks with bounded overlap and no lost characters."""
    if not text.strip():
        return []
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            candidate = text.rfind(" ", start + size // 2, end)
            if candidate > start:
                end = candidate
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


class Store:
    def __init__(self, path: Path | str | None = None, *, encoder: Encoder | None = None,
                 embedding_model: str | None = None):
        self.path = Path(path or database_path())
        self.encoder = encoder
        self.embedding_model = embedding_model or model_name()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL, digest TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL, body TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    chunk_id UNINDEXED, title, body, tokenize='unicode61'
                );
                CREATE TABLE IF NOT EXISTS chunk_vectors (
                    chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
                    vector TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS semantic_vectors (
                    chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
                    model TEXT NOT NULL, dimension INTEGER NOT NULL, vector TEXT NOT NULL,
                    PRIMARY KEY(chunk_id, model)
                );
                CREATE INDEX IF NOT EXISTS idx_semantic_vectors_model ON semantic_vectors(model);
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL, content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    memory_id UNINDEXED, title, content, tokenize='unicode61'
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, prompt TEXT NOT NULL, provider TEXT NOT NULL,
                    model TEXT NOT NULL, status TEXT NOT NULL, answer TEXT NOT NULL DEFAULT '',
                    steps INTEGER NOT NULL DEFAULT 0, input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL
                    REFERENCES runs(id) ON DELETE CASCADE, kind TEXT NOT NULL,
                    payload TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id,id);
                CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
            """)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(runs)")}
            if "mode" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN mode TEXT NOT NULL DEFAULT 'single'")
            if "estimated_cost_usd" not in columns:
                db.execute("ALTER TABLE runs ADD COLUMN estimated_cost_usd REAL")
            # Migrates older on-disk databases without altering chunk/citation IDs.
            for row in db.execute("SELECT c.id, c.body FROM chunks c LEFT JOIN chunk_vectors v ON v.chunk_id=c.id WHERE v.chunk_id IS NULL"):
                db.execute("INSERT INTO chunk_vectors(chunk_id,vector) VALUES (?,?)",
                           (row["id"], json.dumps(vectorize(row["body"]))))

    def add_document(self, title: str, content: str) -> dict:
        title, content = title.strip(), content.strip()
        digest = hashlib.sha256((title + "\0" + content).encode()).hexdigest()
        with self.connect() as db:
            existing = db.execute("SELECT id FROM documents WHERE digest=?", (digest,)).fetchone()
            if existing:
                return {"id": existing["id"], "title": title, "chunks": 0, "duplicate": True}
            cur = db.execute(
                "INSERT INTO documents(title,digest,created_at) VALUES (?,?,?)",
                (title, digest, utcnow()),
            )
            doc_id = cur.lastrowid
            parts = chunk_text(content)
            for idx, part in enumerate(parts):
                chunk_id = db.execute(
                    "INSERT INTO chunks(doc_id,ordinal,body) VALUES (?,?,?)", (doc_id, idx, part)
                ).lastrowid
                db.execute(
                    "INSERT INTO chunks_fts(chunk_id,title,body) VALUES (?,?,?)",
                    (chunk_id, title, part),
                )
                db.execute("INSERT INTO chunk_vectors(chunk_id,vector) VALUES (?,?)",
                           (chunk_id, json.dumps(vectorize(part))))
        return {"id": doc_id, "title": title, "chunks": len(parts), "duplicate": False}

    def list_documents(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("""
                SELECT d.id,d.title,d.created_at,COUNT(c.id) AS chunks
                FROM documents d LEFT JOIN chunks c ON c.doc_id=d.id
                GROUP BY d.id ORDER BY d.id DESC
            """).fetchall()
            return [dict(row) for row in rows]

    def delete_document(self, doc_id: int) -> bool:
        with self.connect() as db:
            ids = [r["id"] for r in db.execute("SELECT id FROM chunks WHERE doc_id=?", (doc_id,))]
            for chunk_id in ids:
                db.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (chunk_id,))
                db.execute("DELETE FROM chunk_vectors WHERE chunk_id=?", (chunk_id,))
                db.execute("DELETE FROM semantic_vectors WHERE chunk_id=?", (chunk_id,))
            cur = db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            return cur.rowcount > 0

    def search(self, query: str, limit: int = 5) -> list[dict]:
        # Quote individual tokens to keep FTS syntax untrusted input from becoming a query language.
        terms = list(dict.fromkeys(re.findall(r"[\w]+", query.casefold(), flags=re.UNICODE)))[:12]
        terms = [t for t in terms if len(t) > 1]
        if not terms:
            return []
        fts_query = " OR ".join('"' + t.replace('"', '') + '"' for t in terms)
        with self.connect() as db:
            rows = db.execute("""
                SELECT c.doc_id, d.title, c.id AS chunk_id, c.body,
                       bm25(chunks_fts, 0.0, 2.0, 1.0) AS rank
                FROM chunks_fts
                JOIN chunks c ON c.id = chunks_fts.chunk_id
                JOIN documents d ON d.id = c.doc_id
                WHERE chunks_fts MATCH ? ORDER BY rank ASC LIMIT ?
            """, (fts_query, min(max(limit, 1), 10))).fetchall()
            return [{**dict(row), "citation": f"doc:{row['doc_id']}#chunk:{row['chunk_id']}"} for row in rows]

    def search_hybrid(self, query: str, limit: int = 5) -> list[dict]:
        """Fuse BM25 with hashed lexical-trigram cosine rankings using RRF."""
        if not query.strip() or len(query) > 400:
            return []
        lexical = self.search(query, 10)
        qv = vectorize(query)
        if not any(qv):
            return lexical[:limit]
        with self.connect() as db:
            rows = db.execute("""SELECT c.doc_id,d.title,c.id AS chunk_id,c.body,v.vector
                FROM chunks c JOIN documents d ON d.id=c.doc_id
                JOIN chunk_vectors v ON v.chunk_id=c.id""").fetchall()
        query_grams = set(grams(query))
        scored = [(similarity(qv, json.loads(r["vector"])), r) for r in rows
                  if query_grams.intersection(grams(r["body"]))]
        ranked = [r for score, r in sorted(scored, key=lambda item: item[0], reverse=True)
                  if score > 0]
        vector_top = [dict(r) for r in ranked[:10]]
        fused = reciprocal_rank_fuse([[x["chunk_id"] for x in lexical],
                                      [x["chunk_id"] for x in vector_top]])
        matches = {x["chunk_id"]: x for x in (lexical + vector_top)}
        return [{**{k: v for k, v in matches[ident].items() if k != "vector"},
                 "citation": f"doc:{matches[ident]['doc_id']}#chunk:{ident}",
                 "fusion_score": round(score, 6), "retrieval": "hybrid_lexical"}
                for ident, score in fused[:min(max(limit, 1), 10)]]

    def get_citation(self, citation: str) -> dict | None:
        """Resolve only exact, canonical citations; never interpolate identifiers into SQL."""
        m = re.fullmatch(r"doc:(\d{1,15})#chunk:(\d{1,15})", citation)
        if not m:
            return None
        with self.connect() as db:
            row = db.execute("""SELECT c.doc_id, d.title, c.id AS chunk_id, c.body
                  FROM chunks c JOIN documents d ON d.id=c.doc_id
                  WHERE c.doc_id=? AND c.id=?""", (int(m[1]), int(m[2]))).fetchone()
        return {**dict(row), "citation": citation} if row else None

    def semantic_status(self) -> dict:
        with self.connect() as db:
            total = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            count = db.execute("SELECT COUNT(*) FROM semantic_vectors WHERE model=?",
                               (self.embedding_model,)).fetchone()[0]
        model_installed = self.encoder is not None or importlib.util.find_spec("sentence_transformers") is not None
        return {"model": self.embedding_model, "indexed_chunks": count,
                "total_chunks": total, "ready": bool(count and count == total and model_installed),
                "complete": count == total, "model_installed": model_installed,
                "optional_dependency": "sentence-transformers"}

    def _encoder(self) -> Encoder:
        return self.encoder or SentenceEncoder(self.embedding_model)

    def index_semantic(self, batch_size: int = 16, max_chunks: int = 256) -> dict:
        """Explicit opt-in indexing; never triggers a download at import/startup.

        Bounded per call; caller can invoke repeatedly. Each batch commits
        independently, so failed model loads do not damage FTS5 data.
        """
        if not 1 <= batch_size <= 64 or not 1 <= max_chunks <= 1000:
            raise ValueError("Invalid semantic indexing limits")
        indexed = 0
        while indexed < max_chunks:
            with self.connect() as db:
                rows = db.execute("""SELECT c.id,c.body FROM chunks c
                    LEFT JOIN semantic_vectors e ON e.chunk_id=c.id AND e.model=?
                    WHERE e.chunk_id IS NULL ORDER BY c.id LIMIT ?""",
                    (self.embedding_model, min(batch_size, max_chunks - indexed))).fetchall()
            if not rows:
                break
            vectors = self._encoder().encode([r["body"] for r in rows])
            if len(vectors) != len(rows):
                raise ValueError("Encoder returned wrong number of vectors")
            normalized = [normalize(v) for v in vectors]
            dimension = len(normalized[0])
            if any(len(v) != dimension for v in normalized):
                raise ValueError("Encoder returned inconsistent dimensions")
            with self.connect() as db:
                for row, vector in zip(rows, normalized):
                    db.execute("""INSERT OR IGNORE INTO semantic_vectors(chunk_id,model,dimension,vector)
                        VALUES (?,?,?,?)""", (row["id"], self.embedding_model,
                                                  dimension, json.dumps(vector)))
            indexed += len(rows)
        return {**self.semantic_status(), "indexed_this_call": indexed}

    def search_semantic(self, query: str, limit: int = 5) -> list[dict]:
        """Exact cosine scan for small corpora. No ANN/vector DB scale claims."""
        if not query.strip() or len(query) > 400:
            return []
        status = self.semantic_status()
        if not status["ready"]:
            raise EmbeddingUnavailable("Semantic index is absent/stale. Install the semantic extra, then POST /api/embeddings/index.")
        qv = normalize(self._encoder().encode([query])[0])
        with self.connect() as db:
            rows = db.execute("""SELECT c.doc_id,d.title,c.id AS chunk_id,c.body,
                   e.vector,e.dimension FROM semantic_vectors e
                   JOIN chunks c ON c.id=e.chunk_id JOIN documents d ON d.id=c.doc_id
                   WHERE e.model=?""", (self.embedding_model,)).fetchall()
        scored = []
        for r in rows:
            if r["dimension"] != len(qv):
                raise EmbeddingUnavailable("Index embedding dimension differs; re-index using the current model")
            score = cosine(qv, json.loads(r["vector"]))
            scored.append((score, r))
        scored.sort(key=lambda item: (-item[0], item[1]["chunk_id"]))
        return [{"doc_id": r["doc_id"], "title": r["title"], "chunk_id": r["chunk_id"],
                 "body": r["body"], "citation": f"doc:{r['doc_id']}#chunk:{r['chunk_id']}",
                 "similarity": round(score, 5), "retrieval": "neural_semantic"}
                for score, r in scored[:min(max(limit, 1), 10)]]

    def search_semantic_hybrid(self, query: str, limit: int = 5) -> list[dict]:
        """RRF blend of BM25 and actual neural embedding rankings."""
        semantic = self.search_semantic(query, 10)
        lexical = self.search(query, 10)
        fused = reciprocal_rank_fuse([[x["chunk_id"] for x in lexical],
                                      [x["chunk_id"] for x in semantic]])
        hits = {r["chunk_id"]: r for r in semantic + lexical}
        return [{**{k: v for k, v in hits[ident].items() if k not in ("rank", "similarity")},
                 "fusion_score": round(score, 6), "retrieval": "hybrid_semantic"}
                for ident, score in fused[:min(max(limit, 1), 10)]]

    def start_run(self, run_id: str, prompt: str, provider: str, model: str,
                  mode: str = "single") -> None:
        with self.connect() as db:
            db.execute("""INSERT INTO runs(id,prompt,provider,model,status,created_at,mode)
                VALUES (?,?,?,?,?,?,?)""", (run_id, prompt, provider, model, "running", utcnow(), mode))

    def append_event(self, run_id: str, event: dict) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO events(run_id,kind,payload,created_at) VALUES (?,?,?,?)",
                       (run_id, event["type"], json.dumps(event), utcnow()))

    def end_run(self, run_id: str, *, answer: str, status: str, steps: int,
                input_tokens: int, output_tokens: int, duration_ms: int,
                estimated_cost_usd: float | None = None) -> None:
        with self.connect() as db:
            db.execute("""UPDATE runs SET answer=?,status=?,steps=?,input_tokens=?,
                       output_tokens=?,duration_ms=?,estimated_cost_usd=? WHERE id=?""",
                       (answer, status, steps, input_tokens, output_tokens, duration_ms,
                        estimated_cost_usd, run_id))

    def list_runs(self, limit: int = 25) -> list[dict]:
        with self.connect() as db:
            return [dict(x) for x in db.execute(
                "SELECT * FROM runs ORDER BY created_at DESC, rowid DESC LIMIT ?", (min(limit, 100),)
            )]

    def get_run(self, run_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row:
                return None
            result = dict(row)
            result["events"] = [json.loads(x["payload"]) for x in db.execute(
                "SELECT payload FROM events WHERE run_id=? ORDER BY id", (run_id,)
            )]
            return result

    def add_memory(self, title: str, content: str) -> dict:
        """Explicit note creation; no inferred or autonomous writes."""
        title, content = title.strip(), content.strip()
        if not 1 <= len(title) <= 120 or not 1 <= len(content) <= 4000:
            raise ValueError('Memory note exceeds bounds')
        with self.connect() as db:
            cur = db.execute('INSERT INTO memories(title,content,created_at) VALUES (?,?,?)',
                             (title, content, utcnow()))
            db.execute('INSERT INTO memories_fts(memory_id,title,content) VALUES (?,?,?)',
                       (cur.lastrowid, title, content))
            return {'id': cur.lastrowid, 'title': title, 'content': content}

    def list_memories(self, limit: int = 50) -> list[dict]:
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM memories ORDER BY id DESC LIMIT ?',
                       (min(max(limit, 1), 100),))]

    def delete_memory(self, ident: int) -> bool:
        with self.connect() as db:
            db.execute('DELETE FROM memories_fts WHERE memory_id=?', (ident,))
            return db.execute('DELETE FROM memories WHERE id=?', (ident,)).rowcount > 0

    def search_memories(self, query: str, limit: int = 3) -> list[dict]:
        tokens = list(dict.fromkeys(re.findall(r'\w+', query.casefold(), re.UNICODE)))[:15]
        tokens = [x for x in tokens if len(x) > 2]
        if not tokens:
            return []
        phrase = ' OR '.join('"' + x.replace('"', '') + '"' for x in tokens)
        with self.connect() as db:
            return [dict(row) for row in db.execute("""SELECT m.id,m.title,m.content
                FROM memories_fts f JOIN memories m ON m.id=f.memory_id
                WHERE memories_fts MATCH ? ORDER BY bm25(memories_fts) LIMIT ?""",
                (phrase, min(max(limit, 1), 10)))]
