(function () {
  const API_URL = (function resolveApi() {
    const urlParam = new URLSearchParams(window.location.search).get('api');
    return urlParam || 'http://127.0.0.1:5000/api/decisions';
  })();

  const statusEl = document.getElementById('status');
  const casesEl = document.getElementById('cases');
  const searchInput = document.getElementById('search-input');
  const decisionFilter = document.getElementById('decision-filter');
  const sortBy = document.getElementById('sort-by');
  const emptyState = document.getElementById('empty-state');

  const totalCasesEl = document.getElementById('total-cases');
  const acceptedCasesEl = document.getElementById('accepted-cases');
  const declinedCasesEl = document.getElementById('declined-cases');
  const acceptanceRateEl = document.getElementById('acceptance-rate');

  let allCases = [];
  let filteredCases = [];

  function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
  }

  function showNotification(message, type = 'success') {
    const n = document.createElement('div');
    n.className = `notification ${type}`;
    n.textContent = message;
    document.getElementById('notifications').appendChild(n);
    setTimeout(() => n.remove(), 3000);
  }

  function td(text) {
    const e = document.createElement('td');
    e.textContent = text;
    return e;
  }

  function decisionBadge(textValue) {
    const span = document.createElement('span');
    const v = (textValue || 'N/A').toLowerCase();
    span.className = `badge ${v === 'accept' ? 'accept' : v === 'decline' ? 'decline' : 'pending'}`;
    span.textContent = textValue || 'N/A';
    return span;
  }

  function formatCurrency(amount) {
    if (amount == null || isNaN(Number(amount))) return '—';
    return new Intl.NumberFormat('en-KE', { style: 'currency', currency: 'KES', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Number(amount));
  }

  function updateStats(cases) {
    const total = cases.length;
    const accepted = cases.filter(c => (c.Decision || '').toLowerCase() === 'accept').length;
    const declined = cases.filter(c => (c.Decision || '').toLowerCase() === 'decline').length;
    const rate = total ? Math.round((accepted / total) * 100) : 0;
    totalCasesEl.textContent = total;
    acceptedCasesEl.textContent = accepted;
    declinedCasesEl.textContent = declined;
    acceptanceRateEl.textContent = rate + '%';
  }

  function renderTable(cases) {
    casesEl.innerHTML = '';
    if (cases.length === 0) {
      emptyState.style.display = 'block';
      document.querySelector('.table-container').style.display = 'none';
      return;
    }
    emptyState.style.display = 'none';
    document.querySelector('.table-container').style.display = 'block';

    cases.forEach((item, i) => {
      const tr = document.createElement('tr');
      // Row click opens full report (except when clicking links/buttons)
      tr.addEventListener('click', function(e) {
        if (e.target && (e.target.closest('a') || e.target.closest('button'))) return;
        window.location.href = `detail.html?${query}`;
        try { localStorage.setItem('detailApi', targetApi); localStorage.setItem('detailIndex', String(i)); } catch (err) {}
      });
      tr.classList.add('row-click');

      // Clickable row number opens full report
      const numCell = document.createElement('td');
      const aNum = document.createElement('a');
      const targetApi = new URL(API_URL, window.location.href).toString();
      const query = new URLSearchParams({ id: String(i), api: targetApi }).toString();
      aNum.href = `detail.html?${query}`;
      aNum.textContent = String(i + 1);
      aNum.title = 'View full report';
      aNum.addEventListener('click', function () {
        try { localStorage.setItem('detailApi', targetApi); localStorage.setItem('detailIndex', String(i)); } catch (e) {}
      });
      numCell.appendChild(aNum);
      tr.appendChild(numCell);

      tr.appendChild(td(item.Insured || '—'));
      tr.appendChild(td(item.Cedant || '—'));
      tr.appendChild(td(item.Broker || '—'));

      const decisionCell = document.createElement('td');
      decisionCell.appendChild(decisionBadge(item.Decision));
      tr.appendChild(decisionCell);

      tr.appendChild(td(((Number(item.Accepted_Share_Pct) || 0)) + '%'));
      tr.appendChild(td(formatCurrency(item.Accepted_Premium_KES)));

      const actionsCell = document.createElement('td');
      const viewBtn = document.createElement('a');
      viewBtn.href = `detail.html?${query}`;
      viewBtn.className = 'btn btn-primary';
      viewBtn.style.fontSize = '0.75rem';
      viewBtn.style.padding = '0.25rem 0.5rem';
      viewBtn.textContent = 'View Report';
      viewBtn.title = 'View full working sheet';
      viewBtn.addEventListener('click', function () {
        try { localStorage.setItem('detailApi', targetApi); localStorage.setItem('detailIndex', String(i)); } catch (e) {}
      });
      actionsCell.appendChild(viewBtn);
      tr.appendChild(actionsCell);

      casesEl.appendChild(tr);
    });
  }

  window.filterTable = function () {
    const searchTerm = (searchInput.value || '').toLowerCase();
    const decisionValue = (decisionFilter.value || '').toLowerCase();
    filteredCases = allCases.filter(item => {
      const s = searchTerm === '' || (item.Insured || '').toLowerCase().includes(searchTerm) || (item.Cedant || '').toLowerCase().includes(searchTerm) || (item.Broker || '').toLowerCase().includes(searchTerm);
      const d = decisionValue === '' || (item.Decision || '').toLowerCase() === decisionValue;
      return s && d;
    });
    renderTable(filteredCases);
    updateStats(filteredCases);
  };

  window.sortTable = function () {
    const v = sortBy.value;
    if (!v) return;
    const m = {
      insured: (a, b) => (a.Insured || '').localeCompare(b.Insured || ''),
      cedant: (a, b) => (a.Cedant || '').localeCompare(b.Cedant || ''),
      decision: (a, b) => (a.Decision || '').localeCompare(b.Decision || ''),
      share: (a, b) => (Number(b.Accepted_Share_Pct) || 0) - (Number(a.Accepted_Share_Pct) || 0),
    };
    if (m[v]) {
      filteredCases.sort(m[v]);
      renderTable(filteredCases);
    }
  };

  window.clearFilters = function () {
    searchInput.value = '';
    decisionFilter.value = '';
    sortBy.value = '';
    filteredCases = [...allCases];
    renderTable(filteredCases);
    updateStats(filteredCases);
    showNotification('Filters cleared', 'success');
  };

  window.refreshData = function () { load(); };

  async function load() {
    statusEl.innerHTML = '<div class="status-dot"></div><span>Loading...</span>';
    try {
      const res = await fetch(API_URL, { credentials: 'omit' });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data = await res.json();
      if (!Array.isArray(data)) throw new Error('Invalid API response');
      allCases = data;
      filteredCases = [...data];
      renderTable(filteredCases);
      updateStats(filteredCases);
      statusEl.innerHTML = `<div class="status-dot"></div><span>Loaded ${data.length} case${data.length !== 1 ? 's' : ''}</span>`;
    } catch (err) {
      console.error(err);
      statusEl.innerHTML = '<div style="width: 8px; height: 8px; border-radius: 50%; background-color: var(--danger-500);"></div><span>Failed to load data</span>';
      showNotification('Failed to load data. Please check the backend.', 'error');
      emptyState.style.display = 'block';
      document.querySelector('.table-container').style.display = 'none';
    }
  }

  initTheme();
  load();
  setInterval(load, 5 * 60 * 1000);
})();
