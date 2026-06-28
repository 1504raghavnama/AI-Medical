async function analyze() {
    const note = document.getElementById('clinical-note').value.trim();
    if (!note) {
        showError('Please enter a clinical note.');
        return;
    }

    const btn = document.getElementById('analyze-btn');
    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    hideError();
    hideResults();

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note })
        });

        if (!response.ok) throw new Error('Server error');

        const data = await response.json();
        renderResults(data);

    } catch (err) {
        showError('Failed to connect to server. Make sure the API is running.');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Analyze & Suggest Codes';
    }
}

function renderResults(data) {
    const resultsSection = document.getElementById('results-section');
    const statusBar = document.getElementById('status-bar');
    const codesContainer = document.getElementById('codes-container');

    let statusHtml = `<strong>${data.total_suggestions} code(s) suggested</strong>`;
    if (data.phi_detected && data.phi_detected.length > 0) {
        statusHtml += ` &nbsp;|&nbsp; <span class="phi-detected">🔒 PHI Removed: ${data.phi_detected.join(', ')}</span>`;
    }
    if (data.negated_entities.length > 0) {
        statusHtml += ` &nbsp;|&nbsp; <span class="negated">Negated (not coded): ${data.negated_entities.join(', ')}</span>`;
    }
    if (data.uncertain_entities.length > 0) {
        statusHtml += ` &nbsp;|&nbsp; <span class="uncertain">Uncertain: ${data.uncertain_entities.join(', ')}</span>`;
    }
    statusBar.innerHTML = statusHtml;

    codesContainer.innerHTML = '';
    data.suggested_codes.forEach(code => {
        const card = document.createElement('div');
        card.className = 'code-card';
        card.innerHTML = `
            <div class="code-header">
                <span class="code-badge">${code.primary_code}</span>
                <span class="code-description">${code.description}</span>
            </div>
            <div class="code-meta">
                Entity: <em>${code.entity}</em> &nbsp;|&nbsp;
                Confidence: <strong>${(code.confidence * 100).toFixed(1)}%</strong> &nbsp;|&nbsp;
                <span class="status-badge status-${code.status}">${code.status}</span>
            </div>
            ${code.llm_reason ? `<div class="llm-reason">🤖 ${code.llm_reason}</div>` : ''}
            <div class="alternatives">
                <div class="alternatives-title">Alternatives</div>
                ${code.alternatives.map(a =>
                    `<div class="alt-item">• ${a.code} — ${a.description} (${(a.confidence * 100).toFixed(1)}%)</div>`
                ).join('')}
            </div>
            <div class="feedback-btns">
                <button class="btn-accept" data-code="${code.primary_code}" onclick="sendFeedback('${code.primary_code}', 'accept', '${code.entity}')">✓ Accept</button>
                <button class="btn-reject" data-code="${code.primary_code}" onclick="sendFeedback('${code.primary_code}', 'reject', '${code.entity}')">✗ Reject</button>
            </div>
        `;
        codesContainer.appendChild(card);
    });

    resultsSection.classList.remove('hidden');
}

async function sendFeedback(code, action, entity) {
    const note = document.getElementById('clinical-note').value.trim();
    
    try {
        await fetch('/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note, code, action, entity })
        });

        // Disable BOTH buttons for this code after any feedback
        const allButtons = document.querySelectorAll(`button[data-code="${code}"]`);
        allButtons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.5';
        });

        // Show which action was taken
        event.target.textContent = action === 'accept' ? '✓ Accepted' : '✗ Rejected';

    } catch (err) {
        console.error('Feedback error:', err);
    }
}

function showError(msg) {
    const section = document.getElementById('error-section');
    document.getElementById('error-message').textContent = msg;
    section.classList.remove('hidden');
}

function hideError() {
    document.getElementById('error-section').classList.add('hidden');
}

function hideResults() {
    document.getElementById('results-section').classList.add('hidden');
}