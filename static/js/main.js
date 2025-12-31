// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    // Set username display if available
    const usernameDisplay = document.getElementById('username-display');
    if (usernameDisplay) {
        // Username will be set from server-side template or API
        fetch('/api/user-info', {
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) {
                    // If not authenticated, username should come from template
                    return null;
                }
                return response.json();
            })
            .then(data => {
                if (data && data.username) {
                    usernameDisplay.textContent = data.username;
                }
            })
            .catch(() => {
                // Fallback if API not available - username should come from template
            });
    }

    // Load defaults on page load
    loadDefaults();

    // Setup save config form handler
    const saveConfigForm = document.getElementById('saveConfigForm');
    if (saveConfigForm) {
        saveConfigForm.addEventListener('submit', handleSaveConfig);
    }

    // Setup type change handler
    const setupTypeSelect = document.getElementById('OPENWRAP_SETUP_TYPE');
    if (setupTypeSelect) {
        setupTypeSelect.addEventListener('change', handleSetupTypeChange);
        handleSetupTypeChange(); // Initial call
    }

    // Partner type change handler
    const partnerTypeSelect = document.getElementById('partner_type');
    if (partnerTypeSelect) {
        partnerTypeSelect.addEventListener('change', handlePartnerTypeChange);
        handlePartnerTypeChange(); // Initial call
    }

    // Deal lineitem checkbox handler
    const dealLineitemCheckbox = document.getElementById('ENABLE_DEAL_LINEITEM');
    if (dealLineitemCheckbox) {
        dealLineitemCheckbox.addEventListener('change', handleDealLineitemChange);
    }

    // Deal config type handler
    const dealConfigTypeSelect = document.getElementById('DEAL_CONFIG_TYPE');
    if (dealConfigTypeSelect) {
        dealConfigTypeSelect.addEventListener('change', handleDealConfigTypeChange);
    }

    // File upload handlers
    const keyJsonInput = document.getElementById('key-json-upload');
    if (keyJsonInput) {
        keyJsonInput.addEventListener('change', handleKeyJsonUpload);
    }

    // CSV file upload handler
    const csvFileInput = document.getElementById('csv-file-input');
    if (csvFileInput) {
        csvFileInput.addEventListener('change', handleCSVUpload);
    }

    // CSV file selector handler
    const csvFileSelector = document.getElementById('csv-file-selector');
    if (csvFileSelector) {
        csvFileSelector.addEventListener('change', function () {
            const filename = this.value;
            if (filename) {
                document.getElementById('OPENWRAP_BUCKET_CSV').value = filename;
                loadCSVToTable(filename);
            }
        });
    }

    // Form submission handler
    const form = document.getElementById('lineItemForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }

    // Load CSV files list on page load
    loadCSVFiles();

    // Add initial size input
    addSize();
});

// File upload handlers
function handleKeyJsonUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/upload-key-json', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.client_email) {
                const preview = document.getElementById('key-json-preview');
                preview.innerHTML = `<div class="file-preview-success">
                <strong>✓ File uploaded:</strong> ${data.filename}<br>
                <strong>Service Account:</strong> ${data.client_email}
            </div>`;
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error uploading file');
        });
}

function handleSetupTypeChange() {
    const setupType = document.getElementById('OPENWRAP_SETUP_TYPE').value;

    // Show/hide fields based on setup type
    const creativeTemplateGroup = document.getElementById('creative-template-group');
    const nativeVarGroup = document.getElementById('native-var-group');
    const videoLengthsGroup = document.getElementById('video-lengths-group');
    const adpodSlotsGroup = document.getElementById('adpod-slots-group');
    const videoPositionGroup = document.getElementById('video-position-group');
    const dealLineitemGroup = document.getElementById('deal-lineitem-group');
    const adpodCacheUrlGroup = document.getElementById('adpod-cache-url-group');
    const bidderCodeGroup = document.getElementById('bidder-code-group');
    const use1x1Checkbox = document.getElementById('OPENWRAP_USE_1x1_CREATIVE');
    const customSetupTypeGroup = document.getElementById('custom-setup-type-group');
    const customSetupTypeInput = document.getElementById('OPENWRAP_CUSTOM_SETUP_TYPE');

    // Handle custom setup type
    if (setupType === 'CUSTOM') {
        customSetupTypeGroup.style.display = 'block';
        if (customSetupTypeInput) {
            customSetupTypeInput.required = true;
        }
    } else {
        customSetupTypeGroup.style.display = 'none';
        if (customSetupTypeInput) {
            customSetupTypeInput.required = false;
            customSetupTypeInput.value = '';
        }
    }

    // Creative template (required for NATIVE and IN_APP_NATIVE)
    if (setupType === 'NATIVE' || setupType === 'IN_APP_NATIVE') {
        if (creativeTemplateGroup) {
            creativeTemplateGroup.style.display = 'block';
            const input = creativeTemplateGroup.querySelector('input');
            if (input) input.required = true;
        }
    } else {
        if (creativeTemplateGroup) {
            creativeTemplateGroup.style.display = 'none';
            const input = creativeTemplateGroup.querySelector('input');
            if (input) input.required = false;
        }
    }

    // Native var (for NATIVE and IN_APP_NATIVE)
    if (setupType === 'NATIVE' || setupType === 'IN_APP_NATIVE') {
        if (nativeVarGroup) nativeVarGroup.style.display = 'block';
    } else {
        if (nativeVarGroup) nativeVarGroup.style.display = 'none';
    }

    // Video lengths and ADPOD slots (required for ADPOD)
    if (setupType === 'ADPOD') {
        if (videoLengthsGroup) {
            videoLengthsGroup.style.display = 'block';
            const input = videoLengthsGroup.querySelector('input');
            if (input) input.required = true;
        }
        if (adpodSlotsGroup) {
            adpodSlotsGroup.style.display = 'block';
            const input = adpodSlotsGroup.querySelector('input');
            if (input) input.required = true;
        }
        if (dealLineitemGroup) dealLineitemGroup.style.display = 'block';
        if (adpodCacheUrlGroup) adpodCacheUrlGroup.style.display = 'block';
    } else {
        if (videoLengthsGroup) {
            videoLengthsGroup.style.display = 'none';
            const input = videoLengthsGroup.querySelector('input');
            if (input) input.required = false;
        }
        if (adpodSlotsGroup) {
            adpodSlotsGroup.style.display = 'none';
            const input = adpodSlotsGroup.querySelector('input');
            if (input) input.required = false;
        }
        if (dealLineitemGroup) dealLineitemGroup.style.display = 'none';
        if (adpodCacheUrlGroup) adpodCacheUrlGroup.style.display = 'none';
    }

    // Video position (for VIDEO and ADPOD)
    if (setupType === 'VIDEO' || setupType === 'ADPOD') {
        if (videoPositionGroup) videoPositionGroup.style.display = 'block';
    } else {
        if (videoPositionGroup) videoPositionGroup.style.display = 'none';
    }

    // Hide bidder code for certain types
    if (bidderCodeGroup) {
        if (setupType === 'JWPLAYER' || setupType === 'IN_APP' ||
            setupType === 'IN_APP_VIDEO' || setupType === 'IN_APP_NATIVE') {
            bidderCodeGroup.style.display = 'none';
        } else {
            bidderCodeGroup.style.display = 'block';
        }
    }

    // Disable 1x1 creative for NATIVE and ADPOD
    if (use1x1Checkbox) {
        if (setupType === 'NATIVE' || setupType === 'IN_APP_NATIVE' || setupType === 'ADPOD') {
            use1x1Checkbox.disabled = true;
            use1x1Checkbox.checked = false;
        } else {
            use1x1Checkbox.disabled = false;
        }
    }
}

function handlePartnerTypeChange() {
    const partnerType = document.getElementById('partner_type').value;
    const section4 = document.getElementById('section-4');
    const prebidPriceBucketsGroup = document.getElementById('prebid-price-buckets-group');
    const bidderCodeGroup = document.getElementById('bidder-code-group');

    if (partnerType === 'prebid') {
        if (section4) section4.style.display = 'none';
        if (prebidPriceBucketsGroup) prebidPriceBucketsGroup.style.display = 'block';
        if (bidderCodeGroup) bidderCodeGroup.style.display = 'block';
    } else {
        if (section4) section4.style.display = 'block';
        if (prebidPriceBucketsGroup) prebidPriceBucketsGroup.style.display = 'none';
        if (bidderCodeGroup) bidderCodeGroup.style.display = 'none';
    }
}

function handleDealLineitemChange() {
    const enabled = document.getElementById('ENABLE_DEAL_LINEITEM').checked;
    const dealConfigTypeGroup = document.getElementById('deal-config-type-group');
    const dealConfigGroup = document.getElementById('deal-config-group');

    if (enabled) {
        if (dealConfigTypeGroup) dealConfigTypeGroup.style.display = 'block';
        if (dealConfigGroup) dealConfigGroup.style.display = 'block';
    } else {
        if (dealConfigTypeGroup) dealConfigTypeGroup.style.display = 'none';
        if (dealConfigGroup) dealConfigGroup.style.display = 'none';
    }
}

function handleDealConfigTypeChange() {
    const dealConfigType = document.getElementById('DEAL_CONFIG_TYPE').value;
    const dealConfigTextarea = document.getElementById('DEAL_CONFIG');

    if (dealConfigTextarea) {
        if (dealConfigType === 'DEALID') {
            dealConfigTextarea.placeholder = '{"pubmatic":{"price":10,"dealids":["PubDeal1","PubDeal2"]}}';
        } else if (dealConfigType === 'DEALTIER') {
            dealConfigTextarea.placeholder = '{"pubmatic":{"price":10,"prefix":["abc","def"],"dealpriority":[5,10]}}';
        }
    }
}

function handleCSVUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/upload-csv', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(data => {
            if (data.filename && data.data) {
                document.getElementById('OPENWRAP_BUCKET_CSV').value = data.filename;
                // Update selector
                loadCSVFiles().then(() => {
                    document.getElementById('csv-file-selector').value = data.filename;
                    // Load CSV data into table
                    populateCSVTable(data.data);
                });
            } else {
                alert('Error uploading file: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error uploading file');
        });
}

// CSV Management Functions
function loadCSVFiles() {
    return fetch('/api/list-csv-files')
        .then(response => response.json())
        .then(data => {
            const selector = document.getElementById('csv-file-selector');
            if (selector && data.files) {
                selector.innerHTML = '<option value="">Select a CSV file...</option>';
                data.files.forEach(file => {
                    const option = document.createElement('option');
                    option.value = file.filename;
                    option.textContent = file.filename + ' (' + formatFileSize(file.size) + ')';
                    selector.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error loading CSV files:', error);
        });
}

function loadCSVToTable(filename) {
    fetch('/api/parse-csv', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ filename: filename })
    })
        .then(response => response.json())
        .then(data => {
            if (data.data) {
                populateCSVTable(data.data);
            } else {
                alert('Error loading CSV: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error loading CSV:', error);
            alert('Error loading CSV file');
        });
}

function populateCSVTable(csvData) {
    const tbody = document.getElementById('csv-table-body');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (csvData && csvData.length > 0) {
        csvData.forEach((row, index) => {
            addCSVRowToTable(row, index);
        });
    } else {
        // Add one empty row if no data
        addCSVRowToTable({ start_range: '', end_range: '', granularity: '', rate_id: '' }, 0);
    }
}

function addCSVRow() {
    const tbody = document.getElementById('csv-table-body');
    if (!tbody) return;

    const rowCount = tbody.children.length;
    addCSVRowToTable({ start_range: '', end_range: '', granularity: '', rate_id: '' }, rowCount);
}

function addCSVRowToTable(rowData, index) {
    const tbody = document.getElementById('csv-table-body');
    if (!tbody) return;

    const tr = document.createElement('tr');
    tr.className = 'csv-row';
    tr.innerHTML = `
        <td><input type="number" class="csv-cell" data-field="start_range" value="${rowData.start_range || ''}" step="0.01" min="0"></td>
        <td><input type="number" class="csv-cell" data-field="end_range" value="${rowData.end_range || ''}" step="0.01" min="0"></td>
        <td><input type="number" class="csv-cell" data-field="granularity" value="${rowData.granularity || ''}" step="0.01"></td>
        <td><input type="number" class="csv-cell" data-field="rate_id" value="${rowData.rate_id || ''}" min="1" max="2"></td>
        <td>
            <button type="button" class="btn-remove" onclick="removeCSVRow(this)">Remove</button>
        </td>
    `;
    tbody.appendChild(tr);
}

function removeCSVRow(button) {
    const tbody = document.getElementById('csv-table-body');
    if (!tbody) return;

    if (tbody.children.length > 1) {
        button.closest('tr').remove();
    } else {
        alert('At least one row is required');
    }
}

function saveCSVTable() {
    const tbody = document.getElementById('csv-table-body');
    if (!tbody) return;

    const csvData = [];
    const rows = tbody.querySelectorAll('tr');

    rows.forEach(row => {
        const cells = row.querySelectorAll('.csv-cell');
        if (cells.length >= 4) {
            const rowData = {
                start_range: cells[0].value.trim(),
                end_range: cells[1].value.trim(),
                granularity: cells[2].value.trim(),
                rate_id: cells[3].value.trim()
            };

            // Validate row
            if (validateCSVRow(rowData)) {
                csvData.push(rowData);
            }
        }
    });

    if (csvData.length === 0) {
        alert('No valid rows to save. Please add at least one row with valid data.');
        return;
    }

    const filename = document.getElementById('OPENWRAP_BUCKET_CSV').value || 'LineItem.csv';

    fetch('/api/save-csv', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            filename: filename,
            data: csvData
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                alert('CSV file saved successfully!');
            } else {
                alert('Error saving CSV: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error saving CSV:', error);
            alert('Error saving CSV file');
        });
}

function validateCSVRow(row) {
    // Check if at least start_range and end_range are provided
    if (!row.start_range || !row.end_range) {
        return false;
    }

    const startRange = parseFloat(row.start_range);
    const endRange = parseFloat(row.end_range);

    // Validate ranges
    if (isNaN(startRange) || isNaN(endRange) || startRange < 0 || endRange < 0) {
        return false;
    }

    if (startRange >= endRange) {
        return false;
    }

    // Granularity can be -1 or a positive number
    if (row.granularity && row.granularity !== '-1') {
        const granularity = parseFloat(row.granularity);
        if (isNaN(granularity) || granularity <= 0) {
            return false;
        }
    }

    // Rate ID should be 1 or 2
    if (row.rate_id) {
        const rateId = parseInt(row.rate_id);
        if (rateId !== 1 && rateId !== 2) {
            return false;
        }
    }

    return true;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Size management functions
function addSize() {
    const container = document.getElementById('sizes-container');
    if (!container) return;

    const sizeInput = document.createElement('div');
    sizeInput.className = 'size-input';
    sizeInput.innerHTML = `
        <input type="number" placeholder="Width" class="size-width" min="1" required>
        <span>x</span>
        <input type="number" placeholder="Height" class="size-height" min="1" required>
        <button type="button" class="btn-remove" onclick="removeSize(this)">Remove</button>
    `;
    container.appendChild(sizeInput);
}

function removeSize(button) {
    const container = document.getElementById('sizes-container');
    if (!container) return;

    if (container.children.length > 1) {
        button.parentElement.remove();
    } else {
        alert('At least one size is required');
    }
}

function loadDefaults() {
    fetch('/api/settings/defaults')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Error loading defaults:', data.error);
                return;
            }

            // Populate form fields
            Object.keys(data).forEach(key => {
                const element = document.getElementById(key);
                if (element) {
                    if (element.type === 'checkbox') {
                        element.checked = data[key] || false;
                    } else if (key === 'DFP_NETWORK_CODE') {
                        // Handle network code - try to extract from googleads.yaml if available
                        if (!data[key] && data.googleads_network_code) {
                            element.value = data.googleads_network_code;
                        } else {
                            element.value = data[key] || '';
                        }
                    } else if (key === 'DFP_PLACEMENT_SIZES') {
                        // Handle sizes array
                        const container = document.getElementById('sizes-container');
                        if (container) {
                            container.innerHTML = '';
                            if (data[key] && data[key].length > 0) {
                                data[key].forEach(size => {
                                    const sizeInput = document.createElement('div');
                                    sizeInput.className = 'size-input';
                                    sizeInput.innerHTML = `
                                        <input type="number" placeholder="Width" class="size-width" 
                                               value="${size.width}" min="1" required>
                                        <span>x</span>
                                        <input type="number" placeholder="Height" class="size-height" 
                                               value="${size.height}" min="1" required>
                                        <button type="button" class="btn-remove" onclick="removeSize(this)">Remove</button>
                                    `;
                                    container.appendChild(sizeInput);
                                });
                            } else {
                                addSize();
                            }
                        }
                    } else if (key === 'OPENWRAP_BUCKET_CSV') {
                        element.value = data[key] || 'LineItem.csv';
                        // Load CSV if file exists
                        if (data[key]) {
                            loadCSVToTable(data[key]);
                        }
                    } else if (Array.isArray(data[key])) {
                        element.value = data[key].join(',');
                    } else if (typeof data[key] === 'object' && data[key] !== null) {
                        // Handle objects like PREBID_PRICE_BUCKETS
                        if (key === 'PREBID_PRICE_BUCKETS') {
                            const precisionEl = document.getElementById('pb_precision');
                            const minEl = document.getElementById('pb_min');
                            const maxEl = document.getElementById('pb_max');
                            const incrementEl = document.getElementById('pb_increment');
                            if (precisionEl) precisionEl.value = data[key].precision || 2;
                            if (minEl) minEl.value = data[key].min || 8;
                            if (maxEl) maxEl.value = data[key].max || 20;
                            if (incrementEl) incrementEl.value = data[key].increment || 0.50;
                        }
                    } else {
                        element.value = data[key] || '';
                    }
                }
            });

            // Trigger change handlers
            handleSetupTypeChange();
            handlePartnerTypeChange();
        })
        .catch(error => {
            console.error('Error loading defaults:', error);
        });
}

function validateForm(silent = false) {
    const form = document.getElementById('lineItemForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return false;
    }

    // Validate sizes
    const sizes = [];
    document.querySelectorAll('.size-input').forEach(sizeInput => {
        const widthInput = sizeInput.querySelector('.size-width');
        const heightInput = sizeInput.querySelector('.size-height');
        const width = widthInput ? widthInput.value.trim() : '';
        const height = heightInput ? heightInput.value.trim() : '';
        if (width && height) {
            sizes.push({ width: width, height: height });
        }
    });

    if (sizes.length === 0) {
        alert('At least one placement size (width x height) is required.');
        return false;
    }

    // Validate custom setup type
    const setupType = document.getElementById('OPENWRAP_SETUP_TYPE').value;
    if (setupType === 'CUSTOM') {
        const customSetupType = document.getElementById('OPENWRAP_CUSTOM_SETUP_TYPE').value.trim();
        if (!customSetupType) {
            alert('Custom Setup Type is required when "Custom" is selected.');
            return false;
        }
    }

    // Additional custom validation
    if (setupType === 'ADPOD') {
        const videoLengths = document.getElementById('VIDEO_LENGTHS').value.trim();
        const adpodSlots = document.getElementById('ADPOD_SLOTS').value.trim();

        if (!videoLengths) {
            alert('Video Lengths is required for ADPOD setup type');
            return false;
        }

        if (!adpodSlots) {
            alert('ADPOD Slots is required for ADPOD setup type');
            return false;
        }
    }

    if (setupType === 'NATIVE' || setupType === 'IN_APP_NATIVE') {
        const creativeTemplate = document.getElementById('OPENWRAP_CREATIVE_TEMPLATE').value.trim();
        if (!creativeTemplate) {
            alert('Creative Template is required for NATIVE setup type');
            return false;
        }
    }

    if (!silent) {
        alert('Validation Successful! All fields are correctly formatted.');
    }
    return true;
}

function handleFormSubmit(event) {
    event.preventDefault();

    if (!validateForm(true)) {
        return;
    }

    // Collect form data
    const formData = collectFormData();

    // Include client_name in form data
    const clientNameInput = document.getElementById('client_name');
    if (clientNameInput) {
        formData.client_name = clientNameInput.value || '';
    }

    // Show loading state
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="loading"></span> Generating...';

    // Show result container
    const resultContainer = document.getElementById('result-container');
    const progressContainer = document.getElementById('progress-container');
    const resultMessage = document.getElementById('result-message');
    const resultOutput = document.getElementById('result-output');

    resultContainer.style.display = 'block';
    progressContainer.style.display = 'block';
    resultMessage.textContent = '';
    resultOutput.textContent = '';

    // Reset progress bar
    updateProgressBar(0, 'Initializing...', 'starting', 0, 0);
    console.log('Progress bar initialized, starting request...');

    // Send request
    console.log('Sending request to /api/generate with data:', formData);
    fetch('/api/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        body: JSON.stringify(formData),
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                return response.text().then(text => {
                    throw new Error(`HTTP error! status: ${response.status}, message: ${text.substring(0, 100)}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.job_id) {
                // Start polling for progress
                pollProgress(data.job_id);
            } else {
                // Fallback to old behavior if no job_id
                submitButton.disabled = false;
                submitButton.textContent = originalText;

                if (data.success) {
                    resultMessage.className = 'success';
                    resultMessage.textContent = '✓ ' + (data.message || 'Line items created successfully!');
                } else {
                    resultMessage.className = 'error';
                    resultMessage.textContent = '✗ ' + (data.error || 'Failed to create line items');
                }
                resultOutput.textContent = data.output || data.error || '';
                progressContainer.style.display = 'none';
            }

            // Scroll to result
            resultContainer.scrollIntoView({ behavior: 'smooth' });
        })
        .catch(error => {
            submitButton.disabled = false;
            submitButton.textContent = originalText;
            progressContainer.style.display = 'none';

            resultMessage.className = 'error';
            resultMessage.textContent = '✗ Error: ' + error.message;

            let errorText = error.stack || error.toString();
            if (error.message.includes('Failed to fetch')) {
                errorText = 'Unable to connect to server. Please ensure the Flask app is running.\n\n' +
                    'To start the server, run: python3 app.py\n\n' +
                    'Error details: ' + error.message;
            }
            resultOutput.textContent = errorText;

            resultContainer.scrollIntoView({ behavior: 'smooth' });

            console.error('Form submission error:', error);
        });
}

function collectFormData() {
    const data = {};

    // Partner type
    data.partner_type = document.getElementById('partner_type').value;

    // Collect all inputs
    const form = document.getElementById('lineItemForm');
    form.querySelectorAll('input, select, textarea').forEach(element => {
        if (element.name && element.name !== '') {
            if (element.type === 'checkbox') {
                data[element.name] = element.checked;
            } else if (element.type === 'number') {
                data[element.name] = element.value ? parseFloat(element.value) : null;
            } else {
                data[element.name] = element.value;
            }
        }
    });

    // Handle custom setup type
    const setupType = document.getElementById('OPENWRAP_SETUP_TYPE').value;
    if (setupType === 'CUSTOM') {
        const customSetupType = document.getElementById('OPENWRAP_CUSTOM_SETUP_TYPE').value;
        data.OPENWRAP_CUSTOM_SETUP_TYPE = customSetupType;
    }

    // Collect sizes
    const sizes = [];
    document.querySelectorAll('.size-input').forEach(sizeInput => {
        const widthInput = sizeInput.querySelector('.size-width');
        const heightInput = sizeInput.querySelector('.size-height');
        const width = widthInput ? widthInput.value.trim() : '';
        const height = heightInput ? heightInput.value.trim() : '';
        if (width && height) {
            sizes.push({ width: width, height: height });
        }
    });

    // Ensure at least one size is provided
    if (sizes.length === 0) {
        console.warn('No sizes provided, adding default size');
        sizes.push({ width: '320', height: '480' });
    }

    data.DFP_PLACEMENT_SIZES = sizes;

    // Collect Prebid price buckets
    if (data.partner_type === 'prebid') {
        data.PREBID_PRICE_BUCKETS = {
            precision: parseInt(document.getElementById('pb_precision').value) || 2,
            min: parseFloat(document.getElementById('pb_min').value) || 8,
            max: parseFloat(document.getElementById('pb_max').value) || 20,
            increment: parseFloat(document.getElementById('pb_increment').value) || 0.50
        };
    }

    // Handle placements (comma-separated string to array)
    if (data.DFP_TARGETED_PLACEMENT_NAMES) {
        data.DFP_TARGETED_PLACEMENT_NAMES = data.DFP_TARGETED_PLACEMENT_NAMES
            .split(',')
            .map(p => p.trim())
            .filter(p => p);
    }

    // Handle GEO targeting (comma-separated string to array)
    if (data.DFP_TARGETED_GEO) {
        data.DFP_TARGETED_GEO = data.DFP_TARGETED_GEO
            .split(',')
            .map(g => g.trim())
            .filter(g => g);
    }

    return data;
}

// Config Save/Load Functions
function showSaveConfigModal() {
    const modal = document.getElementById('saveConfigModal');
    const clientNameInput = document.getElementById('save_client_name');
    const formClientName = document.getElementById('client_name');

    // Pre-fill client name from form
    if (formClientName && formClientName.value) {
        clientNameInput.value = formClientName.value;
    }

    modal.style.display = 'block';
}

function closeSaveConfigModal() {
    document.getElementById('saveConfigModal').style.display = 'none';
    document.getElementById('saveConfigForm').reset();
}

function handleSaveConfig(event) {
    event.preventDefault();

    const configName = document.getElementById('save_config_name').value;
    const clientName = document.getElementById('save_client_name').value;
    const formData = collectFormData();

    if (!configName) {
        alert('Please enter a configuration name');
        return;
    }

    fetch('/api/save-config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            config_name: configName,
            client_name: clientName,
            config_data: formData
        })
    })
        .then(response => {
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                return response.text().then(text => {
                    throw new Error(`HTTP ${response.status}: ${text.substring(0, 100)}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (data && data.success) {
                alert('Configuration saved successfully!');
                closeSaveConfigModal();
            } else {
                alert('Error: ' + (data?.error || 'Failed to save configuration'));
            }
        })
        .catch(error => {
            alert('Error saving configuration: ' + error.message);
        });
}

function showLoadConfigModal() {
    const modal = document.getElementById('loadConfigModal');
    const container = document.getElementById('configListContainer');

    modal.style.display = 'block';
    container.innerHTML = '<p>Loading configurations...</p>';

    fetch('/api/saved-configs', {
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                return response.text().then(text => {
                    throw new Error(`HTTP ${response.status}: ${text.substring(0, 100)}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (!data) return;
            if (data.error) {
                container.innerHTML = '<p class="error">Error: ' + data.error + '</p>';
                return;
            }

            if (data.configs.length === 0) {
                container.innerHTML = '<p>No saved configurations found.</p>';
                return;
            }

            let html = '<div class="config-list">';
            data.configs.forEach(config => {
                const createdDate = new Date(config.created_at).toLocaleDateString();
                html += `
                    <div class="config-item">
                        <div class="config-item-info">
                            <div class="config-item-name">${escapeHtml(config.config_name)}</div>
                            <div class="config-item-meta">
                                ${config.client_name ? 'Client: ' + escapeHtml(config.client_name) + ' • ' : ''}
                                Saved: ${createdDate}
                            </div>
                        </div>
                        <div class="config-item-actions">
                            <button class="btn-primary btn-small" onclick="loadConfig(${config.id})">Load</button>
                            <button class="btn-secondary btn-small" onclick="deleteConfig(${config.id})">Delete</button>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        })
        .catch(error => {
            container.innerHTML = '<p class="error">Error loading configurations: ' + error.message + '</p>';
        });
}

function closeLoadConfigModal() {
    document.getElementById('loadConfigModal').style.display = 'none';
}

function loadConfig(configId) {
    fetch(`/api/load-config/${configId}`, {
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                return response.text().then(text => {
                    throw new Error(`HTTP ${response.status}: ${text.substring(0, 100)}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (!data) return;
            if (data.error) {
                alert('Error: ' + data.error);
                return;
            }

            if (data.config) {
                // Populate all form fields with loaded config
                populateFormFromData(data.config);
                closeLoadConfigModal();
                alert('Configuration loaded successfully!');
            }
        })
        .catch(error => {
            alert('Error loading configuration: ' + error.message);
        });
}

function deleteConfig(configId) {
    if (!confirm('Are you sure you want to delete this configuration?')) {
        return;
    }

    fetch(`/api/delete-config/${configId}`, {
        method: 'DELETE',
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    window.location.href = '/login';
                    return;
                }
                return response.text().then(text => {
                    throw new Error(`HTTP ${response.status}: ${text.substring(0, 100)}`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (!data) return;
            if (data.success) {
                // Refresh config list
                showLoadConfigModal();
            } else {
                alert('Error: ' + (data.error || 'Failed to delete configuration'));
            }
        })
        .catch(error => {
            alert('Error deleting configuration: ' + error.message);
        });
}

function populateFormFromData(configData) {
    // Populate all form fields from config data
    Object.keys(configData).forEach(key => {
        const element = document.getElementById(key) || document.querySelector(`[name="${key}"]`);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = configData[key] === true || configData[key] === 'true';
            } else if (element.tagName === 'SELECT') {
                element.value = configData[key] || '';
            } else {
                element.value = configData[key] || '';
            }
        }
    });

    // Handle special cases like placement sizes
    if (configData.DFP_PLACEMENT_SIZES && Array.isArray(configData.DFP_PLACEMENT_SIZES)) {
        // This would need to be handled by the placement sizes UI
        // For now, we'll just log it
        console.log('Placement sizes:', configData.DFP_PLACEMENT_SIZES);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Progress polling function
function pollProgress(jobId) {
    console.log('Starting progress polling for job:', jobId);
    // Poll every 1 second
    const progressInterval = setInterval(() => {
        fetch(`/api/progress/${jobId}`, {
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401 || response.status === 403) {
                        clearInterval(progressInterval);
                        window.location.href = '/login';
                        return null;
                    }
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (!data) return;

                const status = data.status || 'processing';
                const progress = data.progress || 0;
                const message = data.message || 'Processing...';
                const currentBatch = data.current_batch || 0;
                const totalBatches = data.total_batches || 0;

                console.log('Progress update:', { status: data.status, progress, message, currentBatch, totalBatches });

                // Update progress bar
                updateProgressBar(progress, message, data.status, currentBatch, totalBatches);

                // Update output if available
                if (data.output) {
                    const resultOutput = document.getElementById('result-output');
                    if (resultOutput) {
                        resultOutput.textContent = data.output;
                    }
                }

                // Stop polling if completed or failed
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(progressInterval);

                    const submitButton = document.querySelector('button[type="submit"]');
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.textContent = 'Generate Line Items';
                    }

                    const resultMessage = document.getElementById('result-message');
                    if (resultMessage) {
                        if (data.status === 'completed') {
                            resultMessage.className = 'success';
                            resultMessage.textContent = '✓ ' + (message || 'Line items created successfully!');
                        } else {
                            resultMessage.className = 'error';
                            resultMessage.textContent = '✗ ' + (message || 'Failed to create line items');
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error polling progress:', error);
                clearInterval(progressInterval);

                const submitButton = document.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = 'Generate Line Items';
                }

                const resultMessage = document.getElementById('result-message');
                if (resultMessage) {
                    resultMessage.className = 'error';
                    resultMessage.textContent = '✗ Error: Failed to get progress updates';
                }
            });
    }, 1000); // Poll every second
}

// Update progress bar UI
function updateProgressBar(progress, message, status, currentBatch, totalBatches) {
    const progressBarFill = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');
    const progressStatus = document.getElementById('progress-status');

    console.log('Updating progress bar:', { progressBarFill: !!progressBarFill, progressPercentage: !!progressPercentage, progressStatus: !!progressStatus, progress, message });

    if (progressBarFill) {
        const width = Math.min(100, Math.max(0, progress));
        progressBarFill.style.width = width + '%';
        console.log('Set progress bar width to:', width + '%');
    } else {
        console.error('progress-bar element not found!');
    }

    if (progressPercentage) {
        progressPercentage.textContent = Math.round(progress) + '%';
    } else {
        console.error('progress-percentage element not found!');
    }

    if (progressStatus) {
        let statusText = message || 'Processing...';
        if (totalBatches > 1 && currentBatch > 0) {
            statusText += ` (Batch ${currentBatch}/${totalBatches})`;
        }
        progressStatus.textContent = statusText;
    } else {
        console.error('progress-status element not found!');
    }
}

// Close modals when clicking outside
window.onclick = function (event) {
    const saveModal = document.getElementById('saveConfigModal');
    const loadModal = document.getElementById('loadConfigModal');
    if (event.target === saveModal) {
        closeSaveConfigModal();
    }
    if (event.target === loadModal) {
        closeLoadConfigModal();
    }
}
