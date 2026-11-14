"use strict";

const state = {
  user: null,
  registerMode: false,
  selectedSubmissionId: null,
  selectedQueueItem: null,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function element(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== "") node.textContent = text;
  return node;
}

function showMessage(target, text, type = "success") {
  target.textContent = text;
  target.className = `message ${type === "error" ? "error" : type === "info" ? "info" : ""}`.trim();
  target.classList.remove("hidden");
}

function clearMessage(target) {
  target.textContent = "";
  target.className = "message hidden";
}

async function api(path, { method = "GET", body, formData } = {}) {
  const options = { method, credentials: "include", headers: { Accept: "application/json" } };
  if (formData) options.body = formData;
  else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error("Could not reach the MediScope API. Check that the backend is running.");
  }

  const contentType = response.headers.get("content-type") || "";
  const result = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    const detail = result?.detail;
    throw new Error(Array.isArray(detail) ? detail.map((item) => item.msg).join("; ") : detail || `Request failed (${response.status}).`);
  }
  return result;
}

function setBusy(button, busy, label) {
  if (!button.dataset.originalLabel) button.dataset.originalLabel = button.textContent.trim();
  button.disabled = busy;
  button.textContent = busy ? label : button.dataset.originalLabel;
}

function setAuthMode(registerMode) {
  state.registerMode = registerMode;
  $("#showLogin").classList.toggle("is-active", !registerMode);
  $("#showRegister").classList.toggle("is-active", registerMode);
  $("#showLogin").setAttribute("aria-selected", String(!registerMode));
  $("#showRegister").setAttribute("aria-selected", String(registerMode));
  $("#displayNameField").classList.toggle("hidden", !registerMode);
  $("#displayName").required = registerMode;
  $("#password").autocomplete = registerMode ? "new-password" : "current-password";
  $("#authTitle").textContent = registerMode ? "Create your account" : "Welcome back";
  $("#authDescription").textContent = registerMode
    ? "Create a regular account to ask questions and submit sources."
    : "Sign in to ask a question or submit a source.";
  $("#authSubmit").textContent = registerMode ? "Create account" : "Sign in";
  clearMessage($("#authMessage"));
}

function showSignedOut(message = "") {
  state.user = null;
  $("#workspace").classList.add("hidden");
  $("#accountBar").classList.add("hidden");
  $("#authScreen").classList.remove("hidden");
  if (message) showMessage($("#authMessage"), message, "info");
}

function showSignedIn(user) {
  state.user = user;
  $("#authScreen").classList.add("hidden");
  $("#workspace").classList.remove("hidden");
  $("#accountBar").classList.remove("hidden");
  $("#accountName").textContent = user.display_name || user.email;
  $("#welcomeTitle").textContent = `Good to see you${user.display_name ? `, ${user.display_name}` : ""}`;
  $("#roleBadge").textContent = user.role === "admin" ? "ADMIN" : "USER";
  $("#adminNav").classList.toggle("hidden", user.role !== "admin");
  goToPage("askPage");
}

function goToPage(pageId) {
  if (pageId === "adminPage" && state.user?.role !== "admin") return;
  $$(".page-section").forEach((section) => section.classList.toggle("hidden", section.id !== pageId));
  $$(".nav-button").forEach((button) => button.classList.toggle("is-active", button.dataset.page === pageId));
  if (pageId === "submissionsPage") loadMySubmissions();
  if (pageId === "adminPage") loadAdminDashboard();
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}

function renderReferences(references) {
  const list = $("#referenceList");
  list.replaceChildren();
  if (!references.length) {
    list.append(element("p", "empty-state", "No source passages were retrieved for this answer."));
    return;
  }

  for (const reference of references) {
    const card = element("article", "reference-card");
    const top = element("div", "reference-top");
    const detail = element("div");
    detail.append(element("span", "reference-id", reference.reference_id));
    detail.append(element("h4", "reference-title", reference.document_title || "Untitled source"));
    const page = reference.page_number ? `Page ${reference.page_number}` : "Page not provided";
    detail.append(element("p", "reference-meta", `${page} · Passage ${reference.passage_id || "not provided"}`));
    top.append(detail);
    const score = Number(reference.similarity_score);
    top.append(element("span", "similarity", `Similarity ${Number.isFinite(score) ? score.toFixed(3) : "n/a"}`));
    card.append(top);
    card.append(element("p", "reference-excerpt", reference.excerpt || "No excerpt provided."));
    const sourceUrl = safeUrl(reference.source || "");
    if (sourceUrl) {
      const source = element("a", "reference-source", "Open source ↗");
      source.href = sourceUrl;
      source.target = "_blank";
      source.rel = "noreferrer";
      card.append(source);
    }
    list.append(card);
  }
}

function renderAnswer(result) {
  $("#answerPanel").classList.remove("hidden");
  $("#answerText").textContent = result.answer || "MediScope did not return an answer.";
  $("#routeBadge").textContent = (result.route || "UNKNOWN").replaceAll("_", " ");
  const status = $("#answerStatus");
  status.replaceChildren();
  if (result.safety_response) {
    status.append(element("span", "status-pill danger", "Safety guidance"));
  } else if (result.fallback) {
    status.append(element("span", "status-pill warning", "Not enough source evidence"));
  } else {
    status.append(element("span", "status-pill", "Answer grounded in retrieved sources"));
  }
  renderReferences(result.references || []);
}

async function handleQuestion(event) {
  event.preventDefault();
  const button = $("#askButton");
  const message = $("#answerMessage");
  clearMessage(message);
  $("#answerPanel").classList.add("hidden");
  setBusy(button, true, "Searching sources…");
  try {
    // Normal users send only their question. The document_id filter stays optional in the API.
    const result = await api("/api/questions", {
      method: "POST",
      body: { question: $("#questionInput").value.trim() },
    });
    renderAnswer(result);
  } catch (error) {
    showMessage(message, error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function handleUpload(event) {
  event.preventDefault();
  const button = $("#uploadButton");
  const message = $("#uploadMessage");
  clearMessage(message);
  const file = $("#uploadFile").files[0];
  if (!file) return showMessage(message, "Choose a PDF or TXT file first.", "error");
  const form = new FormData();
  form.append("file", file);
  form.append("title", $("#uploadTitle").value.trim());
  form.append("source_url", $("#sourceUrl").value.trim());
  form.append("scope_reason", $("#scopeReason").value.trim());
  form.append("reveal_identity", $("input[name='reveal_identity']:checked").value);
  setBusy(button, true, "Uploading and checking text…");
  try {
    const result = await api("/api/documents/submissions", { method: "POST", formData: form });
    showMessage(message, `${result.message} Submission ID: ${result.submission_id}. ${result.identity_note || ""}`);
    $("#uploadForm").reset();
    $("input[name='reveal_identity'][value='false']").checked = true;
  } catch (error) {
    showMessage(message, error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

function statusClass(status) {
  if (status === "APPROVED") return "approved";
  if (status === "REJECTED") return "rejected";
  if (status === "PENDING_ADMIN_REVIEW" || status === "NEEDS_REVISION") return "pending";
  return "";
}

function prettyStatus(status) {
  return (status || "UNKNOWN").replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

async function loadMySubmissions() {
  const list = $("#mySubmissionList");
  const message = $("#submissionsMessage");
  clearMessage(message);
  list.replaceChildren(element("p", "loading", "Loading your submissions…"));
  try {
    const result = await api("/api/documents/submissions");
    list.replaceChildren();
    if (!result.items?.length) {
      list.append(element("div", "card empty-state", "You have not submitted any documents yet."));
      return;
    }
    for (const item of result.items) {
      const card = element("article", "submission-card");
      const details = element("div");
      details.append(element("h3", "", item.title || item.file_name || "Untitled submission"));
      details.append(element("p", "", `${item.file_name || "File"} · Submitted ${formatDate(item.submitted_at)}`));
      if (item.review?.decision_reason) details.append(element("p", "review-reason", item.review.decision_reason));
      const side = element("div", "submission-side");
      side.append(element("span", "status-chip " + statusClass(item.status), prettyStatus(item.status)));
      side.append(element("span", "submission-identity", item.identity_choice === "REVEAL" ? "Identity revealed to admins" : "Shown as anonymous"));
      card.append(details, side);
      list.append(card);
    }
  } catch (error) {
    list.replaceChildren();
    showMessage(message, error.message, "error");
  }
}

function formatDate(value) {
  if (!value) return "date unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

async function loadAdminDashboard() {
  const message = $("#adminMessage");
  clearMessage(message);
  try {
    const [dashboard, queue] = await Promise.all([
      api("/api/admin/dashboard"),
      api(`/api/admin/document-submissions?status=${encodeURIComponent($("#queueStatus").value)}`),
    ]);
    renderDashboard(dashboard);
    renderQueue(queue.items || []);
  } catch (error) {
    showMessage(message, error.message, "error");
  }
}

function renderDashboard(data) {
  const cards = $("#dashboardCards");
  cards.replaceChildren();
  const values = [
    ["Approved documents", data.documents?.approved ?? 0],
    ["Pending submissions", data.submissions?.pending_review ?? 0],
    ["Stored passages", data.stored_passages ?? 0],
    ["Active search index", data.active_tfidf_index ? "Ready" : "Not built"],
  ];
  for (const [label, value] of values) {
    const card = element("div", "dashboard-card");
    card.append(element("span", "", label), element("strong", "", String(value)));
    cards.append(card);
  }
}

function renderQueue(items) {
  const list = $("#adminSubmissionList");
  list.replaceChildren();
  if (!items.length) {
    list.append(element("div", "empty-state", "No submissions in this status."));
    return;
  }
  for (const item of items) {
    const button = element("button", `admin-list-item${item.submission_id === state.selectedSubmissionId ? " is-selected" : ""}`);
    button.type = "button";
    button.dataset.submissionId = item.submission_id;
    button.append(element("strong", "", item.title || item.file_name || "Untitled submission"));
    const submitter = item.identity_choice === "REVEAL" ? item.submitter?.display_name || item.submitter?.email || "Identity revealed" : "Anonymous";
    button.append(element("span", "", `${prettyStatus(item.status)} · ${submitter}`));
    button.addEventListener("click", () => loadSubmission(item.submission_id));
    list.append(button);
  }
}

async function loadSubmission(submissionId) {
  state.selectedSubmissionId = submissionId;
  const panel = $("#reviewPanel");
  panel.replaceChildren(element("p", "loading", "Loading submission…"));
  try {
    const item = await api(`/api/admin/document-submissions/${encodeURIComponent(submissionId)}`);
    state.selectedQueueItem = item;
    renderSubmissionReview(item);
    $$(".admin-list-item").forEach((button) => button.classList.toggle("is-selected", button.dataset.submissionId === item.submission_id));
  } catch (error) {
    panel.replaceChildren();
    showMessage($("#adminMessage"), error.message, "error");
  }
}

function renderSubmissionReview(item) {
  const panel = $("#reviewPanel");
  panel.replaceChildren();
  const overview = element("div", "review-overview");
  overview.append(element("span", "status-chip " + statusClass(item.status), prettyStatus(item.status)));
  overview.append(element("h3", "", item.metadata?.title || item.file?.file_name || "Untitled submission"));
  overview.append(element("p", "", `File: ${item.file?.file_name || "unknown"} · ${item.file?.size_bytes ? `${(item.file.size_bytes / 1024 / 1024).toFixed(2)} MB` : "size unavailable"}`));
  const visibleIdentity = item.identity_choice === "REVEAL"
    ? `${item.submitter?.display_name || ""}${item.submitter?.email ? ` · ${item.submitter.email}` : ""}`
    : "Anonymous to the admin review API (account linkage is private).";
  overview.append(element("p", "", `Submitter: ${visibleIdentity}`));
  if (item.metadata?.full_text_url) {
    const url = safeUrl(item.metadata.full_text_url);
    if (url) {
      const link = element("a", "reference-source", "Open supplied source URL ↗");
      link.href = url;
      link.target = "_blank";
      link.rel = "noreferrer";
      overview.append(link);
    }
  }
  panel.append(overview);
  const tools = element("div", "review-tools");
  const download = element("button", "button button-secondary button-small", "Download original PDF/TXT");
  download.type = "button";
  download.addEventListener("click", () => downloadSubmissionFile(item));
  tools.append(download);
  if (item.extraction?.status) tools.append(element("span", "status-chip", `Text check: ${item.extraction.status}`));
  if (item.extraction?.page_count) tools.append(element("span", "status-chip", `${item.extraction.page_count} pages`));
  panel.append(tools);

  if (item.review) {
    const saved = element("div", "card-body");
    saved.append(element("h4", "", `Saved decision: ${prettyStatus(item.review.decision)}`));
    saved.append(element("p", "muted small", item.review.decision_reason || "No decision reason recorded."));
    panel.append(saved);
  }
  if (["APPROVED", "REJECTED"].includes(item.status)) return;
  buildReviewForm(panel, item);
}

async function downloadSubmissionFile(item) {
  const message = $("#adminMessage");
  clearMessage(message);
  try {
    const response = await fetch(`/api/admin/document-submissions/${encodeURIComponent(item.submission_id)}/file`, { credentials: "include" });
    if (!response.ok) {
      const result = await response.json().catch(() => ({}));
      throw new Error(result.detail || `Download failed (${response.status}).`);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = element("a");
    anchor.href = url;
    anchor.download = item.file?.file_name || "submitted-document";
    anchor.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    showMessage(message, error.message, "error");
  }
}

const documentFields = [
  ["document_id", "Document ID", "text", true],
  ["version", "Version", "text", true],
  ["title", "Title", "text", true],
  ["authors_or_organization", "Authors or organization", "text", true],
  ["publication_date", "Publication date", "text", true],
  ["publisher_or_journal", "Publisher or journal", "text", true],
  ["document_type", "Document type", "text", true],
  ["source_locator", "Source locator / DOI", "text", true],
  ["full_text_url", "Full-text URL", "url", true],
  ["full_text_access_checked_on", "Access checked on", "date", true],
  ["license_or_permission", "License or permission", "text", true],
  ["permission_evidence_url", "License evidence URL", "url", true],
  ["permission_conditions", "Attribution / reuse conditions", "textarea", true],
  ["scope_reason", "Why this document is in scope", "textarea", true],
];

const checkGroups = [
  {
    id: "access_reuse",
    title: "Free access and reuse permission",
    help: "Check the full-text source and the document-specific license.",
    checks: ["free_online_access", "reuse_permission"],
  },
  {
    id: "identity_scope",
    title: "Identity, scope, and publication",
    help: "Confirm the authors/source, relevance, and publication status.",
    checks: ["traceable_identity", "scope_and_document_type", "publication_status"],
  },
  {
    id: "usability_privacy",
    title: "File usability and privacy",
    help: "Check text readability and that the file contains no private patient records.",
    checks: ["file_usability_and_privacy"],
  },
];

function slugify(text) {
  return (text || "medical-document").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 55) || "medical-document";
}

function buildReviewForm(panel, item) {
  const form = element("form", "review-form form-stack");
  form.id = "adminReviewForm";
  const info = element("p", "muted small", "Complete the document details and three clear review groups. MediScope converts the groups into its six required checks. The server fills in the reviewer, date, and file hash.");
  form.append(info);
  form.append(element("p", "muted small", "For NEEDS REVISION or REJECTED, only the basic document details and short review notes are needed. Full document details are required only for approval."));

  const details = element("details", "review-details");
  details.open = true;
  details.append(element("summary", "", "Document details and evidence"));
  const fields = element("div", "review-fields");
  const initial = item.metadata || {};
  const suffix = item.submission_id.slice(-6);
  const initialValues = {
    document_id: `${slugify(initial.title)}-${suffix}`,
    version: "1",
    title: initial.title || "",
    authors_or_organization: "",
    publication_date: "",
    publisher_or_journal: "",
    document_type: "",
    source_locator: initial.source_locator || "",
    full_text_url: initial.full_text_url || "",
    full_text_access_checked_on: new Date().toISOString().slice(0, 10),
    license_or_permission: "",
    permission_evidence_url: "",
    permission_conditions: "",
    scope_reason: initial.scope_reason || "",
  };

  for (const [name, label, type, required] of documentFields) {
    const wrapper = element("label", `review-field${type === "textarea" ? " wide" : ""}`);
    const alwaysRequired = ["document_id", "version", "title"].includes(name);
    wrapper.append(element("span", "", `${label}${alwaysRequired ? " *" : ""}`));
    const input = type === "textarea" ? element("textarea") : element("input");
    if (type !== "textarea") input.type = type;
    input.dataset.documentField = name;
    input.value = initialValues[name] || "";
    input.required = ["document_id", "version", "title"].includes(name);
    input.maxLength = 2000;
    wrapper.append(input);
    fields.append(wrapper);
  }
  const hashNote = element("p", "muted small wide", "File SHA-256 is computed and inserted by the backend from this exact upload.");
  fields.append(hashNote);
  details.append(fields);
  form.append(details);

  const checks = element("div", "review-checks");
  for (const group of checkGroups) {
    const section = element("section", "check-group");
    section.append(element("h4", "", group.title), element("p", "", group.help));
    const row = element("div", "check-row");
    const select = element("select");
    select.dataset.checkStatus = group.id;
    select.required = true;
    select.append(new Option("Choose result…", ""));
    for (const value of ["PASS", "NEEDS_INFORMATION", "FAIL", "NOT_APPLICABLE"]) {
      select.append(new Option(value.replaceAll("_", " "), value));
    }
    const note = element("textarea");
    note.dataset.checkNote = group.id;
    note.required = true;
    note.maxLength = 2000;
    note.placeholder = "Write a short note explaining what you checked or what is missing";
    row.append(select, note);
    section.append(row);
    checks.append(section);
  }
  form.append(checks);

  const decision = element("div", "decision-row");
  const decisionLabel = element("label", "review-field");
  decisionLabel.append(element("span", "", "Admin decision *"));
  const decisionSelect = element("select");
  decisionSelect.dataset.decision = "true";
  decisionSelect.required = true;
  decisionSelect.append(new Option("Choose decision…", ""));
  for (const value of ["APPROVED", "NEEDS_REVISION", "REJECTED"]) decisionSelect.append(new Option(value.replaceAll("_", " "), value));
  decisionLabel.append(decisionSelect);
  const reasonLabel = element("label", "review-field");
  reasonLabel.append(element("span", "", "Decision reason *"));
  const reason = element("textarea");
  reason.dataset.decisionReason = "true";
  reason.required = true;
  reason.maxLength = 2000;
  reason.placeholder = "Briefly explain the decision";
  reasonLabel.append(reason);
  const submit = element("button", "button button-primary", "Save admin decision");
  submit.type = "submit";
  decision.append(decisionLabel, reasonLabel, submit);
  form.append(decision);
  decisionSelect.addEventListener("change", () => {
    $$("[data-document-field]", form).forEach((input) => {
      input.required = decisionSelect.value === "APPROVED" || ["document_id", "version", "title"].includes(input.dataset.documentField);
    });
  });

  decisionSelect.addEventListener("change", () => {
    fields.querySelectorAll("label.review-field").forEach((wrapper) => {
      const input = wrapper.querySelector("[data-document-field]");
      if (!input) return;
      const label = wrapper.querySelector("span");
      const base = label.textContent.replace(/\s+\*$/, "");
      label.textContent = `${base}${input.required ? " *" : ""}`;
    });
  });

  const preview = element("details", "review-preview");
  preview.append(element("summary", "", "Review JSON preview"));
  const pre = element("pre");
  pre.dataset.reviewPreview = "true";
  pre.textContent = "Fill in the form to preview the review record.";
  preview.append(pre);
  form.append(preview);
  form.addEventListener("input", updateReviewPreview);
  form.addEventListener("change", updateReviewPreview);
  form.addEventListener("submit", handleAdminDecision);
  panel.append(form);
}

function gatherReviewPayload() {
  const form = $("#adminReviewForm");
  if (!form) throw new Error("Review form is not available.");
  const documentData = {};
  $$('[data-document-field]', form).forEach((input) => { documentData[input.dataset.documentField] = input.value.trim(); });
  documentData.file_sha256 = "";
  const checks = {};
  for (const group of checkGroups) {
    const status = $(`[data-check-status='${group.id}']`, form).value;
    const note = $(`[data-check-note='${group.id}']`, form).value.trim();
    for (const checkName of group.checks) checks[checkName] = { status, note };
  }
  return {
    document: documentData,
    reviewer_id: "",
    reviewed_at: new Date().toISOString().slice(0, 10),
    decision: $("[data-decision='true']", form).value,
    decision_reason: $("[data-decision-reason='true']", form).value.trim(),
    checks,
    ai_screening_report: null,
  };
}

function updateReviewPreview() {
  const target = $("[data-review-preview='true']");
  if (!target) return;
  try { target.textContent = JSON.stringify(gatherReviewPayload(), null, 2); }
  catch { target.textContent = "Complete the form to preview the review record."; }
}

async function handleAdminDecision(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = $("button[type='submit']", form);
  const message = $("#adminMessage");
  clearMessage(message);
  const payload = gatherReviewPayload();
  const statusValues = Object.values(payload.checks).map((item) => item.status);
  if (payload.decision === "APPROVED" && statusValues.some((value) => !["PASS", "NOT_APPLICABLE"].includes(value))) {
    return showMessage(message, "To approve, every review group must be PASS or NOT APPLICABLE. Check the document evidence first.", "error");
  }
  if (payload.decision === "NEEDS_REVISION" && (!statusValues.includes("NEEDS_INFORMATION") || statusValues.includes("FAIL"))) {
    return showMessage(message, "NEEDS_REVISION needs at least one NEEDS_INFORMATION result and no FAIL result.", "error");
  }
  if (payload.decision === "REJECTED" && !statusValues.includes("FAIL")) {
    return showMessage(message, "REJECTED needs at least one failed review group.", "error");
  }
  setBusy(button, true, payload.decision === "APPROVED" ? "Approving and indexing…" : "Saving decision…");
  try {
    const result = await api(`/api/admin/document-submissions/${encodeURIComponent(state.selectedSubmissionId)}/decision`, {
      method: "POST",
      body: payload,
    });
    const processing = result.processing;
    const extra = processing ? ` Added ${processing.passage_count} passages; index ${processing.index_id} is active.` : "";
    showMessage(message, `${result.message}${extra}`);
    await loadAdminDashboard();
    if (state.selectedSubmissionId) await loadSubmission(state.selectedSubmissionId);
  } catch (error) {
    showMessage(message, error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function handleAuth(event) {
  event.preventDefault();
  const button = $("#authSubmit");
  const message = $("#authMessage");
  clearMessage(message);
  const payload = {
    email: $("#email").value.trim(),
    password: $("#password").value,
  };
  setBusy(button, true, state.registerMode ? "Creating account…" : "Signing in…");
  try {
    if (state.registerMode) {
      payload.display_name = $("#displayName").value.trim();
      await api("/api/auth/register", { method: "POST", body: payload });
      setAuthMode(false);
      $("#email").value = payload.email;
      showMessage(message, "Account created. Sign in with your email and password.");
    } else {
      const result = await api("/api/auth/login", { method: "POST", body: payload });
      $("#password").value = "";
      showSignedIn(result.user);
    }
  } catch (error) {
    showMessage(message, error.message, "error");
  } finally {
    setBusy(button, false);
  }
}

async function signOut() {
  try { await api("/api/auth/logout", { method: "POST" }); }
  finally { showSignedOut("You have signed out."); }
}

async function initialize() {
  $("#showLogin").addEventListener("click", () => setAuthMode(false));
  $("#showRegister").addEventListener("click", () => setAuthMode(true));
  $("#authForm").addEventListener("submit", handleAuth);
  $("#logoutButton").addEventListener("click", signOut);
  $("#questionForm").addEventListener("submit", handleQuestion);
  $("#uploadForm").addEventListener("submit", handleUpload);
  $("#refreshSubmissions").addEventListener("click", loadMySubmissions);
  $("#refreshAdmin").addEventListener("click", loadAdminDashboard);
  $("#queueStatus").addEventListener("change", loadAdminDashboard);
  $$(".nav-button").forEach((button) => button.addEventListener("click", () => goToPage(button.dataset.page)));

  try {
    const user = await api("/api/auth/me");
    showSignedIn(user);
  } catch (error) {
    showSignedOut();
    if (!error.message.includes("Sign in")) showMessage($("#authMessage"), error.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", initialize);
