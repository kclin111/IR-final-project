// Main JavaScript for Traffic Law Retrieval System

async function submitQuery() {
    const queryInput = document.getElementById('queryInput');
    const query = queryInput.value.trim();

    if (!query) {
        alert('請輸入查詢內容');
        return;
    }

    // Show loading state
    setLoading(true);
    hideError();
    hideResult();

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Query failed');
        }

        if (data.success) {
            displayResult(data);
        } else {
            showError(data.message || 'Unknown error occurred');
        }

    } catch (error) {
        console.error('Error:', error);
        showError(`查詢失敗: ${error.message}`);
    } finally {
        setLoading(false);
    }
}

function displayResult(data) {
    const resultSection = document.getElementById('resultSection');
    const answerContent = document.getElementById('answerContent');
    const processingTime = document.getElementById('processingTime');
    const retrievalInfo = document.getElementById('retrievalInfo');
    const lawCitations = document.getElementById('lawCitations');
    const caseCitations = document.getElementById('caseCitations');
    const contextPreview = document.getElementById('contextPreview');

    // Display answer
    answerContent.textContent = data.answer;

    // Display meta info
    processingTime.textContent = `⏱️ ${data.processing_time}秒`;
    retrievalInfo.textContent = `📊 檢索: ${data.retrieved_laws} 法條, ${data.retrieved_cases} 判例`;

    // Display law citations
    lawCitations.innerHTML = '';
    if (data.law_citations && data.law_citations.length > 0) {
        data.law_citations.forEach(law => {
            const li = document.createElement('li');
            li.textContent = law;
            lawCitations.appendChild(li);
        });
    } else {
        lawCitations.innerHTML = '<li style="color: #999; font-style: italic;">無法條引用</li>';
    }

    // Display case citations
    caseCitations.innerHTML = '';
    if (data.case_citations && data.case_citations.length > 0) {
        data.case_citations.forEach(caseId => {
            const li = document.createElement('li');
            li.textContent = caseId;
            caseCitations.appendChild(li);
        });
    } else {
        caseCitations.innerHTML = '<li style="color: #999; font-style: italic;">無判例引用</li>';
    }

    // Display context preview
    if (data.context_preview) {
        contextPreview.textContent = data.context_preview;
    }

    // Show result section
    resultSection.style.display = 'block';

    // Scroll to result
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function loadStats() {
    const statsDisplay = document.getElementById('statsDisplay');

    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        if (data.success) {
            const stats = data.statistics;
            statsDisplay.innerHTML = `
                <h4>系統統計資訊</h4>
                <ul style="list-style: none; padding: 10px 0;">
                    <li>📚 法條總數: <strong>${stats.total_laws}</strong></li>
                    <li>⚖️ 判例總數: <strong>${stats.total_cases}</strong></li>
                    <li>📄 判例片段總數: <strong>${stats.total_chunks}</strong></li>
                    <li>📊 平均每條法律關聯判例數: <strong>${stats.avg_cases_per_law}</strong></li>
                </ul>
            `;
            statsDisplay.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading stats:', error);
        statsDisplay.innerHTML = '<p style="color: red;">載入統計資訊失敗</p>';
        statsDisplay.style.display = 'block';
    }
}

function setLoading(isLoading) {
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const btnLoader = document.getElementById('btnLoader');

    submitBtn.disabled = isLoading;

    if (isLoading) {
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline-block';
    } else {
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
}

function showError(message) {
    const errorSection = document.getElementById('errorSection');
    const errorMessage = document.getElementById('errorMessage');

    errorMessage.textContent = message;
    errorSection.style.display = 'block';

    // Scroll to error
    errorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function hideError() {
    const errorSection = document.getElementById('errorSection');
    errorSection.style.display = 'none';
}

function hideResult() {
    const resultSection = document.getElementById('resultSection');
    resultSection.style.display = 'none';
}

// Allow Enter key to submit (with Shift+Enter for new line)
document.addEventListener('DOMContentLoaded', () => {
    const queryInput = document.getElementById('queryInput');

    queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitQuery();
        }
    });
});
