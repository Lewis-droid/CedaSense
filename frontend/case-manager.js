(function () {
  // Mock API endpoints (in a real app, these would be actual backend endpoints)
  const API_URL = 'http://127.0.0.1:5000/api/decisions';
  const CASES_API = 'http://127.0.0.1:5000/api/cases'; // Mock endpoint for case management

  // DOM elements
  const statusEl = document.getElementById('status');
  const casesTableEl = document.getElementById('cases-table');
  const searchInput = document.getElementById('search-input');
  const statusFilter = document.getElementById('status-filter');
  const priorityFilter = document.getElementById('priority-filter');
  const emptyState = document.getElementById('empty-state');
  const selectAllCheckbox = document.getElementById('select-all');
  
  // Stats elements
  const pendingCasesEl = document.getElementById('pending-cases');
  const draftCasesEl = document.getElementById('draft-cases');
  const urgentCasesEl = document.getElementById('urgent-cases');
  const totalManagedEl = document.getElementById('total-managed');

  // Modal elements
  const caseModal = document.getElementById('case-modal');
  const confirmModal = document.getElementById('confirm-modal');
  const caseForm = document.getElementById('case-form');

  // Global data
  let allCases = [];
  let filteredCases = [];
  let editingCaseId = null;
  let selectedCases = new Set();
  let confirmCallback = null;

  // Mock local storage for case management (in real app, this would be backend)
  function getManagedCases() {
    const stored = localStorage.getItem('managedCases');
    return stored ? JSON.parse(stored) : [];
  }

  function saveManagedCases(cases) {
    localStorage.setItem('managedCases', JSON.stringify(cases));
  }

  function generateCaseId() {
    return 'CASE-' + Date.now() + '-' + Math.random().toString(36).substr(2, 5).toUpperCase();
  }

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

  function formatDate(dateString) {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  }

  function createStatusBadge(status) {
    const span = document.createElement('span');
    span.className = `badge ${status}`;
    const statusText = {
      'draft': 'Draft',
      'pending': 'Pending',
      'approved': 'Approved',
      'rejected': 'Rejected'
    };
    span.textContent = statusText[status] || status;
    return span;
  }

  function createPriorityBadge(priority) {
    const span = document.createElement('span');
    const priorityClass = {
      'high': 'danger',
      'medium': 'warning',
      'low': 'accept'
    };
    span.className = `badge ${priorityClass[priority] || 'pending'}`;
    span.textContent = priority.charAt(0).toUpperCase() + priority.slice(1);
    return span;
  }

  // Statistics calculation
  function updateStats(cases) {
    const pending = cases.filter(c => c.status === 'pending').length;
    const draft = cases.filter(c => c.status === 'draft').length;
    const urgent = cases.filter(c => c.priority === 'high' && c.status !== 'approved').length;
    const total = cases.length;

    pendingCasesEl.textContent = pending;
    draftCasesEl.textContent = draft;
    urgentCasesEl.textContent = urgent;
    totalManagedEl.textContent = total;
  }

  // Table rendering
  function renderTable(cases) {
    casesTableEl.innerHTML = '';
    
    if (cases.length === 0) {
      emptyState.style.display = 'block';
      document.querySelector('.table-container').style.display = 'none';
      return;
    }

    emptyState.style.display = 'none';
    document.querySelector('.table-container').style.display = 'block';

    cases.forEach((caseItem, index) => {
      const tr = document.createElement('tr');
      
      // Checkbox
      const checkboxCell = document.createElement('td');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.value = caseItem.id;
      checkbox.checked = selectedCases.has(caseItem.id);
      checkbox.onchange = () => toggleCaseSelection(caseItem.id);
      checkboxCell.appendChild(checkbox);
      tr.appendChild(checkboxCell);
      
      // Case data
      const cells = [
        caseItem.id,
        caseItem.insured || '—',
        caseItem.cedant || '—'
      ];
      
      cells.forEach(text => {
        const td = document.createElement('td');
        td.textContent = text;
        tr.appendChild(td);
      });
      
      // Status badge
      const statusCell = document.createElement('td');
      statusCell.appendChild(createStatusBadge(caseItem.status));
      tr.appendChild(statusCell);
      
      // Priority badge
      const priorityCell = document.createElement('td');
      priorityCell.appendChild(createPriorityBadge(caseItem.priority));
      tr.appendChild(priorityCell);
      
      // Premium
      const premiumCell = document.createElement('td');
      premiumCell.textContent = formatCurrency(caseItem.premium);
      tr.appendChild(premiumCell);
      
      // Created date
      const dateCell = document.createElement('td');
      dateCell.textContent = formatDate(caseItem.createdAt);
      tr.appendChild(dateCell);
      
      // Actions
      const actionsCell = document.createElement('td');
      const actionsDiv = document.createElement('div');
      actionsDiv.className = 'flex gap-2';
      
      // Edit button
      const editBtn = document.createElement('button');
      editBtn.className = 'btn btn-secondary';
      editBtn.style.fontSize = '0.75rem';
      editBtn.style.padding = '0.25rem 0.5rem';
      editBtn.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
      `;
      editBtn.onclick = () => editCase(caseItem.id);
      actionsDiv.appendChild(editBtn);
      
      // Delete button
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn btn-danger';
      deleteBtn.style.fontSize = '0.75rem';
      deleteBtn.style.padding = '0.25rem 0.5rem';
      deleteBtn.innerHTML = `
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="3,6 5,6 21,6"/>
          <path d="M19,6v14a2,2 0 0,1 -2,2H7a2,2 0 0,1 -2,-2V6m3,0V4a2,2 0 0,1 2,-2h4a2,2 0 0,1 2,2v2"/>
        </svg>
      `;
      deleteBtn.onclick = () => deleteCase(caseItem.id);
      actionsDiv.appendChild(deleteBtn);
      
      // Approve/Reject buttons for pending cases
      if (caseItem.status === 'pending') {
        const approveBtn = document.createElement('button');
        approveBtn.className = 'btn btn-success';
        approveBtn.style.fontSize = '0.75rem';
        approveBtn.style.padding = '0.25rem 0.5rem';
        approveBtn.innerHTML = `
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20,6 9,17 4,12"/>
          </svg>
        `;
        approveBtn.onclick = () => approveCase(caseItem.id);
        actionsDiv.appendChild(approveBtn);
        
        const rejectBtn = document.createElement('button');
        rejectBtn.className = 'btn btn-danger';
        rejectBtn.style.fontSize = '0.75rem';
        rejectBtn.style.padding = '0.25rem 0.5rem';
        rejectBtn.innerHTML = `
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        `;
        rejectBtn.onclick = () => rejectCase(caseItem.id);
        actionsDiv.appendChild(rejectBtn);
      }
      
      actionsCell.appendChild(actionsDiv);
      tr.appendChild(actionsCell);
      
      casesTableEl.appendChild(tr);
    });
  }

  // Case selection
  function toggleCaseSelection(caseId) {
    if (selectedCases.has(caseId)) {
      selectedCases.delete(caseId);
    } else {
      selectedCases.add(caseId);
    }
    updateSelectAllCheckbox();
  }

  window.toggleSelectAll = function() {
    if (selectAllCheckbox.checked) {
      filteredCases.forEach(c => selectedCases.add(c.id));
    } else {
      selectedCases.clear();
    }
    renderTable(filteredCases);
  };

  function updateSelectAllCheckbox() {
    const visibleCaseIds = filteredCases.map(c => c.id);
    const selectedVisibleCases = visibleCaseIds.filter(id => selectedCases.has(id));
    
    selectAllCheckbox.checked = visibleCaseIds.length > 0 && selectedVisibleCases.length === visibleCaseIds.length;
    selectAllCheckbox.indeterminate = selectedVisibleCases.length > 0 && selectedVisibleCases.length < visibleCaseIds.length;
  }

  // Filtering and searching
  window.filterCases = function() {
    const searchTerm = searchInput.value.toLowerCase();
    const statusValue = statusFilter.value;
    const priorityValue = priorityFilter.value;

    filteredCases = allCases.filter(caseItem => {
      const matchesSearch = !searchTerm || 
        (caseItem.insured || '').toLowerCase().includes(searchTerm) ||
        (caseItem.cedant || '').toLowerCase().includes(searchTerm) ||
        (caseItem.id || '').toLowerCase().includes(searchTerm);

      const matchesStatus = !statusValue || caseItem.status === statusValue;
      const matchesPriority = !priorityValue || caseItem.priority === priorityValue;

      return matchesSearch && matchesStatus && matchesPriority;
    });

    renderTable(filteredCases);
    updateSelectAllCheckbox();
  };

  window.clearFilters = function() {
    searchInput.value = '';
    statusFilter.value = '';
    priorityFilter.value = '';
    selectedCases.clear();
    filteredCases = [...allCases];
    renderTable(filteredCases);
    updateSelectAllCheckbox();
    showNotification('Filters cleared', 'success');
  };

  // Modal management
  window.openNewCaseModal = function() {
    editingCaseId = null;
    document.getElementById('modal-title').textContent = 'New Case';
    caseForm.reset();
    caseModal.style.display = 'flex';
  };

  window.closeCaseModal = function() {
    caseModal.style.display = 'none';
    editingCaseId = null;
  };

  window.closeConfirmModal = function() {
    confirmModal.style.display = 'none';
    confirmCallback = null;
  };

  function showConfirmModal(message, callback) {
    document.getElementById('confirm-message').textContent = message;
    confirmCallback = callback;
    confirmModal.style.display = 'flex';
  }

  window.confirmAction = function() {
    if (confirmCallback) {
      confirmCallback();
      confirmCallback = null;
    }
    closeConfirmModal();
  };

  // Case operations
  window.saveDraft = function() {
    saveCase('draft');
  };

  window.submitCase = function() {
    saveCase('pending');
  };

  function saveCase(status) {
    const formData = new FormData(caseForm);
    const caseData = {
      id: editingCaseId || generateCaseId(),
      insured: document.getElementById('case-insured').value,
      cedant: document.getElementById('case-cedant').value,
      broker: document.getElementById('case-broker').value,
      perils: document.getElementById('case-perils').value,
      tsi: parseFloat(document.getElementById('case-tsi').value) || 0,
      premium: parseFloat(document.getElementById('case-premium').value) || 0,
      share: parseFloat(document.getElementById('case-share').value) || 0,
      priority: document.getElementById('case-priority').value,
      notes: document.getElementById('case-notes').value,
      status: status,
      createdAt: editingCaseId ? 
        allCases.find(c => c.id === editingCaseId)?.createdAt : 
        new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    // Validation
    if (!caseData.insured || !caseData.cedant || !caseData.perils || !caseData.tsi || !caseData.premium) {
      showNotification('Please fill in all required fields', 'error');
      return;
    }

    const managedCases = getManagedCases();
    
    if (editingCaseId) {
      const index = managedCases.findIndex(c => c.id === editingCaseId);
      if (index !== -1) {
        managedCases[index] = caseData;
      }
      showNotification('Case updated successfully', 'success');
    } else {
      managedCases.push(caseData);
      showNotification(`Case ${status === 'draft' ? 'saved as draft' : 'submitted for review'}`, 'success');
    }

    saveManagedCases(managedCases);
    loadCases();
    closeCaseModal();
  }

  function editCase(caseId) {
    const caseData = allCases.find(c => c.id === caseId);
    if (!caseData) return;

    editingCaseId = caseId;
    document.getElementById('modal-title').textContent = 'Edit Case';
    
    // Populate form
    document.getElementById('case-insured').value = caseData.insured || '';
    document.getElementById('case-cedant').value = caseData.cedant || '';
    document.getElementById('case-broker').value = caseData.broker || '';
    document.getElementById('case-perils').value = caseData.perils || '';
    document.getElementById('case-tsi').value = caseData.tsi || '';
    document.getElementById('case-premium').value = caseData.premium || '';
    document.getElementById('case-share').value = caseData.share || '';
    document.getElementById('case-priority').value = caseData.priority || 'medium';
    document.getElementById('case-notes').value = caseData.notes || '';
    
    caseModal.style.display = 'flex';
  }

  function deleteCase(caseId) {
    showConfirmModal('Are you sure you want to delete this case? This action cannot be undone.', () => {
      const managedCases = getManagedCases();
      const updatedCases = managedCases.filter(c => c.id !== caseId);
      saveManagedCases(updatedCases);
      selectedCases.delete(caseId);
      loadCases();
      showNotification('Case deleted successfully', 'success');
    });
  }

  function approveCase(caseId) {
    updateCaseStatus(caseId, 'approved');
  }

  function rejectCase(caseId) {
    showConfirmModal('Are you sure you want to reject this case?', () => {
      updateCaseStatus(caseId, 'rejected');
    });
  }

  function updateCaseStatus(caseId, newStatus) {
    const managedCases = getManagedCases();
    const caseIndex = managedCases.findIndex(c => c.id === caseId);
    
    if (caseIndex !== -1) {
      managedCases[caseIndex].status = newStatus;
      managedCases[caseIndex].updatedAt = new Date().toISOString();
      saveManagedCases(managedCases);
      loadCases();
      showNotification(`Case ${newStatus} successfully`, 'success');
    }
  }

  // Bulk operations
  window.bulkApprove = function() {
    if (selectedCases.size === 0) {
      showNotification('Please select cases to approve', 'error');
      return;
    }

    showConfirmModal(`Are you sure you want to approve ${selectedCases.size} selected case(s)?`, () => {
      const managedCases = getManagedCases();
      let approvedCount = 0;
      
      managedCases.forEach(caseItem => {
        if (selectedCases.has(caseItem.id) && caseItem.status === 'pending') {
          caseItem.status = 'approved';
          caseItem.updatedAt = new Date().toISOString();
          approvedCount++;
        }
      });
      
      saveManagedCases(managedCases);
      selectedCases.clear();
      loadCases();
      showNotification(`${approvedCount} case(s) approved successfully`, 'success');
    });
  };

  // Data loading
  function loadCases() {
    const managedCases = getManagedCases();
    allCases = managedCases;
    filteredCases = [...allCases];
    
    updateStats(allCases);
    renderTable(filteredCases);
    updateSelectAllCheckbox();
    
    statusEl.innerHTML = `
      <div class="status-dot"></div>
      <span>Managing ${allCases.length} case(s)</span>
    `;
  }

  // Initialize with some sample data if empty
  function initializeSampleData() {
    const existingCases = getManagedCases();
    if (existingCases.length === 0) {
      const sampleCases = [
        {
          id: 'CASE-2025001',
          insured: 'ABC Manufacturing Ltd',
          cedant: 'Kenya Insurance Company',
          broker: 'Prime Brokers Ltd',
          perils: 'Fire, Explosion, Lightning',
          tsi: 50000000,
          premium: 250000,
          share: 25.0,
          priority: 'high',
          status: 'pending',
          notes: 'High-value manufacturing facility requiring urgent review',
          createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          updatedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
        },
        {
          id: 'CASE-2025002',
          insured: 'XYZ Trading Company',
          cedant: 'East Africa Insurance',
          broker: 'Global Risk Advisors',
          perils: 'Theft, Burglary, Fire',
          tsi: 15000000,
          premium: 120000,
          share: 30.0,
          priority: 'medium',
          status: 'draft',
          notes: 'Warehouse facility with good security measures',
          createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
          updatedAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString()
        },
        {
          id: 'CASE-2025003',
          insured: 'Tech Solutions Inc',
          cedant: 'Metropolitan Insurance',
          broker: 'Digital Risk Partners',
          perils: 'Fire, Equipment Breakdown, Cyber',
          tsi: 25000000,
          premium: 180000,
          share: 20.0,
          priority: 'low',
          status: 'approved',
          notes: 'Technology company with comprehensive risk management',
          createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          updatedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
        }
      ];
      
      saveManagedCases(sampleCases);
    }
  }

  // Close modals when clicking outside
  window.onclick = function(event) {
    if (event.target === caseModal) {
      closeCaseModal();
    }
    if (event.target === confirmModal) {
      closeConfirmModal();
    }
  };

  // Initialize
  initTheme();
  initializeSampleData();
  loadCases();

})();
