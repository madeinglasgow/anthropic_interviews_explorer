let allTranscripts = [];
let filteredTranscripts = [];
let currentIndex = 0;

const chatContainer = document.getElementById('chat-container');
const metadata = document.getElementById('metadata');
const navInfo = document.getElementById('nav-info');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const splitFilter = document.getElementById('split-filter');
const chatNumberInput = document.getElementById('chat-number-input');
const summaryPanel = document.getElementById('summary-panel');
const scrollIndicator = document.getElementById('scroll-indicator');

async function loadTranscripts(split = '') {
    const url = split ? `/api/transcripts?split=${split}` : '/api/transcripts';
    const response = await fetch(url);
    const data = await response.json();
    return data.transcripts;
}

async function loadTranscript(transcriptId) {
    const response = await fetch(`/api/transcript/${transcriptId}`);
    return response.json();
}

function renderMessages(messages) {
    chatContainer.innerHTML = '';

    for (const msg of messages) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${msg.role}`;

        const labelDiv = document.createElement('div');
        labelDiv.className = 'message-label';
        labelDiv.textContent = msg.role === 'ai' ? 'AI' : 'User';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = msg.content;

        messageDiv.appendChild(labelDiv);
        messageDiv.appendChild(contentDiv);
        chatContainer.appendChild(messageDiv);
    }

    chatContainer.scrollTop = 0;
}

const FIELD_CONFIG = [
    { key: 'job_title', label: 'Job Title', half: true },
    { key: 'industry', label: 'Industry', half: true },
    { key: 'experience_level', label: 'Experience Level', half: true },
    { key: 'sentiment', label: 'Sentiment', half: true },
    { key: 'ai_tools_mentioned', label: 'AI Tools Mentioned', list: true },
    { key: 'primary_use_cases', label: 'Primary Use Cases', list: true },
    { key: 'key_pain_points', label: 'Key Pain Points', list: true },
    { key: 'last_project_summary', label: 'Last Project Summary' },
];

function renderSummaryCards(transcript) {
    summaryPanel.innerHTML = '';

    for (const field of FIELD_CONFIG) {
        const value = transcript[field.key];

        if (!value || (Array.isArray(value) && value.length === 0)) {
            continue;
        }

        const card = document.createElement('div');
        card.className = `summary-card${field.half ? ' half' : ''}`;

        const label = document.createElement('div');
        label.className = 'card-label';
        label.textContent = field.label;

        const valueDiv = document.createElement('div');
        valueDiv.className = 'card-value';

        if (field.list && Array.isArray(value)) {
            const ul = document.createElement('ul');
            for (const item of value) {
                const li = document.createElement('li');
                li.textContent = item;
                ul.appendChild(li);
            }
            valueDiv.appendChild(ul);
        } else {
            valueDiv.textContent = value;
        }

        card.appendChild(label);
        card.appendChild(valueDiv);
        summaryPanel.appendChild(card);
    }

    // Reset scroll position and update indicator
    summaryPanel.scrollTop = 0;
    updateScrollIndicator();
}

function updateScrollIndicator() {
    const hasOverflow = summaryPanel.scrollHeight > summaryPanel.clientHeight;

    if (!hasOverflow) {
        scrollIndicator.classList.add('hidden');
        return;
    }

    scrollIndicator.classList.remove('hidden');

    // Check if scrolled to bottom (with small threshold for rounding)
    const isAtBottom = summaryPanel.scrollTop + summaryPanel.clientHeight >= summaryPanel.scrollHeight - 5;

    if (isAtBottom) {
        scrollIndicator.classList.add('up');
    } else {
        scrollIndicator.classList.remove('up');
    }
}

function updateNavigation() {
    const total = filteredTranscripts.length;
    navInfo.textContent = total > 0 ? `${currentIndex + 1} / ${total}` : '0 / 0';

    prevBtn.disabled = currentIndex <= 0;
    nextBtn.disabled = currentIndex >= total - 1;

    // Update chat number input to reflect current position
    chatNumberInput.value = total > 0 ? currentIndex + 1 : '';
    chatNumberInput.max = total;
}

async function showTranscript(index) {
    if (index < 0 || index >= filteredTranscripts.length) return;

    currentIndex = index;
    const transcriptInfo = filteredTranscripts[index];

    chatContainer.innerHTML = '<div class="loading">Loading...</div>';
    summaryPanel.innerHTML = '<div class="loading">Loading summary...</div>';

    const transcript = await loadTranscript(transcriptInfo.transcript_id);

    metadata.textContent = `${transcript.transcript_id} | ${transcript.split}`;
    renderMessages(transcript.messages);
    renderSummaryCards(transcript);
    updateNavigation();
}

async function filterBySplit(split) {
    chatContainer.innerHTML = '<div class="loading">Loading transcripts...</div>';

    filteredTranscripts = split
        ? allTranscripts.filter(t => t.split === split)
        : [...allTranscripts];

    currentIndex = 0;

    if (filteredTranscripts.length > 0) {
        await showTranscript(0);
    } else {
        chatContainer.innerHTML = '<div class="loading">No transcripts found</div>';
        metadata.textContent = '';
        updateNavigation();
    }
}

prevBtn.addEventListener('click', () => {
    if (currentIndex > 0) {
        showTranscript(currentIndex - 1);
    }
});

nextBtn.addEventListener('click', () => {
    if (currentIndex < filteredTranscripts.length - 1) {
        showTranscript(currentIndex + 1);
    }
});

splitFilter.addEventListener('change', (e) => {
    filterBySplit(e.target.value);
});

chatNumberInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        const value = parseInt(chatNumberInput.value, 10);
        if (!isNaN(value) && filteredTranscripts.length > 0) {
            // Clamp to valid range
            const clamped = Math.max(1, Math.min(value, filteredTranscripts.length));
            showTranscript(clamped - 1);
        }
        chatNumberInput.blur();
    }
});

summaryPanel.addEventListener('scroll', updateScrollIndicator);

scrollIndicator.addEventListener('click', () => {
    const isUp = scrollIndicator.classList.contains('up');
    if (isUp) {
        summaryPanel.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        summaryPanel.scrollTo({ top: summaryPanel.scrollHeight, behavior: 'smooth' });
    }
});

async function init() {
    allTranscripts = await loadTranscripts();
    filteredTranscripts = [...allTranscripts];

    // Check for deep link parameter
    const urlParams = new URLSearchParams(window.location.search);
    const targetId = urlParams.get('id');

    if (targetId && filteredTranscripts.length > 0) {
        const index = filteredTranscripts.findIndex(t => t.transcript_id === targetId);
        if (index >= 0) {
            await showTranscript(index);
            return;
        }
    }

    if (filteredTranscripts.length > 0) {
        await showTranscript(0);
    }
}

init();
