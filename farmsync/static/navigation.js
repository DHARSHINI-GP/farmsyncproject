// Navigation opens the existing live results rather than starting another audit.
function saveModelPreference(value) {
  try { localStorage.setItem('farmsync_text_model', value); } catch (_) { /* Selection still applies to this request. */ }
}

document.addEventListener('DOMContentLoaded', () => {
  const selector = document.getElementById('aiModelSelect');
  try {
    const saved = localStorage.getItem('farmsync_text_model');
    if ([...selector.options].some(option => option.value === saved)) selector.value = saved;
  } catch (_) { /* Browser storage may be disabled. */ }
});

function switchMode(mode) {
  document.getElementById('compactViewSelect').value = mode;
  for (const button of document.querySelectorAll('header nav [data-view]')) {
    button.setAttribute('aria-pressed', String(button.dataset.view === mode));
  }
  if (mode === 'explorer' || mode === 'audit') {
    filterTable('all');
    const target = document.getElementById(mode === 'audit' ? 'parcelListContainer' : 'map');
    target?.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    if (mode === 'explorer') map.invalidateSize();
    return;
  }
  if (isDrawerCollapsed) toggleDrawer();
  const target = document.getElementById(mode === 'telemetry' ? 'routerTelemetryPanel' : 'aiResponseBox');
  target.setAttribute('tabindex', '-1');
  target.focus({preventScroll: true});
  target.scrollIntoView({behavior: 'smooth', block: 'nearest'});
  if (mode === 'ai') document.getElementById('aiQueryInput').focus({preventScroll: true});
}

const sessionNotifications = [];

function renderNotifications() {
  const items = document.getElementById('notificationItems');
  items.replaceChildren();
  if (!sessionNotifications.length) {
    items.textContent = 'No updates yet. Run an audit or upload a photo.';
    return;
  }
  for (const entry of sessionNotifications) {
    const item = document.createElement('div');
    item.className = 'border-b border-slate-100 py-2';
    const message = document.createElement('p');
    message.textContent = entry.message;
    const time = document.createElement('time');
    time.className = 'text-slate-500';
    time.dateTime = entry.time.toISOString();
    time.textContent = entry.time.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    item.append(message, time);
    items.append(item);
  }
}

function addNotification(message) {
  sessionNotifications.unshift({message, time: new Date()});
  sessionNotifications.splice(30);
  renderNotifications();
  const open = !document.getElementById('notificationsPanel').classList.contains('hidden');
  document.getElementById('notificationUnreadDot').classList.toggle('hidden', open);
}

function toggleNotifications(show) {
  const panel = document.getElementById('notificationsPanel');
  const open = typeof show === 'boolean' ? show : panel.classList.contains('hidden');
  panel.classList.toggle('hidden', !open);
  document.getElementById('notificationsButton').setAttribute('aria-expanded', String(open));
  if (open) {
    renderNotifications();
    document.getElementById('notificationUnreadDot').classList.add('hidden');
    panel.querySelector('button').focus();
  } else {
    document.getElementById('notificationsButton').focus();
  }
}

document.addEventListener('click', event => {
  const panel = document.getElementById('notificationsPanel');
  if (!panel.classList.contains('hidden') && !panel.contains(event.target) &&
      !document.getElementById('notificationsButton').contains(event.target)) {
    toggleNotifications(false);
  }
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !document.getElementById('notificationsPanel').classList.contains('hidden')) {
    toggleNotifications(false);
  }
});
