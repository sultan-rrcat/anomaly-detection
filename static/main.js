// Initialize application state
const columns = typeof window.columns !== 'undefined' ? window.columns : [];
const fileId = typeof window.fileId !== 'undefined' ? window.fileId : null;

const carousel = document.getElementById('carousel');
// const prevBtn = document.getElementById('prevBtn');
// const nextBtn = document.getElementById('nextBtn');
const runAllBtn = document.getElementById('run-all-btn');
const graphContainer = document.getElementById('graph-container');
const uploadForm = document.getElementById('upload-form');
const formFileInput = document.getElementById('form-file-input');
const columnsCount = document.getElementById('columns-count');
const reportStatus = document.getElementById('report-status');
const reportContent = document.getElementById('report-content');
const runAllMessage = document.getElementById('run-all-message');

const columnsPerPage = 15; // 3x5 grid
let startIndex = 0;
let anomalousSets = new Set();

// File upload handling
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const uploadText = document.querySelector('.upload-text');

const MAX_FILE_SIZE_MB = 200;

// DOM Elements for parameters
const methodSelect = document.getElementById("method");
const thresholdGroup = document.getElementById("threshold-group");
const kValueGroup = document.getElementById("kvalue-group");
const zscoreThresholdGroup = document.getElementById("zscore-threshold-group");
const lofThresholdGroup = document.getElementById("lof-threshold-group");
const windowGroup = document.getElementById("window-group");

// Update parameters based on selected method - FIXED VERSION
function updateParameters() {
    const method = methodSelect.value;
    console.log('Method changed to:', method); // Debug log

    // Hide all groups first
    thresholdGroup.style.display = "none";
    kValueGroup.style.display = "none";
    zscoreThresholdGroup.style.display = "none";
    lofThresholdGroup.style.display = "none";
    windowGroup.style.display = "none";

    if (method === "zscore") {
        // Show only z-score threshold
        zscoreThresholdGroup.style.display = "block";
        console.log('Showing Z-Score threshold controls');
    } 
    else if (method === "rolling_zscore") {
        // Show z-score threshold and window size
        zscoreThresholdGroup.style.display = "block";
        windowGroup.style.display = "block";
        console.log('Showing Rolling Z-Score controls');
    }
    else if (method === "knn") {
        // Show percentile + k
        thresholdGroup.style.display = "block";
        kValueGroup.style.display = "block";
        console.log('Showing KNN controls');
    } 
    else if (method === "lof"){
      // Show lof, percentile, k
      kValueGroup.style.display = "block";
      lofThresholdGroup.style.display = "block";
      thresholdGroup.style.display = "block";
      console.log('Showing only LOF controls.')
    }
    else if (method === "isolation_forest") {
        // Show only percentile
        thresholdGroup.style.display = "block";
        console.log('Showing Isolation Forest controls');
    }
    else if(method === "minmax"){
      console.log("Nothing to show for MinMax")
    }
}

// Initialize parameter handling when DOM is ready
function initializeParameterHandling() {
    if (methodSelect) {
        // Run once on load
        updateParameters();
        
        // Add event listener for changes
        methodSelect.addEventListener("change", updateParameters);
        console.log('Parameter handling initialized');
    } else {
        console.error('Method select element not found');
    }
}

uploadArea.addEventListener('click', () => fileInput.click());
uploadArea.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadArea.classList.add('drag-over');
});
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
uploadArea.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadArea.classList.remove('drag-over');
  if (e.dataTransfer.files.length > 0) {
    handleFileSelect(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files.length > 0) {
    handleFileSelect(e.target.files[0]);
  }
});

async function handleFileSelect(file) {
  if (!file) return;

  if (!file.name.toLowerCase().endsWith('.csv') && !file.name.toLowerCase().endsWith('.tdms')) {
    uploadText.textContent = 'Error: Only CSV & TDMS files are allowed';
    return;
  }

  if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
    uploadText.textContent = `Error: File exceeds ${MAX_FILE_SIZE_MB}MB`;
    return;
  }

  uploadText.textContent = 'Uploading...';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('/upload', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = `Upload failed (status ${response.status})`;
      try {
        const errData = await response.json();
        errorMessage = errData.detail || errorMessage;
      } catch {
        const errText = await response.text();
        if (errText) errorMessage = errText;
      }
      throw new Error(errorMessage);
    }

    const data = await response.json();

    // Update global state
    window.columns = data.columns || [];
    if (data.fileId) {
      window.fileId = data.fileId; // persist fileId
    }

    initialize(); // refresh grid
    uploadText.textContent = file.name;

  } catch (error) {
    console.error('Upload error:', error);
    uploadText.textContent = `Error: ${error.message}`;
  }
}

// Initialize columns count
function updateColumnsCount(cols) {
  columnsCount.textContent = `${cols.length} column${cols.length !== 1 ? 's' : ''}`;
}

// Fetch anomalies from server
async function fetchAnomalies() {
  try {
    const resp = await fetch('/change-color');
    if (!resp.ok) return 0;

    const data = await resp.json();
    anomalousSets = new Set(data.anomaly_columns || []);
    return anomalousSets.size;
  } catch (err) {
    console.warn('Could not fetch anomalies', err);
    anomalousSets = new Set();
    return 0;
  }
}

// Render column grid
/*function renderGrid(cols) {
  if (!carousel) return;

  carousel.innerHTML = '';
  const endIndex = startIndex + columnsPerPage;
  const pageColumns = cols.slice(startIndex, endIndex);

  const totalSlots = Math.min(columnsPerPage, Math.max(pageColumns.length, 15));

  for (let i = 0; i < totalSlots; i++) {
    const btn = document.createElement('button');
    btn.className = 'column-btn';

    if (i < pageColumns.length) {
      const col = pageColumns[i];
      btn.textContent = col;
      btn.title = col;
      btn.setAttribute('aria-label', `Column ${col}`);

      if (anomalousSets.has(col)) {
        btn.classList.add('anomalous');
      }

      btn.addEventListener('click', () => generateGraph(col, i));
    } else {
      btn.classList.add('placeholder');
      btn.disabled = true;
    }

    carousel.appendChild(btn);
  }

  prevBtn.disabled = startIndex === 0;
  nextBtn.disabled = endIndex >= cols.length;
}*/
// Render all columns in a single scrollable view
function renderGrid(cols) {
  if (!carousel) return;

  // Clear existing content
  carousel.innerHTML = '';

  // Loop through all columns
  cols.forEach((col, i) => {
    const btn = document.createElement('button');
    btn.className = 'column-btn';
    btn.textContent = col;
    btn.title = col;
    btn.setAttribute('aria-label', `Column ${col}`);

    if (anomalousSets.has(col)) {
      btn.classList.add('anomalous');
    }

    btn.addEventListener('click', () => generateGraph(col, i));
    carousel.appendChild(btn);
  });
}
// Generate graph for selected column
async function generateGraph(columnName, columnIndex) {
  const loadingHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <span>Generating anomaly detection graph...</span>
    </div>
  `;
  graphContainer.innerHTML = loadingHTML;

  const method = document.getElementById("method").value;
  
  let payload = {
      column_name: columnName,
      method: method
  };

  // Add parameters based on method
  const thresholdPercentile = document.getElementById('thresholdPercentile');
  const kValue = document.getElementById('kValue');
  const zscoreThreshold = document.getElementById('zscoreThreshold');
  const lofThreshold = document.getElementById('lofThreshold');
  const windowSize = document.getElementById('windowSize');

  // Only include parameters that are visible/relevant for the selected method
  if (method === "knn") {
      payload.thresholdPercentile = parseFloat(thresholdPercentile.value);
      payload.kValue = parseInt(kValue.value);
  } else if (method === "isolation_forest") {
      payload.thresholdPercentile = parseFloat(thresholdPercentile.value);
  } else if (method === "zscore") {
      payload.zScoreThreshold = parseFloat(zscoreThreshold.value);
  } else if (method === "rolling_zscore") {
      payload.zScoreThreshold = parseFloat(zscoreThreshold.value);
      payload.windowSize = parseInt(windowSize.value);
  } else if (method === "lof"){
      payload.lofThreshold = parseFloat(lofThreshold.value)
      payload.thresholdPercentile = parseFloat(thresholdPercentile.value);
      payload.kValue = parseInt(kValue.value);
  }

  console.log('Generating graph with payload:', payload); // Debug log

  try {
    const response = await fetch('/detect-graph', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (data.error) {
      graphContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-text" style="color: var(--error);">Error: ${data.error}</div>
        </div>
      `;
      return;
    }

    graphContainer.innerHTML = '';
    const fig = JSON.parse(data.graph_json);
    Plotly.newPlot(graphContainer, fig.data, fig.layout, {
      responsive: true,
      displayModeBar: false
    });

    // Update report status
    reportStatus.textContent = `${data.anomalies} anomalies detected`;
    reportStatus.style.background = data.anomalies > 0 ? '#fef2f2' : '#f0fdf4';
    reportStatus.style.color = data.anomalies > 0 ? 'var(--error)' : 'var(--success)';

  } catch (error) {
    console.error('Error generating graph:', error);
    graphContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-text" style="color: var(--error);">Failed to generate graph</div>
        <div class="empty-state-hint">${error}. Check console for details</div>
      </div>
    `;
  }
}

// Navigation handlers
/*
prevBtn.addEventListener('click', async () => {
  startIndex = Math.max(0, startIndex - columnsPerPage);
  await fetchAnomalies();
  renderGrid(window.columns || []);
});

nextBtn.addEventListener('click', async () => {
  if (startIndex + columnsPerPage < (window.columns || []).length) {
    startIndex += columnsPerPage;
    await fetchAnomalies();
    renderGrid(window.columns || []);
  }
});
*/

// Run all analysis
runAllBtn.addEventListener('click', async () => {
  try {
    runAllBtn.disabled = true;
    runAllBtn.innerHTML = `
      <div class="spinner" style="width: 12px; height: 12px;"></div>
      <span>Analyzing...</span>
    `;
    reportStatus.textContent = 'Running analysis...';

    const method = document.getElementById("method").value;
    let requestBody = { method: method };

    // Add parameters based on method
    if (method === "knn") {
      requestBody.thresholdPercentile = parseFloat(document.getElementById('thresholdPercentile').value);
      requestBody.kValue = parseInt(document.getElementById('kValue').value);
    } else if (method === "isolation_forest") {
      requestBody.thresholdPercentile = parseFloat(document.getElementById('thresholdPercentile').value);
    } else if (method === "zscore") {
      requestBody.zScoreThreshold = parseFloat(document.getElementById('zscoreThreshold').value);
    } else if (method === "rolling_zscore") {
      requestBody.zScoreThreshold = parseFloat(document.getElementById('zscoreThreshold').value);
      requestBody.windowSize = parseInt(document.getElementById('windowSize').value);
    } else if (method == "lof"){
      requestBody.lofThreshold = parseFloat(document.getElementById('lofThreshold').value);
      requestBody.thresholdPercentile = parseFloat(document.getElementById('thresholdPercentile').value);
      requestBody.kValue = parseInt(document.getElementById('kValue').value);
    }

    console.log('Running analysis with:', requestBody); // Debug log

    const resp = await fetch('/run-all', {
      method: "POST",
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    if (!resp.ok) {
      throw new Error(`Analysis failed with status ${resp.status}`);
    }

    const result = await resp.json();
    const anomalies = result.anomaly_columns || [];

    // Update global anomaly set
    anomalousSets = new Set(anomalies.map(a => a.column));

    // Re-render grid with anomaly highlights
    renderGrid(window.columns || []);

    // Update report
    const totalAnomalies = anomalies.reduce((sum, a) => sum + a.count, 0);

    let reportText = '';
    if (method === "zscore") {
      reportText = `Analysis completed with Z-score threshold ${document.getElementById('zscoreThreshold').value}.`;
    } else if (method === "rolling_zscore") {
      reportText = `Analysis completed with Rolling Z-score threshold ${document.getElementById('zscoreThreshold').value} and window size ${document.getElementById('windowSize').value}.`;
    } else if (method === "knn") {
      reportText = `Analysis completed with KNN threshold ${document.getElementById('thresholdPercentile').value}% and k=${document.getElementById('kValue').value}.`;
    } else if (method === "lof") {
      reportText = `Analysis completed with LOF threshold ${document.getElementById('lofThreshold').value}. Percentile Threshold ${document.getElementById('thresholdPercentile').value}% and k=${document.getElementById('kValue').value}.`;
    } else if (method === "isolation_forest") {
      reportText = `Analysis completed with Isolation Forest threshold ${document.getElementById('thresholdPercentile').value}%.`;
    }

    reportContent.innerHTML = `
      <div>
        ${reportText}
        Found ${totalAnomalies} total anomalies across ${anomalies.length} columns.
      </div>
    `;

    reportStatus.textContent = `${anomalies.length} anomalous columns found`;
    reportStatus.style.background = anomalies.length > 0 ? '#fef2f2' : '#f0fdf4';
    reportStatus.style.color = anomalies.length > 0 ? 'var(--error)' : 'var(--success)';

    if (anomalies.length > 0) {
      reportContent.innerHTML += `
        <ul class="anomaly-list">
          ${anomalies.map(a => `<li class="anomaly-item">${a.column} (${a.count})</li>`).join('')}
        </ul>
      `;
    }

    runAllMessage.innerHTML = '<div class="message success">Analysis completed successfully!</div>';
    setTimeout(() => runAllMessage.innerHTML = '', 3000);

  } catch (err) {
    console.error(err);
    reportStatus.textContent = 'Analysis failed';
    reportStatus.style.background = '#fef2f2';
    reportStatus.style.color = 'var(--error)';
    runAllMessage.innerHTML = '<div class="message error">Analysis failed. Please try again.</div>';
  } finally {
    runAllBtn.disabled = false;
    runAllBtn.innerHTML = `
      <span class="icon">🔍</span>
      Generate Report
    `;
  }
});

// Initialize application
async function initialize() {
  const cols = Array.isArray(window.columns) ? window.columns : [];
  updateColumnsCount(cols);
  await fetchAnomalies();
  renderGrid(cols);
}

// Wait for DOM to be fully loaded before initializing
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    initializeParameterHandling();
    initialize();
});

// If DOM is already loaded (in case script runs after DOMContentLoaded)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        console.log('DOM loaded (deferred), initializing...');
        initializeParameterHandling();
        initialize();
    });
} else {
    console.log('DOM already loaded, initializing immediately...');
    initializeParameterHandling();
    initialize();
}