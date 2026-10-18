// Product workflows use server-owned sessions, assets, runs and review records.
let activeJobId = null;
let workspaceUser = null;
let workspaceRefreshing = false;
let cloudDeployment = false;

async function openSavedRun(identity) {
  const result = await (await fetch('/api/runs/' + identity)).json();
  document.getElementById('savedRunResult').textContent = JSON.stringify(result.result || result, null, 2);
  const files = document.getElementById('savedRunFiles'); files.replaceChildren();
  for (const asset of result.result?.evidence_assets || []) {
    const button = document.createElement('button'); button.className = 'border rounded px-2 py-1 text-xs'; button.textContent = 'Download source: ' + asset.filename;
    button.onclick = async () => {
      try {
        const response = await fetch(`/api/assets/${asset.id}/file`);
        const url = URL.createObjectURL(await response.blob());
        const link = document.createElement('a'); link.href = url; link.download = asset.filename; link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      } catch (error) {workspaceNotice(error.message);}
    };
    files.append(button);
  }
}

async function uploadCloudEvidence(kind, form) {
  const file = form.get('file');
  const metadata = {};
  for (const key of ['latitude', 'longitude', 'survey_no']) if (form.has(key)) metadata[key] = form.get(key);
  const intent = await (await fetch('/api/uploads/intent', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind, filename:file.name, metadata})})).json();
  const upload = new FormData();
  for (const [key,value] of Object.entries(intent.post.fields)) upload.append(key, value);
  upload.append('file', file);
  const response = await nativeFetch(intent.post.url, {method:'POST',body:upload});
  if (!response.ok) throw new Error('Private S3 upload failed. Retry or contact the operator.');
  return fetch(`/api/uploads/${intent.upload_id}/complete`, {method:'POST'});
}

async function pollCloudJob(runId, showProgress=true) {
  let cursor = 0;
  const deadline = Date.now() + 16 * 60 * 1000;
  while (Date.now() < deadline) {
    const events = await (await fetch(`/api/jobs/${runId}/events?after=${cursor}`)).json();
    for (const event of events.events || []) {
      cursor = Math.max(cursor, Number(event.id));
      if (showProgress && event.kind === 'TASK_PROGRESS') {
        const row = document.createElement('div'); row.textContent = `${event.payload.name || event.payload.task_id}: ${event.payload.status}`;
        const trace = document.getElementById('aiThoughtStepsList'); trace.append(row);
        while (trace.children.length > 100) trace.firstChild.remove();
      }
    }
    const saved = await (await fetch(`/api/jobs/${runId}`)).json();
    if (saved.status === 'COMPLETED') return saved.result;
    if (['FAILED','CANCELLED','INTERRUPTED'].includes(saved.status)) throw new Error(`${saved.status}: ${saved.error || 'See saved history'}`);
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  throw new Error('Analysis is taking longer than expected. Check saved history before submitting again.');
}

function openWorkspace() {
  document.getElementById('workspaceModal').classList.remove('hidden');
  if (!workspaceRefreshing) {
    workspaceRefreshing = true;
    refreshWorkspace().catch(error => workspaceNotice(error.message)).finally(() => {workspaceRefreshing = false;});
  }
}
function closeWorkspace() {
  document.getElementById('workspaceModal').classList.add('hidden');
}
function workspaceNotice(message) {
  document.getElementById('workspaceNotice').textContent = message;
}
async function refreshWorkspace() {
  const status = await (await fetch('/api/auth/status')).json();
  cloudDeployment = !!status.cloud_deployment;
  workspaceUser = status.user;
  document.getElementById('workspaceIdentity').textContent = status.user
    ? `${status.user.username} · ${status.user.role}` : status.login_required ? 'Sign in to your account' : 'Local development workspace';
  document.getElementById('workspaceLogin').classList.toggle('hidden', !!status.user || !status.login_required);
  document.getElementById('workspaceLogout').classList.toggle('hidden', !status.user);
  document.getElementById('workspaceBody').classList.toggle('hidden', status.login_required && !status.user);
  document.querySelectorAll('.simulation-control').forEach(el => el.classList.toggle('hidden', status.production));
  if (status.login_required && !status.user) return;
  const history = await (await fetch('/api/runs')).json();
  const list = document.getElementById('workspaceRuns');
  list.replaceChildren();
  for (const run of history.runs || []) {
    const row = document.createElement('div');
    row.className = 'flex flex-wrap items-center gap-2 border-b py-2';
    const label = document.createElement('span');
    label.className = 'flex-1 text-xs';
    label.textContent = `${new Date(run.created).toLocaleString()} · ${run.status}`;
    const open = document.createElement('button');
    open.className = 'text-blue-700 text-xs font-bold';
    open.textContent = 'Open result';
    open.onclick = async () => {
      try {await openSavedRun(run.id);} catch(error) {workspaceNotice(error.message);}
    };
    const download = document.createElement('button');
    download.className = 'text-emerald-700 text-xs font-bold';
    download.textContent = 'Download JSON';
    download.onclick = async () => {
      const response = await fetch(`/api/runs/${run.id}/export`);
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement('a'); a.href = url; a.download = `farmsync-${run.id}.json`; a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    };
    row.append(label, open, download); list.append(row);
  }
  if (!(history.runs || []).length) list.textContent = 'No saved audits yet.';
  const reviews = await (await fetch('/api/reviews')).json();
  const reviewList = document.getElementById('workspaceReviews'); reviewList.replaceChildren();
  for (const review of reviews.reviews || []) {
    const row = document.createElement('div'); row.className = 'border-b py-2 text-xs';
    const label = document.createElement('span'); label.textContent = `${review.state} · Run ${review.run_id.slice(0, 8)}${review.resolution ? ' · ' + review.resolution : ''}`;
    row.append(label);
    const inspect = document.createElement('button'); inspect.className = 'ml-2 text-blue-700 font-bold'; inspect.textContent = 'Inspect evidence';
    inspect.onclick = async () => {try {await openSavedRun(review.run_id);} catch(error) {workspaceNotice(error.message);}};
    row.append(inspect);
    if (review.state === 'OPEN' && workspaceUser && ['admin', 'reviewer'].includes(workspaceUser.role)) {
      const input = document.createElement('textarea'); input.className = 'block border rounded p-2 w-full mt-2'; input.placeholder = 'Record your evidence review and decision';
      const save = document.createElement('button'); save.className = 'text-emerald-700 font-bold mt-2'; save.textContent = 'Resolve review';
      save.onclick = async () => {
        try {
          await fetch(`/api/reviews/${review.id}/resolve`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({resolution:input.value})});
          await refreshWorkspace();
        } catch (error) { workspaceNotice(error.message); }
      };
      row.append(input, save);
    }
    reviewList.append(row);
  }
  if (!(reviews.reviews || []).length) reviewList.textContent = 'No review cases yet.';
}

async function signInWorkspace(event) {
  event.preventDefault();
  try {
    await fetch('/api/auth/login', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:document.getElementById('loginUsername').value, password:document.getElementById('loginPassword').value})});
    document.getElementById('loginPassword').value = '';
    location.reload();
  } catch (error) { workspaceNotice(error.message); }
}
async function signOutWorkspace() {
  await fetch('/api/auth/logout', {method:'POST'});
  localStorage.removeItem('farmsync_api_key');
  location.reload();
}

async function uploadFieldPhoto(event) {
  event.preventDefault();
  const file = document.getElementById('fieldUploadFile').files[0];
  if (!file) return workspaceNotice('Choose a field photograph.');
  const latitude = document.getElementById('photoLatitude').value;
  const longitude = document.getElementById('photoLongitude').value;
  try {
    await saveAndSelectPhoto(file, latitude, longitude);
    workspaceNotice('Photo saved and selected. Run Ask AI to analyze it. Coordinates are a supplied location claim.');
  } catch (error) { workspaceNotice(error.message); }
}

async function saveAndSelectPhoto(file, latitude = '', longitude = '') {
  const data = new FormData(); data.append('file', file);
  if (latitude) data.append('latitude', latitude);
  if (longitude) data.append('longitude', longitude);
  if (currentSurvey) data.append('survey_no', currentSurvey);
  const result = await (await fetch('/api/images/upload', {method:'POST', body:data})).json();
  if (!result.reference) throw new Error('Photo upload did not complete. Please try again.');
  await loadAvailablePhotos();
  const selector = document.getElementById('photoSelectDropdown');
  if (![...selector.options].some(option => option.value === result.reference)) {
    const option = document.createElement('option'); option.value = result.reference; option.textContent = result.filename; selector.append(option);
  }
  selector.value = result.reference;
  addNotification(`Photo uploaded and selected: ${result.filename}`);
  return result;
}

async function uploadCustomPhoto(input) {
  const file = input.files?.[0];
  if (!file) return;
  const button = document.getElementById('photoUploadButton');
  const status = document.getElementById('photoUploadStatus');
  status.classList.remove('hidden');
  status.textContent = 'Uploading photo...';
  button.disabled = true;
  input.disabled = true;
  try {
    const result = await saveAndSelectPhoto(file);
    status.textContent = `${result.filename} uploaded and selected. Click Ask AI to analyze it. Photo location remains unverified unless checked against the parcel.`;
  } catch (error) {
    status.textContent = `Photo upload failed: ${error.message}`;
    addNotification(status.textContent);
  } finally {
    button.disabled = false;
    input.disabled = false;
    input.value = '';
  }
}

async function runBatchDocument() {
  const reference = document.getElementById('docSelectDropdown').value;
  if (!reference.startsWith('asset:')) return workspaceNotice('Upload and select your PDF first. Batch checks process the rows in that uploaded document.');
  workspaceNotice('Comparing the document rows…');
  try {
    let result = await (await fetch('/api/documents/batch', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({document_path:reference, village:document.getElementById('batchVillage').value || null})})).json();
    if (result.status === 'QUEUED') result = await pollCloudJob(result.run_id, false);
    document.getElementById('savedRunResult').textContent = JSON.stringify(result, null, 2);
    workspaceNotice(`Compared ${result.total_claims} source claims. Unresolved identities and missing fields remain unverified.`);
    await refreshWorkspace();
  } catch (error) { workspaceNotice(error.message); }
}

async function cancelActiveAnalysis() {
  if (!activeJobId) return;
  await fetch(`/api/jobs/${activeJobId}/cancel`, {method:'POST'});
  document.getElementById('aiAnswerContent').textContent = 'Cancellation requested; the active bounded tool call will return safely.';
}

async function submitAnalysis(payload) {
  const created = await (await fetch('/api/jobs', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})).json();
  const runId = created.run_id; activeJobId = runId;
  document.getElementById('cancelAnalysisBtn').classList.remove('hidden');
  let cursor = 0;
  try {
    if (created.progress_transport === 'poll') return await pollCloudJob(runId);
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const response = await fetch(`/api/jobs/${runId}/events`, {headers:{'Last-Event-ID':String(cursor)}});
        const reader = response.body.getReader(), decoder = new TextDecoder();
        let buffer = '';
        while (true) {
          const part = await reader.read();
          if (part.done) break;
          buffer += decoder.decode(part.value, {stream:true});
          let end;
          while ((end = buffer.indexOf('\n\n')) >= 0) {
            const block = buffer.slice(0, end); buffer = buffer.slice(end + 2);
            const id = block.match(/^id: (\d+)/m); if (id) cursor = Number(id[1]);
            const data = block.match(/^data: (.+)$/m);
            if (!data || activeJobId !== runId) continue;
            const event = JSON.parse(data[1]);
            if (event.kind === 'TASK_PROGRESS') {
              const row = document.createElement('div');
              row.textContent = `${event.payload.name || event.payload.task_id}: ${event.payload.status}`;
              const trace = document.getElementById('aiThoughtStepsList'); trace.append(row);
              while (trace.children.length > 100) trace.firstChild.remove();
            }
          }
        }
      } catch (error) {
        if (attempt === 2) throw error;
      }
      const saved = await (await fetch(`/api/jobs/${runId}`)).json();
      if (saved.status === 'COMPLETED') return saved.result;
      if (['FAILED','CANCELLED','INTERRUPTED'].includes(saved.status)) throw new Error(`${saved.status}: ${saved.error || 'See saved run history'}`);
    }
    throw new Error('Progress connection ended; open Workspace to inspect the saved run.');
  } finally {
    if (activeJobId === runId) {
      activeJobId = null;
      document.getElementById('cancelAnalysisBtn').classList.add('hidden');
    }
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const status = await (await fetch('/api/auth/status')).json();
    cloudDeployment = !!status.cloud_deployment;
    workspaceUser = status.user;
    if (status.production) {
      document.getElementById('farmsyncApiKey')?.parentElement?.classList.add('hidden');
      document.getElementById('saveAwsBtn')?.classList.add('hidden');
      document.getElementById('tabRedTeam')?.classList.add('hidden');
      document.querySelectorAll('.simulation-control').forEach(el => el.classList.add('hidden'));
    }
    if (status.login_required && !status.authenticated) openWorkspace();
  } catch (error) { console.warn('Workspace unavailable:', error.message); }
});
