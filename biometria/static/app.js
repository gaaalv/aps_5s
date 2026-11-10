"use strict";
const $ = (selector) => document.querySelector(selector);
const csrf = () => $('meta[name="csrf-token"]').content;
function el(tag, text, className) {
  const item = document.createElement(tag);
  if (text !== undefined) item.textContent = text;
  if (className) item.className = className;
  return item;
}
function notify(message) {
  const box = $("#toast"); box.textContent = message; box.hidden = false;
  window.clearTimeout(notify.timer); notify.timer = window.setTimeout(() => { box.hidden = true; }, 6500);
}
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { "X-CSRF-Token": csrf(), ...options.headers } });
  const body = await response.json().catch(() => ({ error: "Resposta inválida do servidor." }));
  if (!response.ok) throw new Error(body.error || "Não foi possível concluir a operação.");
  return body;
}
function formMessage(message, error = false) {
  const target = $("#form-message"); target.hidden = false;
  target.textContent = message; target.classList.toggle("error", error); target.focus();
}
if ($("#logout")) $("#logout").addEventListener("click", async () => {
  try { await api("/api/logout", { method: "POST" }); location.assign("/"); }
  catch (error) { notify(error.message); }
});

// Fotos ficam somente na memória da aba até o envio ou descarte.
const capture = $(".capture");
let photos = [], stream = null, cameraGeneration = 0;
function stopCamera() {
  cameraGeneration++;
  if (stream) stream.getTracks().forEach(track => track.stop());
  stream = null;
  if (!capture) return;
  $("#camera").srcObject = null; $("#camera").hidden = true;
  $("#camera-placeholder").hidden = false; $("#stop-camera").hidden = true;
  $("#take-photo").disabled = true; $("#start-camera").disabled = false;
}
function renderPhotos() {
  $("#samples").replaceChildren();
  photos.forEach((photo, index) => {
    const item = el("div", undefined, "sample");
    const img = el("img"); img.src = photo.url; img.alt = `Foto ${index + 1} selecionada`;
    const remove = el("button", "×"); remove.type = "button";
    remove.setAttribute("aria-label", `Remover foto ${index + 1}`);
    remove.addEventListener("click", () => { URL.revokeObjectURL(photo.url); photos.splice(index, 1); renderPhotos(); });
    item.append(img, remove); $("#samples").append(item);
  });
  const maximum = Number(capture.dataset.max);
  $("#photo-count").textContent = photos.length === maximum ? `${maximum} foto(s) pronta(s) para confirmar` : `${photos.length} de ${maximum} foto(s)`;
  $("#take-photo").textContent = photos.length < maximum ? `Capturar foto ${photos.length + 1} de ${maximum}` : "Fotos completas";
  $("#take-photo").disabled = !stream || photos.length >= maximum;
  syncPhotoSubmit();
}
function clearPhotos() {
  photos.forEach(photo => URL.revokeObjectURL(photo.url)); photos = [];
  if (capture) { $("#photo-files").value = ""; renderPhotos(); }
}
function captureError(message) {
  $("#capture-error").hidden = !message; $("#capture-error").textContent = message;
}
function addPhoto(file) {
  const max = Number(capture.dataset.max);
  if (!["image/jpeg", "image/png"].includes(file.type)) throw new Error("Use somente JPG ou PNG.");
  if (file.size > 5 * 1024 * 1024) throw new Error("Cada foto deve ter no máximo 5 MB.");
  if (photos.length >= max) throw new Error(`Você já selecionou ${max} foto(s). Remova uma para substituir.`);
  photos.push({ file, url: URL.createObjectURL(file) }); renderPhotos();
}
if (capture) {
  $("#start-camera").addEventListener("click", async () => {
    captureError(""); $("#start-camera").disabled = true;
    const generation = ++cameraGeneration;
    try {
      if (!navigator.mediaDevices?.getUserMedia) throw new Error("Câmera indisponível. Abra em http://localhost:5000 ou use uma foto.");
      const acquired = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" }, audio: false });
      if (generation !== cameraGeneration) { acquired.getTracks().forEach(track => track.stop()); return; }
      stream = acquired;
      $("#camera").srcObject = stream; $("#camera").hidden = false;
      $("#camera-placeholder").hidden = true; $("#stop-camera").hidden = false;
      await $("#camera").play(); renderPhotos();
    } catch (error) {
      if (generation !== cameraGeneration) return;
      stopCamera(); captureError(error.name === "NotAllowedError" ? "Permita o acesso à câmera no navegador ou selecione uma foto." : error.name === "NotFoundError" ? "Nenhuma câmera encontrada. Conecte uma webcam ou selecione uma foto." : error.message);
    }
  });
  $("#stop-camera").addEventListener("click", stopCamera);
  $("#take-photo").addEventListener("click", () => {
    const video = $("#camera");
    if (!video.videoWidth) { captureError("Aguarde a câmera carregar."); return; }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob(blob => {
      try { if (!blob) throw new Error("Falha ao capturar. Tente novamente."); addPhoto(new File([blob], `captura-${Date.now()}.jpg`, { type: "image/jpeg" })); captureError(""); }
      catch (error) { captureError(error.message); }
    }, "image/jpeg", 0.92);
  });
  $("#photo-files").addEventListener("change", event => {
    captureError("");
    try { for (const file of event.target.files) addPhoto(file); }
    catch (error) { captureError(error.message); }
    event.target.value = "";
  });
  $("#clear-photos").addEventListener("click", clearPhotos);
  window.addEventListener("pagehide", () => { stopCamera(); clearPhotos(); });
}

// A senha nunca é guardada em localStorage, URL ou cookie.
document.querySelectorAll(".password-toggle").forEach(button => button.addEventListener("click", () => {
  const input = document.getElementById(button.dataset.target), show = input.type === "password";
  input.type = show ? "text" : "password"; button.textContent = show ? "Ocultar" : "Mostrar";
  button.setAttribute("aria-pressed", String(show)); button.setAttribute("aria-label", show ? "Ocultar senha" : "Mostrar senha");
}));
if ($("#credentials-form")) $("#credentials-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget, button = $("#submit-button"), label = button.textContent;
  if (!form.reportValidity()) return;
  button.disabled = true; button.textContent = "Verificando seus dados…";
  try {
    const result = await api("/api/auth/password", { method: "POST", body: new FormData(form) });
    $("#password").value = ""; location.assign(result.next);
  } catch (error) { formMessage(error.message, true); }
  finally { button.disabled = false; button.textContent = label; }
});
if ($("#cancel-login")) $("#cancel-login").addEventListener("click", async () => {
  try { await api("/api/auth/cancel", { method: "POST" }); stopCamera(); clearPhotos(); location.assign("/entrar"); }
  catch (error) { formMessage(error.message, true); }
});
function matchingPasswords() {
  const confirm = $("#password-confirm");
  if (!confirm) return true;
  confirm.setCustomValidity(confirm.value === $("#password").value ? "" : "As senhas não coincidem.");
  return confirm.checkValidity();
}
["#password", "#password-confirm"].forEach(selector => $(selector)?.addEventListener("input", () => $("#password-confirm")?.setCustomValidity("")));
function syncPhotoSubmit() {
  if (!capture) return;
  const consent = $('input[name="consent"]');
  $("#submit-button").disabled = photos.length !== Number(capture.dataset.max) || !!(consent && !consent.checked) || !!document.querySelector('form[aria-busy="true"]');
}
const enrollForm = $("#enroll-form");
function showEnrollStep(second) {
  $("#enroll-details").hidden = second; $("#enroll-biometrics").hidden = !second;
  const steps = document.querySelectorAll("#enroll-stepper li");
  steps.forEach((step,index) => {
    if (index === Number(second)) step.setAttribute("aria-current", "step"); else step.removeAttribute("aria-current");
    step.classList.toggle("complete", second && index === 0);
  });
  if (!second) stopCamera();
  const heading = document.querySelector(second ? "#enroll-biometrics h2" : "#enroll-details h2");
  heading.tabIndex = -1; heading.focus();
}
function validDetails() {
  matchingPasswords();
  const invalid = [...document.querySelectorAll("#enroll-details input,#enroll-details select")].find(input => !input.checkValidity());
  if (invalid) { showEnrollStep(false); invalid.reportValidity(); return false; }
  return true;
}
function nextEnrollStep() {
  if (!validDetails()) return;
  $("#summary-name").textContent = $("#name").value.trim();
  $("#summary-login").textContent = `Usuário: ${$("#login").value.trim()}`;
  $("#summary-role").textContent = enrollForm.dataset.initial === "yes" ? "Ministro · Nível 3" : $("#level").selectedOptions[0].textContent;
  showEnrollStep(true); syncPhotoSubmit();
}
if (enrollForm) {
  $("#enroll-next").addEventListener("click", nextEnrollStep);
  $("#enroll-back").addEventListener("click", () => showEnrollStep(false));
  $('input[name="consent"]').addEventListener("change", syncPhotoSubmit);
  $("#level")?.addEventListener("change", () => { $("#role-help").textContent = $("#level").value === "2" ? "Menu com boletins públicos e investigações." : "Menu com boletins públicos."; });
}
const photoForm = $("#login-form") || enrollForm || $("#activation-form");
if (photoForm) photoForm.addEventListener("submit", async event => {
  event.preventDefault();
  if (photoForm === enrollForm && !$("#enroll-details").hidden) { nextEnrollStep(); return; }
  if (photoForm === enrollForm && !validDetails()) return;
  matchingPasswords();
  if (!photoForm.reportValidity()) return;
  const max = Number(capture.dataset.max);
  if (photos.length !== max) { formMessage(`Selecione ou capture ${max} foto(s) para continuar.`, true); return; }
  const button = $("#submit-button"), label = button.textContent;
  button.disabled = true; button.textContent = "Conferindo a biometria…";
  photoForm.setAttribute("aria-busy", "true");
  try {
    const data = new FormData(photoForm);
    photos.forEach(photo => data.append("photos", photo.file));
    const path = photoForm.id === "login-form" ? "/api/login" : photoForm.id === "activation-form" ? "/api/activate" : photoForm.dataset.initial === "yes" ? "/api/setup" : "/api/users";
    const result = await api(path, { method: "POST", body: data });
    stopCamera(); clearPhotos(); photoForm.reset(); location.assign(result.next);
  } catch (error) { formMessage(error.message, true); }
  finally { button.textContent = label; photoForm.removeAttribute("aria-busy"); syncPhotoSubmit(); }
});

let records = [];
function renderRecords() {
  const query = $("#search").value.toLocaleLowerCase("pt-BR"), level = $("#records").dataset.level;
  const visible = records.filter(record => (level === "all" || String(record.level) === level) && `${record.title} ${record.region}`.toLocaleLowerCase("pt-BR").includes(query));
  const target = $("#records"); target.replaceChildren();
  $("#record-count").textContent = `${visible.length} documento(s) nesta consulta`;
  if (!visible.length) target.append(el("p", "Nenhum documento encontrado para este filtro.", "empty"));
  visible.forEach(record => {
    const row = el("article", undefined, "record-row"), info = el("div", undefined, "record-info");
    info.append(el("h3", record.title), el("p", `${record.region} · Nível ${record.level} · ${record.updated_at.split("-").reverse().join("/")}`));
    const button = el("button", "Consultar", "secondary"); button.type = "button";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const { record: detail } = await api(`/api/records/${record.id}`);
        $("#detail-level").textContent = `DOCUMENTO · NÍVEL ${detail.level}`;
        $("#detail-title").textContent = detail.title; $("#detail-region").textContent = detail.region;
        $("#detail-body").textContent = detail.body; $("#record-dialog").showModal();
      } catch (error) { notify(error.message); }
      finally { button.disabled = false; }
    });
    row.append(el("span", `0${record.level}`, "record-symbol"), info, button); target.append(row);
  });
}
if ($("#records")) {
  api(`/api/records?level=${$("#records").dataset.level}`).then(data => { records = data.records; renderRecords(); }).catch(error => { $("#records").textContent = error.message; $("#record-count").textContent = "Falha ao carregar."; });
  $("#search").addEventListener("input", renderRecords);
  $("#close-dialog").addEventListener("click", () => $("#record-dialog").close());
}
function table(headers) {
  const result = el("table"), head = el("thead"), row = el("tr"), body = el("tbody");
  headers.forEach(text => { const th = el("th", text); th.scope = "col"; row.append(th); });
  head.append(row); result.append(head, body); return { result, body };
}
async function loadUsers() {
  const { users } = await api("/api/users"), { result, body } = table(["Participante", "Perfil", "Vínculo de acesso", "Situação", "Ações"]);
  users.forEach(user => {
    const row = el("tr"), name = el("td", user.name), actions = el("td"); name.append(el("small", user.login));
    if (user.level !== 3) {
      const toggle = el("button", user.active ? "Desativar" : "Reativar", "text-button"); toggle.type = "button";
      toggle.addEventListener("click", async () => {
        toggle.disabled = true;
        try { const data = await api(`/api/users/${user.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ active: !user.active }) }); notify(data.message); await loadUsers(); }
        catch (error) { notify(error.message); toggle.disabled = false; }
      });
      const remove = el("button", "Excluir", "text-button danger"); remove.type = "button";
      remove.addEventListener("click", () => {
        deleteTarget = user.id;
        $("#delete-description").textContent = `Você está excluindo ${user.name} (usuário ${user.login}).`;
        $("#delete-message").hidden = true; $("#delete-dialog").showModal();
      });
      actions.append(toggle, remove);
    } else actions.textContent = "Cadastro principal";
    const binding = el("td"); binding.append(el("span", user.password_ready ? "Senha + rosto" : "Senha a definir", user.password_ready ? "badge" : "badge pending"));
    row.append(name, el("td", { 1: "Servidor · N1", 2: "Diretor · N2", 3: "Ministro · N3" }[user.level]), binding, el("td", user.active ? "Ativo" : "Inativo"), actions); body.append(row);
  });
  $("#user-list").replaceChildren(result);
}
let deleteTarget = null;
if ($("#delete-dialog")) {
  $("#cancel-delete").addEventListener("click", () => $("#delete-dialog").close());
  $("#confirm-delete").addEventListener("click", async () => {
    const button = $("#confirm-delete"); button.disabled = true;
    try { const data = await api(`/api/users/${deleteTarget}`, { method: "DELETE" }); $("#delete-dialog").close(); notify(data.message); await loadUsers(); }
    catch (error) { $("#delete-message").textContent = error.message; $("#delete-message").hidden = false; }
    finally { button.disabled = false; }
  });
}
if ($("#user-list")) loadUsers().catch(error => { $("#user-list").textContent = error.message; });
async function loadAudit() {
  const { events } = await api("/api/audit"), { result, body } = table(["Data e hora", "Participante", "Evento", "Detalhe"]);
  events.forEach(event => {
    const row = el("tr");
    [new Date(event.created_at.replace(" ", "T") + "Z").toLocaleString("pt-BR"), event.name || "Não identificado / removido", event.event.replaceAll("_", " "), event.detail].forEach(value => row.append(el("td", value)));
    body.append(row);
  });
  $("#audit-list").replaceChildren(events.length ? result : el("p", "Nenhum evento registrado.", "empty"));
}
if ($("#audit-list")) {
  const refresh = () => loadAudit().catch(error => { $("#audit-list").textContent = error.message; });
  refresh(); $("#refresh-audit").addEventListener("click", refresh);
}
// Remove a tela restrita quando a sessão expira ou é revogada em outra aba.
if (document.body.dataset.authenticated === "yes") {
  const checkSession = async () => {
    try { const data = await api("/api/state"); if (!data.user) location.replace("/entrar"); }
    catch (_) { /* A próxima consulta autenticada também verifica a sessão no servidor. */ }
  };
  window.setInterval(checkSession, 15000); window.addEventListener("focus", checkSession);
  window.addEventListener("pageshow", event => { if (event.persisted) checkSession(); });
}
