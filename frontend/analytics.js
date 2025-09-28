(function () {
  const API_URL = (function resolveApi() {
    const urlParam = new URLSearchParams(window.location.search).get('api');
    return urlParam || 'http://127.0.0.1:5000/api/decisions';
  })();

  // Chart instances
  let decisionChart = null;
  let cedantChart = null;
  let riskChart = null;
  let acceptanceChart = null;

  // DOM elements
  const statusEl = document.getElementById('status');
  const totalPremiumEl = document.getElementById('total-premium');
  const avgShareEl = document.getElementById('avg-share');
  const topCedantEl = document.getElementById('top-cedant');
  const riskExposureEl = document.getElementById('risk-exposure');
  const cedantPerformanceEl = document.getElementById('cedant-performance');
  const perilAnalysisEl = document.getElementById('peril-analysis');

  // Global data
  let allCases = [];

  // Theme management
  function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
  }

  window.toggleTheme = function() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    showNotification('Theme changed to ' + newTheme + ' mode', 'success');
    
    // Update chart themes
    updateChartThemes();
  };

  // Notification system
  function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.getElementById('notifications').appendChild(notification);
    
    setTimeout(() => {
      notification.remove();
    }, 3000);
  }

  // Utility functions
  function formatCurrency(amount) {
    if (!amount || isNaN(amount)) return 'KES 0';
    return new Intl.NumberFormat('en-KE', {
      style: 'currency',
      currency: 'KES',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  }

  function getChartColors() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
      primary: isDark ? '#60a5fa' : '#3b82f6',
      success: isDark ? '#4ade80' : '#22c55e',
      danger: isDark ? '#f87171' : '#ef4444',
      warning: isDark ? '#fbbf24' : '#f59e0b',
      text: isDark ? '#f3f4f6' : '#374151',
      grid: isDark ? '#374151' : '#e5e7eb',
      background: isDark ? '#1f2937' : '#ffffff'
    };
  }

  // Chart creation functions
  function createDecisionChart(data) {
    const ctx = document.getElementById('decisionChart').getContext('2d');
    const colors = getChartColors();
    
    const decisions = data.reduce((acc, item) => {
      const decision = item.Decision?.toLowerCase() || 'pending';
      acc[decision] = (acc[decision] || 0) + 1;
      return acc;
    }, {});

    if (decisionChart) decisionChart.destroy();
    
    decisionChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: Object.keys(decisions).map(d => d.charAt(0).toUpperCase() + d.slice(1)),
        datasets: [{
          data: Object.values(decisions),
          backgroundColor: [colors.success, colors.danger, colors.warning],
          borderColor: colors.background,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: colors.text }
          }
        }
      }
    });
  }

  function createCedantChart(data) {
    const ctx = document.getElementById('cedantChart').getContext('2d');
    const colors = getChartColors();
    
    const cedantData = data.reduce((acc, item) => {
      const cedant = item.Cedant || 'Unknown';
      if (!acc[cedant]) {
        acc[cedant] = { premium: 0, cases: 0 };
      }
      acc[cedant].premium += item.Accepted_Premium_KES || 0;
      acc[cedant].cases += 1;
      return acc;
    }, {});

    const sortedCedants = Object.entries(cedantData)
      .sort(([,a], [,b]) => b.premium - a.premium)
      .slice(0, 10);

    if (cedantChart) cedantChart.destroy();
    
    cedantChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: sortedCedants.map(([name]) => name.length > 15 ? name.substring(0, 15) + '...' : name),
        datasets: [{
          label: 'Premium (KES)',
          data: sortedCedants.map(([,data]) => data.premium),
          backgroundColor: colors.primary,
          borderColor: colors.primary,
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: colors.text } }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { 
              color: colors.text,
              callback: function(value) {
                return formatCurrency(value);
              }
            },
            grid: { color: colors.grid }
          },
          x: {
            ticks: { color: colors.text },
            grid: { color: colors.grid }
          }
        }
      }
    });
  }

  function createRiskChart(data) {
    const ctx = document.getElementById('riskChart').getContext('2d');
    const colors = getChartColors();
    
    const riskData = data.reduce((acc, item) => {
      const perils = item.Perils_Covered || 'Unknown';
      const perilList = typeof perils === 'string' ? perils.split(',').map(p => p.trim()) : [perils];
      
      perilList.forEach(peril => {
        if (!acc[peril]) {
          acc[peril] = { exposure: 0, cases: 0 };
        }
        acc[peril].exposure += item.Accepted_Liability_KES || 0;
        acc[peril].cases += 1;
      });
      
      return acc;
    }, {});

    const sortedRisks = Object.entries(riskData)
      .sort(([,a], [,b]) => b.exposure - a.exposure)
      .slice(0, 8);

    if (riskChart) riskChart.destroy();
    
    riskChart = new Chart(ctx, {
      type: 'polarArea',
      data: {
        labels: sortedRisks.map(([name]) => name.length > 20 ? name.substring(0, 20) + '...' : name),
        datasets: [{
          data: sortedRisks.map(([,data]) => data.exposure),
          backgroundColor: [
            colors.primary + '80',
            colors.success + '80',
            colors.danger + '80',
            colors.warning + '80',
            colors.primary + '60',
            colors.success + '60',
            colors.danger + '60',
            colors.warning + '60'
          ],
          borderColor: colors.background,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: colors.text }
          }
        },
        scales: {
          r: {
            ticks: { color: colors.text },
            grid: { color: colors.grid }
          }
        }
      }
    });
  }

  function createAcceptanceChart(data) {
    const ctx = document.getElementById('acceptanceChart').getContext('2d');
    const colors = getChartColors();
    
    // Group by month for time series
    const monthlyData = data.reduce((acc, item) => {
      // Use current date as placeholder since we don't have actual dates
      const date = new Date();
      const monthKey = date.toISOString().substring(0, 7); // YYYY-MM format
      
      if (!acc[monthKey]) {
        acc[monthKey] = { total: 0, accepted: 0 };
      }
      
      acc[monthKey].total += 1;
      if (item.Decision?.toLowerCase() === 'accept') {
        acc[monthKey].accepted += 1;
      }
      
      return acc;
    }, {});

    const sortedMonths = Object.entries(monthlyData)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-6); // Last 6 months

    if (acceptanceChart) acceptanceChart.destroy();
    
    acceptanceChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: sortedMonths.map(([month]) => new Date(month + '-01').toLocaleDateString('en-US', { month: 'short', year: 'numeric' })),
        datasets: [{
          label: 'Acceptance Rate (%)',
          data: sortedMonths.map(([,data]) => ((data.accepted / data.total) * 100).toFixed(1)),
          borderColor: colors.success,
          backgroundColor: colors.success + '20',
          fill: true,
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: colors.text } }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            ticks: { 
              color: colors.text,
              callback: function(value) {
                return value + '%';
              }
            },
            grid: { color: colors.grid }
          },
          x: {
            ticks: { color: colors.text },
            grid: { color: colors.grid }
          }
        }
      }
    });
  }

  function updateChartThemes() {
    if (decisionChart) createDecisionChart(allCases);
    if (cedantChart) createCedantChart(allCases);
    if (riskChart) createRiskChart(allCases);
    if (acceptanceChart) createAcceptanceChart(allCases);
  }

  // Analytics calculations
  function updateMetrics(data) {
    const totalPremium = data.reduce((sum, item) => sum + (item.Accepted_Premium_KES || 0), 0);
    const avgShare = data.length > 0 ? 
      data.reduce((sum, item) => sum + (item.Accepted_Share_Pct || 0), 0) / data.length : 0;
    
    const cedantCounts = data.reduce((acc, item) => {
      const cedant = item.Cedant || 'Unknown';
      acc[cedant] = (acc[cedant] || 0) + 1;
      return acc;
    }, {});
    
    const topCedant = Object.entries(cedantCounts)
      .sort(([,a], [,b]) => b - a)[0]?.[0] || '—';
    
    const totalExposure = data.reduce((sum, item) => sum + (item.Accepted_Liability_KES || 0), 0);

    totalPremiumEl.textContent = formatCurrency(totalPremium);
    avgShareEl.textContent = avgShare.toFixed(1) + '%';
    topCedantEl.textContent = topCedant;
    riskExposureEl.textContent = formatCurrency(totalExposure);
  }

  function updateCedantPerformance(data) {
    const cedantData = data.reduce((acc, item) => {
      const cedant = item.Cedant || 'Unknown';
      if (!acc[cedant]) {
        acc[cedant] = { cases: 0, accepted: 0, premium: 0, totalShare: 0 };
      }
      acc[cedant].cases += 1;
      if (item.Decision?.toLowerCase() === 'accept') {
        acc[cedant].accepted += 1;
      }
      acc[cedant].premium += item.Accepted_Premium_KES || 0;
      acc[cedant].totalShare += item.Accepted_Share_Pct || 0;
      return acc;
    }, {});

    const sortedCedants = Object.entries(cedantData)
      .sort(([,a], [,b]) => b.premium - a.premium)
      .slice(0, 10);

    cedantPerformanceEl.innerHTML = "";
    sortedCedants.forEach(([cedant, data]) => {
      const tr = document.createElement('tr');
      const acceptanceRate = data.cases > 0 ? (data.accepted / data.cases * 100).toFixed(1) : '0.0';
      const avgShare = data.cases > 0 ? (data.totalShare / data.cases).toFixed(1) : '0.0';
      
      tr.innerHTML = `
        <td>${cedant}</td>
        <td>${data.cases}</td>
        <td>${acceptanceRate}%</td>
        <td>${formatCurrency(data.premium)}</td>
        <td>${avgShare}%</td>
      `;
      cedantPerformanceEl.appendChild(tr);
    });
  }

  function updatePerilAnalysis(data) {
    const perilData = data.reduce((acc, item) => {
      const perils = item.Perils_Covered || 'Unknown';
      const perilList = typeof perils === 'string' ? perils.split(',').map(p => p.trim()) : [perils];
      
      perilList.forEach(peril => {
        if (!acc[peril]) {
          acc[peril] = { cases: 0, accepted: 0, exposure: 0, premium: 0 };
        }
        acc[peril].cases += 1;
        if (item.Decision?.toLowerCase() === 'accept') {
          acc[peril].accepted += 1;
        }
        acc[peril].exposure += item.Accepted_Liability_KES || 0;
        acc[peril].premium += item.Accepted_Premium_KES || 0;
      });
      
      return acc;
    }, {});

    const sortedPerils = Object.entries(perilData)
      .sort(([,a], [,b]) => b.exposure - a.exposure)
      .slice(0, 10);

    perilAnalysisEl.innerHTML = '';
    sortedPerils.forEach(([peril, data]) => {
      const tr = document.createElement('tr');
      const acceptanceRate = data.cases > 0 ? (data.accepted / data.cases * 100).toFixed(1) : '0.0';
      const avgPremiumRate = data.exposure > 0 ? (data.premium / data.exposure * 1000).toFixed(2) : '0.00';
      
      tr.innerHTML = `
        <td>${peril}</td>
        <td>${data.cases}</td>
        <td>${formatCurrency(data.exposure)}</td>
        <td>${acceptanceRate}%</td>
        <td>${avgPremiumRate}‰</td>
      `;
      perilAnalysisEl.appendChild(tr);
    });
  }

  // Export functionality
  window.exportAnalytics = function() {
    const reportData = generateAnalyticsReport(allCases);
    downloadJSON(reportData, 'analytics_report_' + new Date().toISOString().split('T')[0] + '.json');
    showNotification('Analytics report exported successfully', 'success');
  };

  function generateAnalyticsReport(data) {
    return {
      reportDate: new Date().toISOString(),
      summary: {
        totalCases: data.length,
        acceptedCases: data.filter(c => c.Decision?.toLowerCase() === 'accept').length,
        totalPremium: data.reduce((sum, item) => sum + (item.Accepted_Premium_KES || 0), 0),
        totalExposure: data.reduce((sum, item) => sum + (item.Accepted_Liability_KES || 0), 0),
        averageShare: data.length > 0 ? data.reduce((sum, item) => sum + (item.Accepted_Share_Pct || 0), 0) / data.length : 0
      },
      cedantAnalysis: Object.entries(data.reduce((acc, item) => {
        const cedant = item.Cedant || 'Unknown';
        if (!acc[cedant]) acc[cedant] = { cases: 0, premium: 0 };
        acc[cedant].cases += 1;
        acc[cedant].premium += item.Accepted_Premium_KES || 0;
        return acc;
      }, {})).map(([cedant, data]) => ({ cedant, ...data })),
      perilAnalysis: Object.entries(data.reduce((acc, item) => {
        const perils = item.Perils_Covered || 'Unknown';
        const perilList = typeof perils === 'string' ? perils.split(',').map(p => p.trim()) : [perils];
        perilList.forEach(peril => {
          if (!acc[peril]) acc[peril] = { cases: 0, exposure: 0 };
          acc[peril].cases += 1;
          acc[peril].exposure += item.Accepted_Liability_KES || 0;
        });
        return acc;
      }, {})).map(([peril, data]) => ({ peril, ...data }))
    };
  }

  function downloadJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Chart update function
  window.updateCharts = function() {
    if (allCases.length > 0) {
      createDecisionChart(allCases);
      createCedantChart(allCases);
      createRiskChart(allCases);
      createAcceptanceChart(allCases);
      showNotification('Charts updated successfully', 'success');
    }
  };

  // Data refresh
  window.refreshData = function() {
    load();
  };

  // Main load function
  async function load() {
    statusEl.innerHTML = '<div class="status-dot"></div><span>Loading analytics...</span>';
    
    try {
      const res = await fetch(API_URL, { credentials: 'omit' });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      
      const data = await res.json();
      if (!Array.isArray(data)) {
        throw new Error('Invalid API response format');
      }

      allCases = data;
      
      // Update all analytics
      updateMetrics(data);
      updateCedantPerformance(data);
      updatePerilAnalysis(data);
      if (allCases.length === 0) {
        cedantPerformanceEl.innerHTML = '<tr><td colspan="5">No data available</td></tr>';
        perilAnalysisEl.innerHTML = '<tr><td colspan="5">No data available</td></tr>';
      }
      
      // Create charts
      createDecisionChart(data);
      createCedantChart(data);
      createRiskChart(data);
      createAcceptanceChart(data);
      
      statusEl.innerHTML = `
        <div class="status-dot"></div>
        <span>Analytics loaded (${data.length} cases)</span>
      `;

      showNotification(`Analytics updated with ${data.length} cases`, 'success');
      
    } catch (err) {
      console.error('Load error:', err);
      statusEl.innerHTML = `
        <div style="width: 8px; height: 8px; border-radius: 50%; background-color: var(--danger-500);"></div>
        <span>Failed to load analytics</span>
      `;
      
      showNotification('Failed to load analytics data. Please check if the backend is running.', 'error');
    }
  }

  // Initialize
  initTheme();
  load();

  // Auto-refresh every 10 minutes
  setInterval(load, 10 * 60 * 1000);

})();
