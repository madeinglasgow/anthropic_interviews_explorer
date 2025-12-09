let allTranscripts = [];
let filteredTranscripts = [];
let currentIndex = 0;

const chatContainer = document.getElementById('chat-container');
const metadata = document.getElementById('metadata');
const navInfo = document.getElementById('nav-info');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const splitFilter = document.getElementById('split-filter');

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

function updateNavigation() {
    const total = filteredTranscripts.length;
    navInfo.textContent = total > 0 ? `${currentIndex + 1} / ${total}` : '0 / 0';

    prevBtn.disabled = currentIndex <= 0;
    nextBtn.disabled = currentIndex >= total - 1;
}

async function showTranscript(index) {
    if (index < 0 || index >= filteredTranscripts.length) return;

    currentIndex = index;
    const transcriptInfo = filteredTranscripts[index];

    chatContainer.innerHTML = '<div class="loading">Loading...</div>';

    const transcript = await loadTranscript(transcriptInfo.transcript_id);

    metadata.textContent = `${transcript.transcript_id} | ${transcript.split}`;
    renderMessages(transcript.messages);
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

async function init() {
    allTranscripts = await loadTranscripts();
    filteredTranscripts = [...allTranscripts];

    if (filteredTranscripts.length > 0) {
        await showTranscript(0);
    }
}

init();
