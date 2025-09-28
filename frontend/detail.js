(function () {
  const params = new URLSearchParams(window.location.search);
  const idParam = params.get('id') || localStorage.getItem('detailIndex');
  const API_URL = params.get('api') || localStorage.getItem('detailApi') || 'http://127.0.0.1:5000/api/decisions';

  const statusEl = document.getElementById('status');
  const tbody = document.getElementById('tbody');

  function setHeader(caseData) {
    document.getElementById('f-insured').textContent = caseData.Insured || '—';
    document.getElementById('f-cedant').textContent = caseData.Cedant || '—';
    document.getElementById('f-broker').textContent = caseData.Broker || '—';
    const d = (caseData.Decision || 'N/A').toLowerCase();
    const badge = document.getElementById('f-decision');
    badge.textContent = caseData.Decision || 'N/A';
    badge.classList.remove('accept', 'decline');
    badge.classList.add(d === 'accept' ? 'accept' : 'decline');
  }

  function row(guideline, value) {
    const tr = document.createElement('tr');
    const th = document.createElement('th');
    th.textContent = guideline;
    const td = document.createElement('td');
    td.innerHTML = value;
    tr.appendChild(th);
    tr.appendChild(td);
    return tr;
  }

  function text(v) {
    try {
      if (v === null || v === undefined) return "—";
      if (typeof v === "number") {
        if (!isFinite(v)) return "—";
        return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(v);
      }
      if (Array.isArray(v)) {
        return v.map(x => String(x)).join(", ");
      }
      if (typeof v === "object") return `<pre>${escapeHtml(JSON.stringify(v, null, 2))}</pre>`;
      const s = String(v);
      return s;
    } catch (e) {
      return String(v ?? "—");
    }
    if (v === null || v === undefined) return '—';
    if (typeof v === 'object') return `<pre>${escapeHtml(JSON.stringify(v, null, 2))}</pre>`;
    return String(v);
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  }

  function currency(amount, code) {
    if (amount === null || amount === undefined || isNaN(amount)) return '—';
    const num = Number(amount);
    return `${code || ''} ${num.toLocaleString(undefined, { maximumFractionDigits: 2 })}`.trim();
  }

  function percent(p) {
    if (p === null || p === undefined || isNaN(p)) return '—';
    return `${Number(p).toFixed(2)}%`;
  }

  function buildRows(c) {
    const rows = [];
    rows.push(row('Insured', text(c.Insured)));
    rows.push(row('Cedant', text(c.Cedant)));
    rows.push(row('Broker', text(c.Broker)));
    rows.push(row('Perils Covered', text(c.Perils_Covered)));
    rows.push(row('Geographical Limit (Country/Region)', text(c.Geographical_Limit)));
    rows.push(row('Situation of Risk/Voyage', text(c.Situation_of_Risk)));
    rows.push(row('Occupation of Insured', text(c.Occupation_of_Insured)));
    rows.push(row('Main Activities', text(c.Main_Activities)));

    const tsiParts = [];
    tsiParts.push(`<div><b>Total Sum Insured (Original):</b> ${currency(c.TSI_Original_Currency, c.Original_Currency)}</div>`);
    if (c.TSI_KES !== undefined) {
      tsiParts.push(`<div><b>Total Sum Insured (KES):</b> ${currency(c.TSI_KES, 'KES')}</div>`);
    }
    rows.push(row('Total Sum Insured (TSI) & Breakdown', tsiParts.join('')));

    rows.push(row('Excess/Deductible', currency(c.Excess_Deductible, c.Original_Currency)));
    rows.push(row('Retention of Cedant (%)', percent(c.Retention_of_Cedant_Pct)));
    rows.push(row('Possible Maximum Loss (PML %)', percent(c.PML_Pct)));

    const cat = c.CAT_Exposure || {};
    rows.push(row('CAT Exposure', `<div>Earthquake: ${text(cat.Earthquake)}</div><div>Flood: ${text(cat.Flood)}</div><div>Typhoon: ${text(cat.Typhoon)}</div>`));

    const period = [];
    if (c.Period_Start) period.push(`From: ${text(c.Period_Start)}`);
    if (c.Period_End) period.push(`To: ${text(c.Period_End)}`);
    rows.push(row('Period of Insurance', period.join(' • ') || '—'));

    rows.push(row('Reinsurance Deductions', '—'));

    const claims = `<div>Paid (3y): ${currency(c.Paid_Losses_3_Years, c.Original_Currency)}</div>
                    <div>Outstanding (3y): ${currency(c.Outstanding_Reserves_3_Years, c.Original_Currency)}</div>
                    <div>Recoveries (3y): ${currency(c.Recoveries_3_Years, c.Original_Currency)}</div>
                    <div>Earned Premium (3y): ${currency(c.Earned_Premium_3_Years, c.Original_Currency)}</div>
                    <div>Loss Ratio: ${percent(c.Loss_Ratio_Pct)}</div>`;
    rows.push(row('Claims Experience (Last 3 years)', claims));

    rows.push(row('Share Offered (%)', percent(c.Share_Offered_Pct)));
    rows.push(row('Inward Acceptances', '—'));
    rows.push(row("Risk Surveyor’s Report", '—'));

    const rate = `<div>Rate (%): ${text(c.Premium_Rate_Percentage)}</div><div>Rate (‰): ${text(c.Premium_Rate_Permille)}</div>`;
    rows.push(row('Premium Rates', rate));

    const prem = [];
    prem.push(`<div>Premium (Original): ${currency(c.Premium_Original_Currency, c.Original_Currency)}</div>`);
    if (c.Premium_KES !== undefined) prem.push(`<div>Premium (KES): ${currency(c.Premium_KES, 'KES')}</div>`);
    rows.push(row('Premium', prem.join('')));

    rows.push(row('Climate Change Risk Factors', text(c.Climate_Change_Risk || (c.Climate_ESG_Risk && c.Climate_ESG_Risk.ClimateRisk))))
    rows.push(row('ESG Risk Assessment', text(c.ESG_Risk_Level || (c.Climate_ESG_Risk && c.Climate_ESG_Risk.ESGRisk))))

    const proposedShare = (c.Proposed_Share && c.Proposed_Share.ProposedShare_percent) ?? c.Accepted_Share_Pct;
    rows.push(row('% Share (Proposed Acceptance)', percent(proposedShare)));

    const liability = `<div>Accepted Liability (KES): ${currency(c.Accepted_Liability_KES, 'KES')}</div>`;
    rows.push(row('Liability (Original currency & KES)', liability));

    const premiumAccepted = `<div>Accepted Premium (KES): ${currency(c.Accepted_Premium_KES, 'KES')}</div>`;
    rows.push(row('Premium (Original currency & KES)', premiumAccepted));

    rows.push(row('Remarks', text(c.Remarks)));

    const assessment = [];
    if (c.Market_Considerations) assessment.push(`<div><b>Market Considerations:</b> ${escapeHtml(JSON.stringify(c.Market_Considerations))}</div>`);
    if (c.Portfolio_Impact) assessment.push(`<div><b>Portfolio Impact:</b> ${escapeHtml(JSON.stringify(c.Portfolio_Impact))}</div>`);
    if (c.CAT_Exposure) assessment.push(`<div><b>CAT Exposure:</b> ${escapeHtml(JSON.stringify(c.CAT_Exposure))}</div>`);
    rows.push(row('Technical Assessment', assessment.join('')));

    rows.push(row('Market Considerations', text(c.Market_Considerations && c.Market_Considerations.CompetitorRate_per_mille !== undefined ? `${c.Market_Considerations.CompetitorRate_per_mille} ‰` : '—')));

    rows.push(row('Portfolio Impact', text(c.Portfolio_Impact && c.Portfolio_Impact.PortfolioImpact ? c.Portfolio_Impact.PortfolioImpact : '—')));

    rows.push(row('Proposed Terms & Conditions', text(c.Proposed_Terms_Conditions)));

    rows.push(row('Positive Assessment', text(c.Positive_Assessment)));

    rows.push(row('I propose we write … % share', percent(proposedShare)));

    rows.push(row('Signature/Date/Time', text(c.Underwriter_Signoff || new Date().toISOString())));

    rows.push(row('Manager’s Comments', text(c.Manager_Comments)));

    return rows;
  }

  async function load() {
    if (!idParam) {
      statusEl.textContent = 'Missing ?id= query parameter';
      return;
    }
    const index = Number(idParam);
    if (isNaN(index)) {
      statusEl.textContent = 'Invalid id parameter';
      return;
    }

    statusEl.textContent = 'Loading case…';
    try {
      const res = await fetch(API_URL);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (!Array.isArray(data)) throw new Error('Invalid API response');
      if (index < 0 || index >= data.length) {
        tbody.innerHTML = "<tr><td colspan=2>Case not found</td></tr>";
        statusEl.textContent = "Case not found";
        return;
      }
      const caseData = data[index];
      setHeader(caseData);
      tbody.innerHTML = '';
      buildRows(caseData).forEach((r) => tbody.appendChild(r));
      statusEl.textContent = 'Loaded';
    } catch (e) {
      console.error(e);
      statusEl.textContent = 'Failed to load case';
    }
  }

  load();
})(); 