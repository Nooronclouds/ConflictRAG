// ConflictRAG — Librarian shell
import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { Icon } from "./Icon";
import * as api from "./api";
import type { AskResponse, Conversation, Doc, Folder, TraceStep } from "./api";

type MidView = "folder" | "recent" | "trash" | "search" | "answer" | "doc";

export default function App() {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [allDocs, setAllDocs] = useState<Doc[]>([]);
  const [trashDocs, setTrashDocs] = useState<Doc[]>([]);
  const [currentFolder, setCurrentFolder] = useState("");
  const [midView, setMidView] = useState<MidView>("folder");
  const [turns, setTurns] = useState<{ question: string; answer: AskResponse }[]>([]);
  const [pending, setPending] = useState<string | null>(null);
  const [convId, setConvId] = useState<string | null>(null);
  const [scope, setScope] = useState<string | null>(null);   // ask about ONE document
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  const [highlight, setHighlight] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [folderModal, setFolderModal] = useState(false);
  const [folderName, setFolderName] = useState("");
  const [uploading, setUploading] = useState<string | null>(null);
  const [restoring, setRestoring] = useState<string | null>(null);
  const [viewDoc, setViewDoc] = useState<{ name: string; page?: number } | null>(null);
  const [docReturn, setDocReturn] = useState<MidView>("folder");
  const [confirmDel, setConfirmDel] = useState<{ kind: "doc" | "folder" | "chat" | "purge"; id: string; label: string } | null>(null);

  async function refresh() {
    setFolders(await api.listFolders());
    setConversations(await api.listConversations());
    setAllDocs(await api.listDocuments(""));
    setTrashDocs(await api.listTrash());
  }
  useEffect(() => { refresh(); }, []);

  function openFolder(id: string) {
    setCurrentFolder(id); setMidView("folder"); setHighlight(null); setSearch(""); setScope(null);
  }
  function openView(v: MidView) { setMidView(v); setHighlight(null); setScope(null); }

  function onSearch(q: string) { setSearch(q); setMidView(q ? "search" : "folder"); setScope(null); }

  async function runAsk(text: string) {
    if (!text.trim() || busy) return;
    setBusy(true);
    setInput(""); setPending(text);
    // keep the PDF open if the question is scoped to it; otherwise show evidence
    setMidView((v) => (v === "doc" ? "doc" : "answer"));
    try {
      const res = await api.ask(text, { scope, conversationId: convId });
      setConvId(res.conversation_id);
      setTurns((t) => [...t, { question: text, answer: res }]);
      setHighlight(res.evidence?.[0]?.folder ?? null);
      setConversations(await api.listConversations());
    } catch {
      setTurns((t) => [...t, { question: text, answer: { type: "not_found", message: "Couldn't reach the server — is the backend running on :8000?", related_sources: [], evidence: [] } }]);
    } finally {
      setPending(null); setBusy(false);
    }
  }

  function newChat() {
    setTurns([]); setPending(null); setConvId(null); setScope(null);
    setMidView("folder"); setHighlight(null);
  }

  const fileRef = useRef<HTMLInputElement>(null);
  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const files = e.target.files; if (!files) return;
    const list = Array.from(files);
    try {
      for (let i = 0; i < list.length; i++) {
        setUploading(`Processing ${list[i].name} (${i + 1}/${list.length})… reading, chunking & embedding`);
        await api.uploadDocument(list[i], currentFolder || undefined);
      }
    } finally {
      e.target.value = "";
      setUploading(null);
      await refresh();
    }
  }

  // open a document IN THE MIDDLE PANE (remember where to go back to)
  // and scope the Librarian to it so follow-up questions are about THIS doc
  function openViewer(name: string, page?: number) {
    setDocReturn(midView === "doc" ? docReturn : midView);
    setViewDoc({ name, page });
    setMidView("doc");
    setScope(name);
  }
  function closeViewer() { setViewDoc(null); setScope(null); setMidView(docReturn); }

  async function doDelete() {
    if (!confirmDel) return;
    const { kind, id } = confirmDel;
    if (kind === "doc") await api.deleteDocument(id);            // soft → Trash
    else if (kind === "purge") await api.purgeDocument(id);      // permanent
    else if (kind === "chat") {
      await api.deleteConversation(id);
      if (convId === id) newChat();
    } else {
      await api.deleteFolder(id);
      if (currentFolder === id) openFolder("");
    }
    setConfirmDel(null);
    await refresh();
  }

  async function restoreDoc(name: string) {
    if (restoring) return;
    setRestoring(name);              // re-indexing the PDF takes a few seconds
    try { await api.restoreDocument(name); }
    finally { setRestoring(null); await refresh(); }
  }

  async function confirmFolder() {
    if (folderName.trim()) { await api.createFolder(folderName.trim()); await refresh(); }
    setFolderModal(false); setFolderName("");
  }

  // open a SAVED chat (loads ALL its turns — does NOT re-run the pipeline)
  async function openConversation(id: string) {
    const conv = await api.getConversation(id);
    if (!conv || !conv.turns?.length) return;
    setTurns(conv.turns.map((t) => ({ question: t.question, answer: t.response })));
    setConvId(id); setPending(null); setScope(null);
    setMidView("answer");
    const last = conv.turns[conv.turns.length - 1].response;
    setHighlight(last.evidence?.[0]?.folder ?? null);
  }

  // ---- derive the middle pane from the current view ----
  const inAnswer = midView === "answer";
  const inChat = turns.length > 0 || pending !== null;   // right pane shows the thread
  const lastAnswer = turns.length ? turns[turns.length - 1].answer : null;
  let midDocs: Doc[] = [];
  let midLabel = "Knowledge base";
  let emptyMsg = "";
  if (midView === "answer") { midDocs = lastAnswer?.evidence ?? []; midLabel = "Evidence for your question"; emptyMsg = "No source documents."; }
  else if (midView === "recent") { midDocs = allDocs; midLabel = "Recent files"; emptyMsg = "No files yet."; }
  else if (midView === "trash") { midDocs = trashDocs; midLabel = "Trash"; emptyMsg = "Trash is empty."; }
  else if (midView === "search") {
    const q = search.toLowerCase();
    midDocs = allDocs.filter((d) => d.name.toLowerCase().includes(q));
    midLabel = `Search: "${search}"`; emptyMsg = `No documents match "${search}".`;
  } else {
    midDocs = currentFolder ? allDocs.filter((d) => d.folder === currentFolder) : allDocs;
    midLabel = folders.find((f) => f.id === currentFolder)?.name ?? "Knowledge base";
  }
  const showOnboarding = midView === "folder" && midDocs.length === 0;

  const nav = (kind: string, id = "") => {
    if (highlight && kind === "folder" && highlight === id) return "hl";
    if (inAnswer) return "";
    if (kind === "root" && midView === "folder" && currentFolder === "") return "sel";
    if (kind === "folder" && midView === "folder" && currentFolder === id) return "sel";
    if (kind === "recent" && midView === "recent") return "sel";
    if (kind === "trash" && midView === "trash") return "sel";
    return "";
  };

  return (
    <div className="win">
      <input ref={fileRef} type="file" multiple style={{ display: "none" }} onChange={handleUpload} />

      {folderModal && (
        <div className="modal-overlay" onClick={() => { setFolderModal(false); setFolderName(""); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">New folder</div>
            <input
              autoFocus className="modal-input" placeholder="Folder name"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") confirmFolder(); if (e.key === "Escape") { setFolderModal(false); setFolderName(""); } }}
            />
            <div className="modal-actions">
              <button className="tb-btn" onClick={() => { setFolderModal(false); setFolderName(""); }}>Cancel</button>
              <button className="tb-btn primary" onClick={confirmFolder}>Create</button>
            </div>
          </div>
        </div>
      )}

      <div className="topchrome">
        <div className="toolbar">
          <button className="tb-ico" title="Back" onClick={() => openFolder("")}><Icon name="back" /></button>
          <button className="tb-ico" title="Forward" onClick={() => openFolder("")}><Icon name="fwd" /></button>
          <button className="tb-ico" title="Up to Knowledge base" onClick={() => openFolder("")}><Icon name="up" /></button>
          <div className="sep" />
          <button className="tb-btn primary" onClick={() => fileRef.current?.click()}><Icon name="up" /> Upload</button>
          <button className="tb-btn" onClick={() => setFolderModal(true)}><Icon name="new" /> New folder</button>
          <div className="sep" />
          <button className="tb-btn"><Icon name="sort" /> Sort <Icon name="chevd" size={12} /></button>
          <button className="tb-btn"><Icon name="view" /> View <Icon name="chevd" size={12} /></button>
          <div className="grow" />
          <button className="tb-btn" onClick={newChat}><Icon name="robot" /> Librarian</button>
        </div>
        <div className="addr-row">
          <div className="crumb">
            <Icon name="folder" color="#eab000" /> Knowledge base <Icon name="chev" size={13} /> <span className="cur">{midLabel}</span>
          </div>
          <div className="search">
            <Icon name="search" />
            <input placeholder="Search knowledge base…" value={search} onChange={(e) => onSearch(e.target.value)} />
          </div>
        </div>
      </div>

      <div className="body">
        <nav className="nav">
          <div className={`nav-item ${nav("home")}`} onClick={() => openFolder("")}><Icon name="home" /> Home</div>
          <div className="nav-sec">This PC — Knowledge base</div>
          <div className={`nav-item ${nav("root")}`} onClick={() => openFolder("")}>
            <Icon name="chevd" size={12} /><Icon name="folder" className="fold" /> Knowledge base
          </div>
          {folders.length === 0 && <div className="nav-item sub" style={{ color: "var(--hint)" }}>No folders yet</div>}
          {folders.map((f) => (
            <div key={f.id} className={`nav-item sub ${nav("folder", f.id)}`} onClick={() => openFolder(f.id)}>
              <Icon name="folder" className="fold" /> <span className="grow">{f.name}</span>
              <button className="row-del" title="Delete folder"
                onClick={(e) => { e.stopPropagation(); setConfirmDel({ kind: "folder", id: f.id, label: f.name }); }}>
                <Icon name="trash" size={14} />
              </button>
            </div>
          ))}
          <div className="nav-sec">Library</div>
          <div className={`nav-item ${nav("recent")}`} onClick={() => openView("recent")}><Icon name="hist" /> Recent files</div>
          <div className={`nav-item ${nav("trash")}`} onClick={() => openView("trash")}><Icon name="file" /> Trash</div>
        </nav>

        <section className="mid">
          {midView === "doc" && viewDoc ? (
            <>
              <div className="mid-head">
                <span className="lbl" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <button className="tb-btn" onClick={closeViewer}><Icon name="back" size={14} /> Back</button>
                  <Icon name="file" className="doc" size={15} />
                  {viewDoc.name}{viewDoc.page ? ` — page ${viewDoc.page}` : ""}
                </span>
                <a className="tb-btn" href={api.fileUrl(viewDoc.name)} target="_blank" rel="noreferrer"><Icon name="open" size={14} /> Open in browser</a>
              </div>
              <iframe
                className="doc-frame"
                src={api.fileUrl(viewDoc.name) + (viewDoc.page ? `#page=${viewDoc.page}` : "")}
                title={viewDoc.name}
              />
            </>
          ) : (
          <>
          <div className="mid-head"><span className="lbl">{midLabel}</span><span>{midDocs.length} items</span></div>
          {uploading && (
            <div className="uploading"><span className="spin" /> {uploading}</div>
          )}
          {restoring && (
            <div className="uploading"><span className="spin" /> Restoring {restoring}… re-indexing the document</div>
          )}
          {showOnboarding ? (
            <div className="empty">
              <Icon name="folder" size={64} className="big" />
              <h3>Your knowledge base is empty</h3>
              <div>Add documents to begin — the Librarian answers only from what's here.</div>
              <div className="drop">Drag files or a folder here</div>
              <button className="btn-accent" onClick={() => fileRef.current?.click()}><Icon name="up" /> Upload documents</button>
            </div>
          ) : midDocs.length === 0 ? (
            <div className="empty"><Icon name="file" size={48} className="big" /><div>{emptyMsg}</div></div>
          ) : (
            <>
              <div className="cols"><div>Name <Icon name="chevd" size={12} /></div><div>Date modified</div><div>Type</div><div>Size</div><div>Status</div></div>
              <div className="rows">
                {midDocs.map((d) => (
                  <div className="row" key={d.id} onClick={() => openViewer(d.name)} title="Click to view">
                    <div className="nm"><Icon name="file" className="doc" /><span>{d.name}</span></div>
                    <div className="c">{d.date}</div><div className="c">{d.type}</div><div className="c">{d.size}</div>
                    <div className="statuscell">
                      <span className={`badge ${d.status === "ready" ? "ok" : "warn"}`}>{d.status}</span>
                      {midView === "trash" ? (
                        <span className="row-actions">
                          <button className="row-del" title="Restore" disabled={restoring === d.name}
                            onClick={(e) => { e.stopPropagation(); restoreDoc(d.name); }}>
                            {restoring === d.name ? <span className="spin" /> : <Icon name="refresh" size={14} />}
                          </button>
                          <button className="row-del danger" title="Delete permanently"
                            onClick={(e) => { e.stopPropagation(); setConfirmDel({ kind: "purge", id: d.name, label: d.name }); }}>
                            <Icon name="trash" size={14} />
                          </button>
                        </span>
                      ) : (
                        <button className="row-del" title="Move to Trash"
                          onClick={(e) => { e.stopPropagation(); setConfirmDel({ kind: "doc", id: d.name, label: d.name }); }}>
                          <Icon name="trash" size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
          </>
          )}
        </section>

        <aside className="lib">
          <div className="lib-head">
            <span className="robot"><Icon name="robot" /></span>
            <div><div className="lib-title">Librarian</div><div className="lib-sub">Conflict-aware · answers only from your KB</div></div>
            <div className="lib-tool">
              <button className="tb-ico" title="Chat history" onClick={newChat}><Icon name="hist" /></button>
              <button className="tb-ico" title="New chat" onClick={newChat}><Icon name="new" /></button>
            </div>
          </div>

          <div className="lib-body">
            {!inChat ? (
              <>
                <button className="newchat" onClick={newChat}><Icon name="new" size={14} /> New chat</button>
                <div className="hsec">Recent chats</div>
                {conversations.length === 0 && <div className="idle-hint" style={{ textAlign: "left" }}>No chats yet.</div>}
                {conversations.map((c) => (
                  <div className="hitem" key={c.id} onClick={() => openConversation(c.id)}>
                    <Icon name="hist" size={14} color="var(--hint)" />
                    <span className="htitle">{c.title}</span>
                    <span className="tm">{c.when}</span>
                    <button className="row-del" title="Delete chat"
                      onClick={(e) => { e.stopPropagation(); setConfirmDel({ kind: "chat", id: c.id, label: c.title }); }}>
                      <Icon name="trash" size={13} />
                    </button>
                  </div>
                ))}
                <div className="idle-hint">Ask a question, or open a folder to browse.<br />Answers cite the documents they came from.</div>
              </>
            ) : (
              <>
                {turns.map((t, i) => (
                  <div key={i} className="turn">
                    <div className="q"><span>{t.question}</span></div>
                    <AnswerCard res={t.answer} onOpenDoc={openViewer} />
                  </div>
                ))}
                {pending !== null && (
                  <div className="turn">
                    <div className="q"><span>{pending}</span></div>
                    <div className="idle-hint">Thinking…</div>
                  </div>
                )}
              </>
            )}
          </div>

          {scope && (
            <div className="scope-chip">
              <Icon name="file" size={13} className="doc" />
              <span>Asking about <b>{scope}</b></span>
              <button className="icon-btn" title="Ask the whole knowledge base instead" onClick={() => setScope(null)}><Icon name="close" size={13} /></button>
            </div>
          )}
          <form className="lib-input" onSubmit={(e) => { e.preventDefault(); runAsk(input); }}>
            <button type="button" className="icon-btn" title="Attach a document" onClick={() => fileRef.current?.click()}><Icon name="clip" /></button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={scope ? `Ask about ${scope}…` : "Ask about your knowledge base…"}
            />
            <button type="submit" className="icon-btn primary"><Icon name="send" /></button>
          </form>
        </aside>
      </div>

      {confirmDel && (
        <div className="modal-overlay" onClick={() => setConfirmDel(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">
              {confirmDel.kind === "folder" ? "Delete folder?"
                : confirmDel.kind === "chat" ? "Delete chat?"
                : confirmDel.kind === "purge" ? "Delete permanently?"
                : "Move to Trash?"}
            </div>
            <div className="note" style={{ marginBottom: 14 }}>
              {confirmDel.kind === "folder"
                ? <>“{confirmDel.label}” will be removed. Any documents inside move back to the Knowledge base root.</>
                : confirmDel.kind === "chat"
                ? <>“{confirmDel.label}” will be permanently deleted from your chat history.</>
                : confirmDel.kind === "purge"
                ? <>“{confirmDel.label}” will be <b>permanently</b> deleted — file and all its data. This can’t be undone.</>
                : <>“{confirmDel.label}” moves to Trash. The Librarian stops using it, but you can restore it later.</>}
            </div>
            <div className="modal-actions">
              <button className="tb-btn" onClick={() => setConfirmDel(null)}>Cancel</button>
              <button className="tb-btn danger" onClick={doDelete}>
                <Icon name="trash" size={14} /> {confirmDel.kind === "doc" ? "Move to Trash" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="status"><span>{midDocs.length} items</span></div>
    </div>
  );
}

function AnswerCard({ res, onOpenDoc }: { res: AskResponse; onOpenDoc: (name: string, page?: number) => void }) {
  return (
    <>
      {res.type === "confident" && (
        <div>
          <div className="tag ok"><Icon name="check" size={13} /> Answer</div>
          <div className="answer">{res.answer}</div>
          {res.citations.length > 0 && (
            <div className="cite-section">
              <div className="cite-label">Sources cited</div>
              <div className="cite-chips">
                {res.citations.map((c, i) => (
                  <span key={i} className="cite-link" onClick={() => onOpenDoc(c.doc.endsWith(".pdf") ? c.doc : c.doc + ".pdf", c.page ?? undefined)}>
                    <Icon name="file" size={13} className="doc" /> {c.doc} <span className="cite-page">p.{c.page}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      {res.type === "resolved" && (
        <div>
          <div className="tag warn">Resolved · revision</div>
          <div className="answer">{res.answer}</div>
          <div className="hist">
            Supersedes{" "}
            <span className="cite-link" onClick={() => onOpenDoc(res.superseded.doc.endsWith(".pdf") ? res.superseded.doc : res.superseded.doc + ".pdf", res.superseded.page ?? undefined)}>
              <span className="strike">{res.superseded.excerpt}</span> · {res.superseded.doc}
            </span>
          </div>
          <div className="cite-section">
            <div className="cite-label">Current source</div>
            <span className="cite-link" onClick={() => onOpenDoc(res.governing.doc.endsWith(".pdf") ? res.governing.doc : res.governing.doc + ".pdf", res.governing.page ?? undefined)}>
              <Icon name="file" size={13} className="doc" /> {res.governing.doc} <span className="cite-page">p.{res.governing.page}</span>
            </span>
          </div>
        </div>
      )}
      {res.type === "conflict" && (
        <div>
          <div className="tag bad">Sources disagree · {res.conflict_kind} conflict</div>
          <div className="note">{res.suggestion}</div>
          {res.sources.map((s, i) => (
            <div className="srccard" key={i} onClick={() => onOpenDoc(s.doc.endsWith(".pdf") ? s.doc : s.doc + ".pdf", s.page ?? undefined)}>
              <div className="v">{s.excerpt}</div>
              <div className="m"><Icon name="file" size={12} className="doc" /> {s.doc} · p.{s.page} <span style={{color: "var(--accent)", fontSize: 11}}>— click to view</span></div>
            </div>
          ))}
        </div>
      )}
      {res.type === "not_found" && (
        <div>
          <div className="tag info">Not in the knowledge base</div>
          <div className="answer">{res.message}</div>
          <button className="cta"><Icon name="up" size={14} /> Add a source</button>
        </div>
      )}
      {res.related_sources.length > 0 && (
        <>
          <div className="rl-t">Related in your knowledge base</div>
          <div className="rl">
            {res.related_sources.map((r, i) => (
              <div className="r" key={i} onClick={() => onOpenDoc(r.doc.endsWith(".pdf") ? r.doc : r.doc + ".pdf", r.page ?? undefined)}>
                <Icon name="file" className="doc" size={15} />
                <span className="rn">{r.doc}<div className="sub2">p.{r.page} · {r.excerpt}</div></span>
                <span className="rel">{r.relevance.toFixed(2)}</span>
                <Icon name="open" size={14} color="var(--accent)" />
              </div>
            ))}
          </div>
        </>
      )}
      {res.trace && res.trace.length > 0 && <TracePanel trace={res.trace} />}
    </>
  );
}

function TracePanel({ trace }: { trace: TraceStep[] }) {
  const [open, setOpen] = useState(false);
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const totalMs = trace.reduce((s, t) => s + t.duration_ms, 0);

  const dotColor = (step: TraceStep) => {
    if (step.step === "detect" && (step.details?.conflicts_found as number) > 0) return "warn";
    if (step.step === "reconcile" && step.details?.resolvable) return "ok";
    if (step.step === "reconcile" && !step.details?.resolvable) return "warn";
    if (step.result === "success") return "ok";
    return "neutral";
  };

  return (
    <div style={{ marginTop: 6 }}>
      <div className="trace-toggle" onClick={() => setOpen(!open)}>
        <Icon name={open ? "chevd" : "chev"} size={12} />
        <span>Agent Trace · {trace.length} steps</span>
        <span className="grow" />
        <span className="trace-dur-total">{totalMs < 1000 ? `${totalMs}ms` : `${(totalMs / 1000).toFixed(1)}s`}</span>
      </div>
      {open && (
        <div className="trace-timeline">
          {trace.map((t, i) => (
            <div className="trace-step" key={i}>
              <div className={`trace-dot ${dotColor(t)}`} />
              <div className="trace-body">
                <div className="trace-label">{t.label}</div>
                <div className="trace-meta">
                  <span className="trace-ms">{t.duration_ms}ms</span>
                  <button className="trace-detail-toggle" onClick={() => setExpandedStep(expandedStep === i ? null : i)}>
                    {expandedStep === i ? "hide details" : "details"}
                  </button>
                </div>
                {expandedStep === i && (
                  <div className="trace-details">{JSON.stringify(t.details, null, 2)}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
