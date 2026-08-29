const BASE = "http://localhost:8000";

export type Status = "ready" | "processing" | "failed";
export interface Folder { id: string; name: string; }
export interface Doc { id: string; name: string; folder: string; date: string; type: string; size: string; status: Status; }
export interface RelatedSource { doc: string; page: number | null; excerpt: string; relevance: number; }
export interface ConflictSource { doc: string; page: number | null; excerpt: string; }
export interface Citation { doc: string; page: number | null; snippet: string; }
export interface Conversation { id: string; title: string; when: string; question: string; }
export interface TraceStep { step: string; label: string; duration_ms: number; result: string; details: Record<string, unknown>; }

export type AskResponse =
  | { type: "confident"; answer: string; citations: Citation[]; related_sources: RelatedSource[]; evidence: Doc[]; trace?: TraceStep[] }
  | { type: "resolved"; conflict_kind: string; answer: string; governing: ConflictSource; superseded: ConflictSource; note: string; related_sources: RelatedSource[]; evidence: Doc[]; trace?: TraceStep[] }
  | { type: "conflict"; conflict_kind: string; question_summary: string; sources: ConflictSource[]; suggestion: string; related_sources: RelatedSource[]; evidence: Doc[]; trace?: TraceStep[] }
  | { type: "not_found"; message: string; related_sources: RelatedSource[]; evidence: Doc[]; trace?: TraceStep[] };

export async function listFolders(): Promise<Folder[]> {
  return (await fetch(`${BASE}/folders`)).json();
}
export async function listDocuments(folderId: string): Promise<Doc[]> {
  return (await fetch(`${BASE}/documents?folder=${encodeURIComponent(folderId)}`)).json();
}
export async function listConversations(): Promise<Conversation[]> {
  return (await fetch(`${BASE}/conversations`)).json();
}
export interface AskResult extends Record<string, unknown> { conversation_id: string; }
export async function ask(
  question: string,
  opts: { scope?: string | null; conversationId?: string | null } = {}
): Promise<AskResponse & { conversation_id: string }> {
  const r = await fetch(`${BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      attachment_id: opts.scope ?? null,        // scope retrieval to one document
      conversation_id: opts.conversationId ?? null,  // continue an existing chat thread
    }),
  });
  return r.json();
}

export async function uploadDocument(file: File, folder?: string) {
  const fd = new FormData();
  fd.append("file", file);
  if (folder) fd.append("folder", folder);
  const r = await fetch(`${BASE}/ingest`, { method: "POST", body: fd });
  return r.json();
}

export async function createFolder(name: string): Promise<Folder> {
  const r = await fetch(`${BASE}/folders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return r.json();
}

export interface Turn { question: string; response: AskResponse; }
export async function getConversation(id: string): Promise<{ id: string; turns: Turn[] } | null> {
  return (await fetch(`${BASE}/conversations/${id}`)).json();
}

// URL of the raw PDF, for previewing/opening a document
export function fileUrl(name: string): string {
  return `${BASE}/documents/view?name=${encodeURIComponent(name)}`;
}

export async function deleteDocument(name: string): Promise<void> {
  // soft delete → moves to Trash
  await fetch(`${BASE}/documents?name=${encodeURIComponent(name)}`, { method: "DELETE" });
}

export async function listTrash(): Promise<Doc[]> {
  return (await fetch(`${BASE}/trash`)).json();
}

export async function restoreDocument(name: string): Promise<void> {
  await fetch(`${BASE}/documents/restore?name=${encodeURIComponent(name)}`, { method: "POST" });
}

export async function purgeDocument(name: string): Promise<void> {
  // permanent delete from Trash
  await fetch(`${BASE}/documents/purge?name=${encodeURIComponent(name)}`, { method: "DELETE" });
}

export async function deleteFolder(id: string): Promise<void> {
  await fetch(`${BASE}/folders/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
}