const dialog = document.querySelector('#eventDialog');
const form = document.querySelector('#eventForm');
const errorBox = document.querySelector('#formError');
const dialogTitle = document.querySelector('#eventDialogTitle');
const submitLabel = document.querySelector('#eventSubmitLabel');
const categoryFilter = document.querySelector('#categoryFilter');
const detailDialog = document.querySelector('#eventDetailDialog');
let activeDetailEvent = null;

function updateCalendarNowLine() {
  const tracks = document.querySelectorAll('.calendar-day-track[data-date]');
  if (!tracks.length) return;

  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Ho_Chi_Minh',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date()).reduce((values, part) => {
    values[part.type] = part.value;
    return values;
  }, {});
  const dateKey = `${parts.year}-${parts.month}-${parts.day}`;
  const track = [...tracks].find((item) => item.dataset.date === dateKey);
  document.querySelectorAll('.calendar-now').forEach((line) => line.remove());
  if (!track) return;

  const hour = Number(parts.hour);
  const minute = Number(parts.minute);
  const second = Number(parts.second);
  if (hour < 7 || hour >= 24) return;

  const line = document.createElement('div');
  line.className = 'calendar-now';
  line.style.top = `${hour * 60 + minute + second / 60 - 7 * 60}px`;
  line.setAttribute('aria-label', `Giờ hiện tại ${parts.hour}:${parts.minute}`);
  line.innerHTML = '<i></i>';
  track.append(line);
}

updateCalendarNowLine();
window.setInterval(updateCalendarNowLine, 15000);

function syncCategoryColor(select) {
  if (!select) return;
  [...select.classList].filter((name) => name.startsWith('category-')).forEach((name) => select.classList.remove(name));
  select.classList.add('category-select');
  if (select.value && select.value !== 'all') select.classList.add(`category-${select.value}`);
}

document.querySelectorAll('#categoryFilter, select[name="category"]').forEach((select) => {
  syncCategoryColor(select);
  select.addEventListener('change', () => syncCategoryColor(select));
});

function setActiveNavItem(target) {
  document.querySelectorAll('.nav-item').forEach((item) => {
    const isActive = item === target;
    item.classList.toggle('active', isActive);
    item.setAttribute('aria-current', isActive ? 'page' : 'false');
  });
}

function syncNavSelection() {
  const items = [...document.querySelectorAll('.nav-item')];
  const hash = window.location.hash;
  const params = new URLSearchParams(window.location.search);
  const period = params.get('period');

  const match = items.find((item) => {
    const href = item.getAttribute('href') || '';
    if (!href) return false;
    if (href.startsWith('#')) return href === hash;
    const url = new URL(href, window.location.href);
    if (url.hash && hash) return url.hash === hash;
    if (url.search) {
      const hrefParams = new URLSearchParams(url.search);
      return hrefParams.get('period') === period;
    }
    return item.classList.contains('active');
  });

  setActiveNavItem(match || items[0] || null);
}

function toast(message) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = message;
  document.body.append(el);
  setTimeout(() => el.remove(), 2200);
}

function syncRepeatUntilField() {
  const isRecurring = form.elements.repeat_rule.value !== 'none';
  const isForever = form.elements.repeat_forever.checked;
  const dateInput = form.elements.repeat_until;
  const isWeekly = form.elements.repeat_rule.value === 'weekly';
  form.querySelector('.repeat-days-field').style.display = isWeekly ? 'block' : 'none';
  dateInput.disabled = !isRecurring || isForever;
  dateInput.closest('.repeat-end-field').style.display = isRecurring ? 'block' : 'none';
  if (!isRecurring || isForever) {
    dateInput.value = '';
  }
}

function setRepeatDaysForDate(dateValue) {
  if (!dateValue) return;
  const weekday = (new Date(`${dateValue}T12:00:00`).getDay() + 6) % 7;
  form.querySelectorAll('[name="repeat_days"]').forEach((checkbox) => {
    checkbox.checked = Number(checkbox.value) === weekday;
  });
}

function syncMeetingLinkField() {
  const isGroupMeeting = form.elements.category.value === 'group_meeting';
  const groupFields = form.querySelector('.meeting-field-group');
  if (groupFields) {
    groupFields.style.display = isGroupMeeting ? 'block' : 'none';
  }
  if (!isGroupMeeting) {
    form.elements.zoom_link.value = '';
    form.elements.zoom_id.value = '';
    form.elements.zoom_password.value = '';
  }
}

function prepareCreateForm(dateValue) {
  form.reset();
  form.elements.event_id.value = '';
  form.elements.event_date.value = dateValue || form.elements.event_date.defaultValue;
  form.elements.repeat_forever.checked = true;
  form.elements.repeat_rule.value = 'none';
  form.elements.repeat_interval.value = '1';
  setRepeatDaysForDate(form.elements.event_date.value);
  syncRepeatUntilField();
  syncMeetingLinkField();
  dialogTitle.textContent = 'Tạo sự kiện mới';
  submitLabel.textContent = 'Lưu sự kiện';
  errorBox.textContent = '';
}

document.querySelectorAll('.nav-item').forEach((item) => {
  item.addEventListener('click', () => {
    setActiveNavItem(item);
  });
});

syncNavSelection();

document.querySelectorAll('[data-open-modal]').forEach((button) => button.addEventListener('click', () => {
  prepareCreateForm(button.dataset.date);
  dialog.showModal();
  form.elements.title.focus();
}));

// Switch between weekly and monthly reflection prompts without losing unsaved text.
document.querySelectorAll('[data-reflection-tab]').forEach((tab) => tab.addEventListener('click', () => {
  const period = tab.dataset.reflectionTab;
  document.querySelectorAll('[data-reflection-tab]').forEach((item) => {
    const active = item === tab;
    item.classList.toggle('is-active', active);
    item.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('[data-reflection-form]').forEach((form) => form.classList.toggle('is-hidden', form.dataset.reflectionForm !== period));
}));

document.querySelectorAll('[data-goal-tab]').forEach((tab) => tab.addEventListener('click', () => {
  const period = tab.dataset.goalTab;
  document.querySelectorAll('[data-goal-tab]').forEach((item) => {
    const active = item === tab;
    item.classList.toggle('is-active', active);
    item.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('[data-goal-form]').forEach((form) => form.classList.toggle('is-hidden', form.dataset.goalForm !== period));
}));

document.querySelectorAll('[data-history-tab]').forEach((tab) => tab.addEventListener('click', () => {
  const type = tab.dataset.historyTab;
  document.querySelectorAll('[data-history-tab]').forEach((item) => {
    const active = item === tab;
    item.classList.toggle('is-active', active);
    item.setAttribute('aria-selected', String(active));
  });
  document.querySelectorAll('[data-history-list]').forEach((list) => list.classList.toggle('is-hidden', list.dataset.historyList !== type));
}));

const historyDate = (value) => {
  const [year, month, day] = value.split('-').map(Number);
  return new Date(year, month - 1, day, 12);
};
const historyDateLabel = (value) => new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(historyDate(value));
function addHistoryEntry(container, title, range, fields) {
  const details = document.createElement('details');
  details.className = 'history-entry';
  const summary = document.createElement('summary');
  const period = document.createElement('strong');
  period.textContent = title;
  const date = document.createElement('time');
  date.textContent = range;
  summary.append(period, date);
  details.append(summary);
  const content = document.createElement('div');
  content.className = 'history-entry-content';
  fields.filter(([, value]) => value?.trim()).forEach(([label, value]) => {
    const answer = document.createElement('p');
    const answerLabel = document.createElement('strong');
    answerLabel.textContent = label;
    const answerText = document.createElement('span');
    answerText.textContent = value;
    answer.append(answerLabel, answerText);
    content.append(answer);
  });
  details.append(content);
  container.append(details);
}
function renderHistory(data) {
  const reflectionList = document.querySelector('[data-history-list="reflections"]');
  const goalList = document.querySelector('[data-history-list="goals"]');
  reflectionList.replaceChildren();
  goalList.replaceChildren();
  const periodNames = { week: 'Tổng kết tuần', month: 'Tổng kết tháng', quarter: 'Mục tiêu quý' };
  (data.reflections || []).forEach((item) => {
    const start = historyDate(item.period_start);
    const end = new Date(start);
    if (item.period_type === 'week') end.setDate(end.getDate() + 6);
    else end.setMonth(end.getMonth() + 1, 0);
    const range = `${historyDateLabel(item.period_start)} – ${new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' }).format(end)}`;
    const fields = [
      ['Điều khiến mình tự hào', item.proud],
      ['Điều muốn cải thiện', item.improve],
      ['Bài học', item.lesson],
      ['Khoảnh khắc muốn lưu giữ', item.memory],
      ['Mô thức nhận ra trong tháng', item.pattern],
    ];
    addHistoryEntry(reflectionList, periodNames[item.period_type] || 'Tổng kết', range, fields);
  });
  (data.goals || []).forEach((item) => {
    const fields = [['Mục tiêu', item.goal_text], ['Vì sao điều này quan trọng', item.reason], ['Bước đầu tiên', item.first_step]];
    addHistoryEntry(goalList, periodNames[item.period_type] || 'Mục tiêu', `${historyDateLabel(item.period_start)} – ${historyDateLabel(item.period_end)}`, fields);
  });
  if (!reflectionList.children.length) reflectionList.innerHTML = '<p class="history-empty">Chưa có tổng kết nào. Những điều bạn ghi lại sẽ xuất hiện ở đây.</p>';
  if (!goalList.children.length) goalList.innerHTML = '<p class="history-empty">Chưa có mục tiêu nào được lưu.</p>';
}
async function refreshHistory() {
  try {
    const response = await fetch('/api/history');
    if (!response.ok) throw new Error('History unavailable');
    renderHistory(await response.json());
  } catch {
    document.querySelectorAll('[data-history-list]').forEach((list) => {
      list.innerHTML = '<p class="history-empty">Chưa tải được lịch sử. Vui lòng thử tải lại trang.</p>';
    });
  }
}
refreshHistory();

document.querySelectorAll('[data-reflection-form]').forEach((reflectionForm) => reflectionForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = reflectionForm.querySelector('button[type="submit"]');
  const status = reflectionForm.querySelector('.reflection-save-status');
  const body = Object.fromEntries(new FormData(reflectionForm));
  body.period = reflectionForm.dataset.reflectionForm;
  body.period_start = reflectionForm.dataset.periodStart;
  button.disabled = true;
  status.textContent = 'Đang lưu…';
  try {
    const response = await fetch('/api/reflections', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const result = await response.json().catch(() => ({}));
    status.textContent = response.ok ? 'Đã lưu tổng kết.' : (result.error || 'Chưa lưu được. Thử lại nhé.');
    if (response.ok) refreshHistory();
  } catch {
    status.textContent = 'Không thể kết nối. Kiểm tra mạng rồi thử lại nhé.';
  } finally {
    button.disabled = false;
  }
}));

document.querySelectorAll('[data-goal-form]').forEach((goalForm) => goalForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = goalForm.querySelector('button[type="submit"]');
  const status = goalForm.querySelector('.goal-save-status');
  const body = Object.fromEntries(new FormData(goalForm));
  body.period = goalForm.dataset.goalForm;
  body.period_start = goalForm.dataset.periodStart;
  body.period_end = goalForm.dataset.periodEnd;
  button.disabled = true;
  status.textContent = 'Đang lưu…';
  try {
    const response = await fetch('/api/goals', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const result = await response.json().catch(() => ({}));
    status.textContent = response.ok ? 'Đã lưu mục tiêu.' : (result.error || 'Chưa lưu được. Thử lại nhé.');
    if (response.ok) refreshHistory();
  } catch {
    status.textContent = 'Không thể kết nối. Kiểm tra mạng rồi thử lại nhé.';
  } finally {
    button.disabled = false;
  }
}));

document.querySelectorAll('[data-close-modal]').forEach((button) => button.addEventListener('click', () => dialog.close()));
dialog?.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
form?.elements.repeat_rule?.addEventListener('change', syncRepeatUntilField);
form?.elements.repeat_forever?.addEventListener('change', syncRepeatUntilField);
form?.elements.category?.addEventListener('change', syncMeetingLinkField);
form?.elements.event_date?.addEventListener('change', () => {
  if (form.elements.repeat_rule.value === 'weekly') setRepeatDaysForDate(form.elements.event_date.value);
});

categoryFilter?.addEventListener('change', () => {
  const params = new URLSearchParams(window.location.search);
  params.set('category', categoryFilter.value);
  window.location.search = params.toString();
});

document.querySelector('[data-copy-schedule]')?.addEventListener('click', async (event) => {
  const button = event.currentTarget;
  const weekdayNames = ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy'];
  const categoryNames = { work: 'Công việc', personal: 'Cá nhân', health: 'Sức khỏe', study: 'Học tập', group_meeting: 'Họp nhóm', other: 'Khác' };
  const days = new Map();
  document.querySelectorAll('.event-item[data-occurrence]').forEach((item) => {
    const date = item.dataset.occurrence;
    if (!date) return;
    const copy = item.querySelector('.event-copy');
    if (!copy) return;
    const title = copy.querySelector('strong')?.textContent.trim();
    const timeText = copy.querySelector('span')?.textContent.trim() || '';
    const timeRange = timeText.match(/\d{1,2}:\d{2}\s*[–-]\s*\d{1,2}:\d{2}/)?.[0];
    const times = timeRange?.match(/(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})/);
    const time = timeRange ? `${times[1]}-${times[2]}${times[2] <= times[1] ? ' (ngày hôm sau)' : ''}` : '';
    if (!title || !time) return;
    const categoryTag = copy.querySelector('.category-tag');
    const categoryKey = [...item.classList].find((name) => name.startsWith('category-'))?.slice('category-'.length);
    const category = categoryTag?.textContent.trim() || categoryNames[categoryKey] || '';
    const occurrenceStatus = item.dataset.occurrenceStatus || 'planned';
    const statusNote = item.dataset.statusNote || '';
    const missions = [...item.querySelectorAll('.mission-list .mission-item')].map((mission) => {
      const checkbox = mission.querySelector('.mission-check');
      return `    ${checkbox?.checked ? '☑' : '☐'} ${mission.querySelector('span')?.textContent.trim() || ''}`;
    });
    if (!days.has(date)) days.set(date, []);
    const statusText = occurrenceStatus === 'cancelled' ? ' [Đã hủy]' : occurrenceStatus === 'rescheduled' ? ` [Đổi lịch${statusNote ? `: ${statusNote}` : ''}]` : '';
    days.get(date).push([`${time}: ${title}${category ? ` [${category}]` : ''}${statusText}`, ...(missions.length ? ['  Mission nhỏ:', ...missions] : [])].join('\n'));
  });

  const lines = [...days.entries()].sort(([a], [b]) => a.localeCompare(b)).flatMap(([date, events]) => {
    const parsed = new Date(`${date}T12:00:00`);
    const [year, month, day] = date.split('-');
    return [`${weekdayNames[parsed.getDay()]} (${day}/${month}/${year}):`, ...events, ''];
  });
  const text = lines.length ? `Lịch trình ${document.querySelector('.view-switch .selected')?.textContent.trim().toLowerCase() || 'hiện tại'}:\n\n${lines.join('\n').trim()}` : 'Chưa có sự kiện trong khoảng thời gian này.';
  try {
    await navigator.clipboard.writeText(text);
    toast('Đã sao chép lịch dưới dạng văn bản.');
  } catch {
    const field = document.createElement('textarea');
    field.value = text;
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.append(field);
    field.select();
    const copied = document.execCommand('copy');
    field.remove();
    toast(copied ? 'Đã sao chép lịch dưới dạng văn bản.' : 'Không thể sao chép lịch.');
  }
  button.blur();
});

form?.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorBox.textContent = '';
  if (form.elements.repeat_forever.checked || form.elements.repeat_rule.value === 'none') {
    form.elements.repeat_until.value = '';
  }
  if (form.elements.category.value !== 'group_meeting') {
    form.elements.zoom_link.value = '';
    form.elements.zoom_id.value = '';
    form.elements.zoom_password.value = '';
  }
  const payload = Object.fromEntries(new FormData(form));
  payload.repeat_days = [...form.querySelectorAll('[name="repeat_days"]:checked')].map((checkbox) => Number(checkbox.value));
  const eventId = form.elements.event_id.value;
  const submitButton = form.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  try {
    const response = await fetch(eventId ? `/api/events/${eventId}` : '/api/events', {
      method: eventId ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) { errorBox.textContent = result.error || 'Không thể lưu sự kiện.'; return; }
    dialog.close();
    const newCategory = form.elements.category.value;
    const currentFilter = form.dataset.categoryFilter;
    const nextFilter = currentFilter === 'all' || currentFilter === newCategory ? currentFilter : newCategory;
    window.location.href = `/?period=${form.dataset.period}&date=${form.elements.event_date.value}&category=${nextFilter}`;
  } catch (error) {
    errorBox.textContent = 'Không kết nối được máy chủ. Vui lòng thử lưu lại.';
  } finally {
    submitButton.disabled = false;
  }
});

document.querySelectorAll('.edit-button').forEach((button) => button.addEventListener('click', async () => {
  const item = button.closest('[data-event-id]');
  if (!item) return;
  const response = await fetch(`/api/events/${item.dataset.eventId}`);
  if (!response.ok) { toast('Không tải được sự kiện.'); return; }
  const event = await response.json();
  prepareCreateForm(event.event_date);
  form.elements.event_id.value = event.id;
  form.elements.title.value = event.title;
  form.elements.event_date.value = event.event_date;
  form.elements.category.value = event.category || 'personal';
  form.elements.priority.value = event.priority;
  form.elements.start_time.value = event.start_time.slice(0, 5);
  form.elements.end_time.value = event.end_time.slice(0, 5);
  form.elements.repeat_rule.value = event.repeat_rule;
  form.elements.repeat_interval.value = event.repeat_interval || '1';
  const repeatDays = event.repeat_days?.length ? event.repeat_days : [(new Date(`${event.event_date}T12:00:00`).getDay() + 6) % 7];
  form.querySelectorAll('[name="repeat_days"]').forEach((checkbox) => {
    checkbox.checked = repeatDays.includes(Number(checkbox.value));
  });
  form.elements.repeat_forever.checked = !event.repeat_until;
  form.elements.repeat_until.value = event.repeat_until || '';
  syncRepeatUntilField();
  form.elements.notes.value = event.notes || '';
  form.elements.missions.value = (event.missions || []).join('\n');
  form.elements.zoom_link.value = event.zoom_link || '';
  form.elements.zoom_id.value = event.zoom_id || '';
  form.elements.zoom_password.value = event.zoom_password || '';
  syncMeetingLinkField();
  dialogTitle.textContent = 'Chỉnh sửa sự kiện';
  submitLabel.textContent = 'Lưu thay đổi';
  dialog.showModal();
  form.elements.title.focus();
}));

async function toggleMission(item, missionIndex, control) {
  control.disabled = true;
  const response = await fetch(`/api/events/${item.dataset.eventId}/missions/toggle`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ occurrence_date: item.dataset.occurrence, mission_index: missionIndex }),
  });
  if (response.ok) {
    window.location.reload();
    return true;
  }
  else {
    control.disabled = false;
    toast('Không thể cập nhật mission.');
    return false;
  }
}

function updateMissionDisplay(item, missionIndex, completed) {
  item.querySelectorAll(`.mission-check[data-mission-index="${missionIndex}"]`).forEach((checkbox) => {
    checkbox.checked = completed;
    checkbox.closest('.mission-item')?.classList.toggle('is-done', completed);
  });
  detailDialog.querySelectorAll(`.detail-mission-check[data-mission-index="${missionIndex}"]`).forEach((checkbox) => {
    checkbox.checked = completed;
    checkbox.closest('.detail-mission-item')?.classList.toggle('is-done', completed);
  });
  const checks = [...item.querySelectorAll('.mission-check')];
  const progress = item.querySelector('.mission-progress-toggle');
  if (progress) progress.textContent = `${checks.filter((checkbox) => checkbox.checked).length}/${checks.length} mission`;
}

function openEventDetails(item) {
  const copy = item.querySelector('.event-copy');
  if (!copy) return;
  const title = copy.querySelector('strong')?.textContent.trim() || 'Sự kiện';
  const timeText = copy.querySelector('span')?.textContent.trim() || '';
  const timeRange = timeText.match(/\d{1,2}:\d{2}\s*[–-]\s*\d{1,2}:\d{2}/)?.[0];
  const times = timeRange?.match(/(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})/);
  const time = timeRange ? `${times[1]} – ${times[2]}${times[2] <= times[1] ? ' (ngày hôm sau)' : ''}` : timeText;
  const date = item.dataset.occurrence || '';
  activeDetailEvent = item;
  const [year, month, day] = date.split('-');
  const dayLabel = date ? new Date(`${date}T12:00:00`).toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) : '';
  detailDialog.querySelector('#eventDetailTitle').textContent = title;
  detailDialog.querySelector('#eventDetailTime').textContent = [dayLabel, time].filter(Boolean).join(' · ');
  detailDialog.querySelector('#eventOccurrenceStatus').value = item.dataset.occurrenceStatus || 'planned';
  detailDialog.querySelector('#eventOccurrenceNote').value = item.dataset.statusNote || '';
  detailDialog.querySelector('#statusSaveMessage').textContent = '';
  const sourceCategory = copy.querySelector('.category-tag');
  const category = detailDialog.querySelector('#eventDetailCategory');
  category.textContent = sourceCategory?.textContent.trim() || 'Chưa phân loại';
  category.className = `category-tag event-detail-category ${[...(sourceCategory?.classList || [])].filter((name) => name.startsWith('category-')).join(' ')}`;
  const sourceZoom = copy.querySelector('.meeting-link, a[href*="zoom"]');
  const zoomLink = detailDialog.querySelector('#eventDetailZoom');
  zoomLink.hidden = !sourceZoom;
  if (sourceZoom) zoomLink.href = sourceZoom.href;
  const description = [...copy.querySelectorAll('small')]
    .filter((node) => !node.classList.contains('category-tag') && !node.classList.contains('mission-progress'))
    .map((node) => node.textContent.trim()).filter(Boolean).join('\n');
  const descriptionBox = detailDialog.querySelector('#eventDetailDescription');
  descriptionBox.textContent = description || 'Chưa có ghi chú cho sự kiện này.';
  const list = detailDialog.querySelector('#eventDetailMissions');
  list.replaceChildren();
  const sourceMissions = [...item.querySelectorAll('.mission-list .mission-item')];
  if (!sourceMissions.length) {
    const empty = document.createElement('p');
    empty.className = 'event-detail-empty';
    empty.textContent = 'Chưa có mission. Mở chỉnh sửa sự kiện để thêm mission.';
    list.append(empty);
  }
  sourceMissions.forEach((source) => {
    const sourceCheck = source.querySelector('.mission-check');
    const label = document.createElement('label');
    label.className = `detail-mission-item${sourceCheck.checked ? ' is-done' : ''}`;
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'detail-mission-check';
    checkbox.dataset.missionIndex = sourceCheck.dataset.missionIndex;
    checkbox.checked = sourceCheck.checked;
    checkbox.disabled = item.dataset.occurrenceStatus !== 'planned';
    const text = document.createElement('span');
    text.textContent = source.querySelector('span')?.textContent.trim() || '';
    checkbox.addEventListener('change', async () => {
      const desired = checkbox.checked;
      checkbox.disabled = true;
      const response = await fetch(`/api/events/${item.dataset.eventId}/missions/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ occurrence_date: date, mission_index: checkbox.dataset.missionIndex }),
      });
      if (response.ok) updateMissionDisplay(item, checkbox.dataset.missionIndex, desired);
      else {
        checkbox.checked = !desired;
        toast('Không thể cập nhật mission.');
      }
      checkbox.disabled = false;
    });
    label.append(checkbox, text);
    list.append(label);
  });
  detailDialog.showModal();
}

document.querySelectorAll('[data-close-detail]').forEach((button) => button.addEventListener('click', () => detailDialog.close()));
detailDialog?.addEventListener('click', (event) => { if (event.target === detailDialog) detailDialog.close(); });
document.querySelector('#saveOccurrenceStatus')?.addEventListener('click', async () => {
  if (!activeDetailEvent) return;
  const status = detailDialog.querySelector('#eventOccurrenceStatus').value;
  const note = detailDialog.querySelector('#eventOccurrenceNote').value.trim();
  const message = detailDialog.querySelector('#statusSaveMessage');
  const button = document.querySelector('#saveOccurrenceStatus');
  button.disabled = true;
  const response = await fetch(`/api/events/${activeDetailEvent.dataset.eventId}/occurrence-status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ occurrence_date: activeDetailEvent.dataset.occurrence, status, note }),
  });
  if (response.ok) window.location.reload();
  else {
    const result = await response.json().catch(() => ({}));
    message.textContent = result.error || 'Không lưu được trạng thái.';
    button.disabled = false;
  }
});

document.querySelectorAll('.event-item').forEach((item) => {
  item.tabIndex = 0;
  item.setAttribute('aria-haspopup', 'dialog');
  item.addEventListener('click', (event) => {
    if (event.target.closest('button, input, a, .mission-item')) return;
    openEventDetails(item);
  });
  item.addEventListener('keydown', (event) => {
    if ((event.key === 'Enter' || event.key === ' ') && event.target === item) {
      event.preventDefault();
      openEventDetails(item);
    }
  });
  item.querySelectorAll('.mission-progress-toggle').forEach((button) => button.addEventListener('click', () => {
    toggleMission(item, button.dataset.missionToggle, button);
  }));
  item.querySelectorAll('.mission-check').forEach((checkbox) => checkbox.addEventListener('change', async () => {
    const wasChecked = checkbox.checked;
    if (!await toggleMission(item, checkbox.dataset.missionIndex, checkbox)) checkbox.checked = wasChecked;
  }));
  item.querySelector('.check-button')?.addEventListener('click', async () => {
    const button = item.querySelector('.check-button');
    button.disabled = true;
    try {
      const response = await fetch(`/api/events/${item.dataset.eventId}/toggle`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ occurrence_date: item.dataset.occurrence }) });
      if (response.ok) window.location.reload();
      else toast('Không thể cập nhật trạng thái hoàn thành. Vui lòng thử lại.');
    } catch (error) {
      toast('Không kết nối được máy chủ. Vui lòng thử lại.');
    } finally {
      button.disabled = false;
    }
  });
  item.querySelector('.delete-button')?.addEventListener('click', async () => {
    if (!window.confirm('Xóa sự kiện này và các lần lặp của nó?')) return;
    const response = await fetch(`/api/events/${item.dataset.eventId}`, { method: 'DELETE' });
    if (response.ok) window.location.reload();
  });
});

document.querySelector('[data-save-schedule-image]')?.addEventListener('click', () => {
  const button = document.querySelector('[data-save-schedule-image]');
  const params = new URLSearchParams(window.location.search);
  const period = params.get('period') || 'week';
  const localToday = new Date();
  const anchorText = params.get('date') || `${localToday.getFullYear()}-${String(localToday.getMonth() + 1).padStart(2, '0')}-${String(localToday.getDate()).padStart(2, '0')}`;
  const [anchorYear, anchorMonth, anchorDay] = anchorText.split('-').map(Number);
  const anchor = new Date(anchorYear, anchorMonth - 1, anchorDay, 12);
  const moveDate = (date, amount) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + amount, 12);
  const isoDate = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  let start = anchor;
  let end = anchor;
  if (period === 'week') {
    start = moveDate(anchor, -((anchor.getDay() + 6) % 7));
    end = moveDate(start, 6);
  } else if (period === 'month') {
    start = new Date(anchor.getFullYear(), anchor.getMonth(), 1, 12);
    end = new Date(anchor.getFullYear(), anchor.getMonth() + 1, 0, 12);
  } else if (period === 'quarter') {
    const month = Math.floor(anchor.getMonth() / 3) * 3;
    start = new Date(anchor.getFullYear(), month, 1, 12);
    end = new Date(anchor.getFullYear(), month + 3, 0, 12);
  } else if (period === 'year') {
    start = new Date(anchor.getFullYear(), 0, 1, 12);
    end = new Date(anchor.getFullYear(), 11, 31, 12);
  }

  const eventsByDate = new Map();
  const categoryNames = { work: 'Công việc', personal: 'Cá nhân', health: 'Sức khỏe', study: 'Học tập', group_meeting: 'Họp nhóm', other: 'Khác' };
  document.querySelectorAll('.event-item[data-occurrence]').forEach((item) => {
    const copy = item.querySelector('.event-copy');
    const title = copy?.querySelector('strong')?.textContent.trim();
    const timeText = copy?.querySelector('span')?.textContent.trim() || '';
    const timeMatch = timeText.match(/(\d{1,2}:\d{2})\s*[–-]\s*(\d{1,2}:\d{2})/);
    if (!copy || !title || !timeMatch) return;
    const categoryKey = [...item.classList].find((name) => name.startsWith('category-'))?.slice(9) || 'other';
    const status = item.dataset.occurrenceStatus || 'planned';
    const missionChecks = [...item.querySelectorAll('.mission-check')];
    const event = {
      title,
      startTime: timeMatch[1],
      endTime: timeMatch[2],
      overnight: timeMatch[2] <= timeMatch[1],
      categoryKey,
      category: copy.querySelector('.category-tag')?.textContent.trim() || categoryNames[categoryKey] || 'Khác',
      status,
      statusNote: item.dataset.statusNote || '',
      missionTotal: missionChecks.length,
      missionDone: missionChecks.filter((checkbox) => checkbox.checked).length,
    };
    if (!eventsByDate.has(item.dataset.occurrence)) eventsByDate.set(item.dataset.occurrence, []);
    eventsByDate.get(item.dataset.occurrence).push(event);
  });

  const dateList = [];
  for (let date = start; date <= end; date = moveDate(date, 1)) dateList.push(new Date(date));
  const compactGrid = !['day', 'week'].includes(period);
  let displayDates = dateList;
  let weekRows = [];
  if (compactGrid) {
    const gridStart = moveDate(start, -((start.getDay() + 6) % 7));
    const gridEnd = moveDate(end, (7 - end.getDay()) % 7);
    displayDates = [];
    for (let date = gridStart; date <= gridEnd; date = moveDate(date, 1)) displayDates.push(new Date(date));
    for (let index = 0; index < displayDates.length; index += 7) weekRows.push(displayDates.slice(index, index + 7));
  } else {
    weekRows = [displayDates];
  }

  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const width = 1800;
  const margin = 48;
  const gap = 12;
  const columns = compactGrid ? 7 : displayDates.length;
  const colWidth = (width - margin * 2 - gap * (columns - 1)) / columns;
  const visibleLimit = compactGrid ? 3 : 10;
  const rowHeights = weekRows.map((row) => {
    const maxEvents = Math.max(0, ...row.map((date) => Math.min((eventsByDate.get(isoDate(date)) || []).length, visibleLimit)));
    return compactGrid ? Math.max(132, 44 + maxEvents * 68) : Math.max(420, 118 + maxEvents * 84);
  });
  const headerHeight = 142;
  canvas.width = width;
  canvas.height = headerHeight + rowHeights.reduce((sum, value) => sum + value, 0) + gap * weekRows.length + margin;

  const palette = {
    work: { bg: '#eaf8fa', edge: '#76c8c7', text: '#39797e' },
    personal: { bg: '#fff7d9', edge: '#e0c557', text: '#896d28' },
    health: { bg: '#eaf7ef', edge: '#7fc4a1', text: '#47795d' },
    study: { bg: '#fff0ef', edge: '#e89a9b', text: '#9b595d' },
    group_meeting: { bg: '#f1edff', edge: '#a48cdb', text: '#6b5897' },
    other: { bg: '#f0f1ec', edge: '#9ba69b', text: '#59675e' },
  };
  const roundRect = (x, y, w, h, radius, fill, stroke) => {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, radius);
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.stroke(); }
  };
  const drawWrapped = (text, x, y, maxWidth, lineHeight, maxLines = 2) => {
    const words = String(text).split(/\s+/);
    let line = '';
    let lines = [];
    for (const word of words) {
      const next = line ? `${line} ${word}` : word;
      if (ctx.measureText(next).width > maxWidth && line) {
        lines.push(line);
        line = word;
      } else line = next;
    }
    if (line) lines.push(line);
    if (lines.length > maxLines) {
      lines = lines.slice(0, maxLines);
      let last = lines[maxLines - 1];
      while (last && ctx.measureText(`${last}…`).width > maxWidth) last = last.slice(0, -1);
      lines[maxLines - 1] = `${last.trimEnd()}…`;
    }
    lines.forEach((value, index) => ctx.fillText(value, x, y + index * lineHeight));
    return lines.length;
  };
  const weekdayNames = ['Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy'];
  const titleRange = document.querySelector('.range-title strong')?.textContent.trim() || '';

  ctx.fillStyle = '#fff8e7';
  ctx.fillRect(0, 0, width, canvas.height);
  ctx.fillStyle = '#568f78';
  ctx.font = '700 17px "Segoe UI", sans-serif';
  ctx.fillText('DAYBOOK  ·  LỊCH TRÌNH', margin, 45);
  ctx.fillStyle = '#30414a';
  ctx.font = '700 32px "Segoe UI", sans-serif';
  ctx.fillText(titleRange ? `Lịch trình ${titleRange}` : 'Lịch trình', margin, 91);
  ctx.fillStyle = '#7f8b89';
  ctx.font = '14px "Segoe UI", sans-serif';
  ctx.fillText('Kế hoạch cá nhân', margin, 119);

  let y = headerHeight;
  weekRows.forEach((row, rowIndex) => {
    const rowHeight = rowHeights[rowIndex];
    row.forEach((date, columnIndex) => {
      const x = margin + columnIndex * (colWidth + gap);
      const dayKey = isoDate(date);
      const inRange = date >= start && date <= end;
      const dayEvents = (eventsByDate.get(dayKey) || []).sort((a, b) => a.startTime.localeCompare(b.startTime));
      roundRect(x, y, colWidth, rowHeight, 12, inRange ? '#fffefa' : '#f7f4ea', '#e9e5d9');
      ctx.fillStyle = inRange ? '#34454a' : '#a9aaa2';
      ctx.font = '700 12px "Segoe UI", sans-serif';
      ctx.fillText(`${weekdayNames[date.getDay()]} ${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}`, x + 12, y + 22);
      const cardHeight = compactGrid ? 62 : 76;
      const shown = dayEvents.slice(0, visibleLimit);
      shown.forEach((event, eventIndex) => {
        const cy = y + 32 + eventIndex * (cardHeight + 5);
        const colors = palette[event.categoryKey] || palette.other;
        const statusColor = event.status === 'cancelled' ? '#b65c59' : event.status === 'rescheduled' ? '#98772d' : colors.text;
        roundRect(x + 7, cy, colWidth - 14, cardHeight, 8, event.status === 'cancelled' ? '#f6eeea' : colors.bg, null);
        ctx.fillStyle = colors.edge;
        roundRect(x + 7, cy, 4, cardHeight, [8, 0, 0, 8], colors.edge, null);
        ctx.fillStyle = '#66736f';
        ctx.font = `600 ${compactGrid ? 9 : 11}px "Segoe UI", sans-serif`;
        const timeLabel = `${event.startTime}–${event.endTime}${event.overnight ? ' (+1 ngày)' : ''}`;
        ctx.fillText(timeLabel, x + 18, cy + (compactGrid ? 13 : 16));
        ctx.fillStyle = '#30414a';
        ctx.font = `600 ${compactGrid ? 10 : 13}px "Segoe UI", sans-serif`;
        drawWrapped(event.title, x + 18, cy + (compactGrid ? 28 : 36), colWidth - 34, compactGrid ? 12 : 15, 2);
        ctx.fillStyle = statusColor;
        ctx.font = `600 ${compactGrid ? 8 : 10}px "Segoe UI", sans-serif`;
        const metaY = cy + (compactGrid ? 55 : 63);
        const meta = event.status === 'cancelled' ? 'Đã hủy' : event.status === 'rescheduled' ? 'Đổi lịch' : event.category;
        ctx.fillText(meta, x + 18, metaY);
        if (event.missionTotal) {
          const missionText = `${event.missionDone}/${event.missionTotal} mission`;
          ctx.textAlign = 'right';
          ctx.fillStyle = '#568f78';
          ctx.fillText(missionText, x + colWidth - 16, metaY);
          ctx.textAlign = 'left';
        }
      });
      if (dayEvents.length > visibleLimit) {
        ctx.fillStyle = '#7c8791';
        ctx.font = '10px "Segoe UI", sans-serif';
        ctx.fillText(`+${dayEvents.length - visibleLimit} sự kiện khác`, x + 12, y + rowHeight - 10);
      }
    });
    y += rowHeight + gap;
  });

  button.disabled = true;
  button.textContent = 'Đang tạo ảnh…';
  canvas.toBlob((blob) => {
    button.disabled = false;
    button.textContent = 'Lưu ảnh';
    if (!blob) { toast('Không tạo được ảnh lịch.'); return; }
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `lich-trinh-${period}-${anchorText}.png`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    toast('Đã lưu ảnh lịch trình.');
  }, 'image/png');
});
