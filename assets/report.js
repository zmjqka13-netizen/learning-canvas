(() => {
  'use strict';
  const fields = [...document.querySelectorAll('[data-save], [data-done], [data-gap]')];
  const reportKey = document.body.dataset.reportKey;
  const storageKey = 'learning-canvas:v1:' + reportKey;
  const status = document.querySelector('#save-status');
  const progress = document.querySelector('#read-progress');
  let storageEnabled = true;
  const fieldKey = el => el.dataset.save || (el.dataset.done ? 'done:' + el.dataset.done : 'gap:' + el.dataset.gap);
  function record() {
    const values = {};
    fields.forEach(el => { values[fieldKey(el)] = el.type === 'checkbox' ? el.checked : el.value; });
    return {reportKey, values, savedAt: new Date().toISOString()};
  }
  function updateProgress() {
    const frames = fields.filter(el => el.dataset.done);
    const completed = frames.filter(el => el.checked).length;
    progress.max = frames.length;
    progress.value = completed;
    document.querySelector('#progress-text').textContent = `${completed} / ${frames.length} 帧已自评完成`;
  }
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
    if (saved && saved.reportKey === reportKey && saved.values && typeof saved.values === 'object') {
      fields.forEach(el => {
        const value = saved.values[fieldKey(el)];
        if (el.type === 'checkbox') el.checked = value === true;
        else if (typeof value === 'string') el.value = value;
      });
    }
    localStorage.setItem(storageKey, JSON.stringify(record()));
    status.textContent = '记录保存在当前浏览器；请导出重要练习。';
  } catch (_) {
    storageEnabled = false;
    status.textContent = '浏览器不允许本地保存；本页仍可练习，请导出记录。';
  }
  fields.forEach(el => el.addEventListener('input', () => {
    updateProgress();
    if (storageEnabled) {
      try { localStorage.setItem(storageKey, JSON.stringify(record())); }
      catch (_) { storageEnabled = false; status.textContent = '保存失败，请导出练习记录。'; }
    }
  }));
  document.querySelector('#collapse-frames').addEventListener('click', () => {
    document.querySelectorAll('.frame details').forEach(el => { el.open = false; });
    document.querySelector('#own-words').focus();
  });
  document.querySelector('#expand-frames').addEventListener('click', () => {
    document.querySelectorAll('.frame details').forEach(el => { el.open = true; });
  });
  document.querySelector('#export-record').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(record(), null, 2)], {type:'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = 'learning-canvas-practice.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.querySelector('#clear-record').addEventListener('click', () => {
    if (!window.confirm('清空这份报告在当前浏览器中的练习记录？请先导出需要保留的内容。')) return;
    fields.forEach(el => { if (el.type === 'checkbox') el.checked = false; else el.value = ''; });
    try { localStorage.removeItem(storageKey); } catch (_) {}
    updateProgress();
  });
  let priorPrintState = [];
  window.addEventListener('beforeprint', () => {
    priorPrintState = [...document.querySelectorAll('details')].map(el => [el,el.open]);
    priorPrintState.forEach(([el]) => { el.open = true; });
  });
  window.addEventListener('afterprint', () => priorPrintState.forEach(([el,open]) => { el.open = open; }));
  updateProgress();
})();
