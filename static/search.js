const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const filterSplit = document.getElementById('filter-split');
const filterSentiment = document.getElementById('filter-sentiment');
const filterIndustry = document.getElementById('filter-industry');
const resultsInfo = document.getElementById('results-info');
const resultsContainer = document.getElementById('results-container');
const pagination = document.getElementById('pagination');

let currentQuery = '';
let currentOffset = 0;
const PAGE_SIZE = 20;

async function performSearch(query, offset = 0) {
    if (!query.trim()) {
        showEmptyState();
        return;
    }

    currentQuery = query;
    currentOffset = offset;

    resultsContainer.innerHTML = '<div class="loading">Searching...</div>';
    resultsInfo.textContent = '';
    pagination.innerHTML = '';

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                limit: PAGE_SIZE,
                offset: offset,
                split: filterSplit.value || null,
                sentiment: filterSentiment.value || null,
                industry: filterIndustry.value || null
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Search failed');
        }

        const data = await response.json();
        renderResults(data);
    } catch (error) {
        console.error('Search error:', error);
        resultsContainer.innerHTML = `<div class="error">Search failed: ${error.message}</div>`;
    }
}

function renderResults(data) {
    if (data.results.length === 0) {
        resultsContainer.innerHTML = '<div class="no-results">No matching interviews found</div>';
        resultsInfo.textContent = '0 results';
        return;
    }

    const start = data.offset + 1;
    const end = Math.min(data.offset + data.results.length, data.total);
    resultsInfo.textContent = `Showing ${start}-${end} of ${data.total} results`;

    resultsContainer.innerHTML = '';

    for (const result of data.results) {
        const card = document.createElement('a');
        card.className = 'result-card';
        card.href = `/viewer?id=${result.transcript_id}`;
        card.innerHTML = `
            <div class="result-header">
                <span class="result-title">
                    <span class="result-title-label">Job title:</span> ${result.job_title || 'Unknown'}
                    <span class="result-id">${result.transcript_id}</span>
                </span>
                <span class="relevance-score" title="Relevance score">
                    ${Math.round(result.score * 100)}%
                </span>
            </div>
            <div class="result-meta">
                <span class="meta-tag split">${result.split}</span>
                ${result.industry ? `<span class="meta-tag industry">${result.industry}</span>` : ''}
                ${result.sentiment ? `<span class="meta-tag sentiment ${result.sentiment.toLowerCase()}">${result.sentiment}</span>` : ''}
            </div>
            <p class="result-snippet">${result.snippet}</p>
        `;
        resultsContainer.appendChild(card);
    }

    renderPagination(data.total, data.offset);
}

function renderPagination(total, offset) {
    pagination.innerHTML = '';

    const totalPages = Math.ceil(total / PAGE_SIZE);
    const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

    if (totalPages <= 1) return;

    // Previous button
    if (currentPage > 1) {
        const prevBtn = document.createElement('button');
        prevBtn.className = 'page-btn';
        prevBtn.textContent = 'Previous';
        prevBtn.onclick = () => performSearch(currentQuery, (currentPage - 2) * PAGE_SIZE);
        pagination.appendChild(prevBtn);
    }

    // Page info
    const pageInfo = document.createElement('span');
    pageInfo.className = 'page-info';
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    pagination.appendChild(pageInfo);

    // Next button
    if (currentPage < totalPages) {
        const nextBtn = document.createElement('button');
        nextBtn.className = 'page-btn';
        nextBtn.textContent = 'Next';
        nextBtn.onclick = () => performSearch(currentQuery, currentPage * PAGE_SIZE);
        pagination.appendChild(nextBtn);
    }
}

function showEmptyState() {
    resultsContainer.innerHTML = `
        <div class="empty-state">
            <p>Enter a search query to find relevant interviews</p>
            <p class="hint">Try: "creative professionals using AI for brainstorming" or "concerns about AI replacing jobs"</p>
        </div>
    `;
    resultsInfo.textContent = '';
    pagination.innerHTML = '';
}

// Event listeners
searchBtn.addEventListener('click', () => performSearch(searchInput.value));

searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        performSearch(searchInput.value);
    }
});

// Re-search when filters change
[filterSplit, filterSentiment].forEach(filter => {
    filter.addEventListener('change', () => {
        if (currentQuery) {
            performSearch(currentQuery);
        }
    });
});

filterIndustry.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && currentQuery) {
        performSearch(currentQuery);
    }
});

// Check for deep link parameter
const urlParams = new URLSearchParams(window.location.search);
const queryParam = urlParams.get('q');
if (queryParam) {
    searchInput.value = queryParam;
    performSearch(queryParam);
}
