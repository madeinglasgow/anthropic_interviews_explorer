// Chart.js default configuration
Chart.defaults.font.family = "'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
Chart.defaults.font.size = 12;

// Color palette based on coral theme
const COLORS = {
    primary: '#fd4a61',
    primaryLight: '#fde8eb',
    positive: '#22c55e',
    neutral: '#64748b',
    negative: '#ef4444',
    mixed: '#f59e0b',
};

const CHART_COLORS = [
    '#fd4a61',
    '#f97316',
    '#eab308',
    '#22c55e',
    '#14b8a6',
    '#06b6d4',
    '#3b82f6',
    '#8b5cf6',
    '#d946ef',
    '#ec4899',
];

const SENTIMENT_COLORS = {
    'positive': COLORS.positive,
    'neutral': COLORS.neutral,
    'negative': COLORS.negative,
    'mixed': COLORS.mixed,
};

async function fetchSummary() {
    const response = await fetch('/api/summary');
    return response.json();
}

function createDoughnutChart(ctx, labels, data, colors) {
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 12,
                        padding: 12,
                    }
                }
            }
        }
    });
}

function createHorizontalBarChart(ctx, labels, data, color = COLORS.primary) {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: color,
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        display: false
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function createGroupedBarChart(ctx, labels, datasets) {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets.map((ds, i) => ({
                label: ds.label,
                data: ds.data,
                backgroundColor: CHART_COLORS[i % CHART_COLORS.length],
                borderRadius: 4,
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 12,
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#f1f5f9'
                    }
                }
            }
        }
    });
}

function renderSentimentChart(data) {
    const ctx = document.getElementById('sentiment-chart').getContext('2d');
    const sentiments = Object.keys(data.sentiment_counts);
    const counts = Object.values(data.sentiment_counts);
    const colors = sentiments.map(s => SENTIMENT_COLORS[s.toLowerCase()] || COLORS.neutral);

    createDoughnutChart(ctx, sentiments, counts, colors);
}

function renderExperienceChart(data) {
    const ctx = document.getElementById('experience-chart').getContext('2d');
    const levels = Object.keys(data.experience_counts);
    const counts = Object.values(data.experience_counts);

    createDoughnutChart(ctx, levels, counts, CHART_COLORS.slice(0, levels.length));
}

function renderSplitChart(data) {
    const ctx = document.getElementById('split-chart').getContext('2d');
    const splits = Object.keys(data.split_counts);
    const counts = Object.values(data.split_counts);

    createDoughnutChart(ctx, splits, counts, CHART_COLORS.slice(0, splits.length));
}

function renderIndustriesChart(data) {
    const ctx = document.getElementById('industries-chart').getContext('2d');
    const labels = data.top_industries.map(i => i.name);
    const counts = data.top_industries.map(i => i.count);

    createHorizontalBarChart(ctx, labels, counts);
}

function renderToolsChart(data) {
    const ctx = document.getElementById('tools-chart').getContext('2d');
    const labels = data.top_tools.map(t => t.name);
    const counts = data.top_tools.map(t => t.count);

    createHorizontalBarChart(ctx, labels, counts, CHART_COLORS[4]);
}

function renderUseCasesChart(data) {
    const ctx = document.getElementById('use-cases-chart').getContext('2d');
    const labels = data.top_use_cases.map(u => u.name);
    const counts = data.top_use_cases.map(u => u.count);

    createHorizontalBarChart(ctx, labels, counts, CHART_COLORS[2]);
}

function renderPainPointsChart(data) {
    const ctx = document.getElementById('pain-points-chart').getContext('2d');
    const labels = data.top_pain_points.map(p => p.name);
    const counts = data.top_pain_points.map(p => p.count);

    createHorizontalBarChart(ctx, labels, counts, CHART_COLORS[3]);
}

function renderSentimentBySplitChart(data) {
    const ctx = document.getElementById('sentiment-by-split-chart').getContext('2d');
    const splits = Object.keys(data.sentiment_by_split);

    // Get all unique sentiments
    const allSentiments = new Set();
    for (const split of splits) {
        for (const sentiment of Object.keys(data.sentiment_by_split[split])) {
            allSentiments.add(sentiment);
        }
    }

    const sentiments = Array.from(allSentiments);
    const datasets = sentiments.map(sentiment => ({
        label: sentiment,
        data: splits.map(split => data.sentiment_by_split[split][sentiment] || 0),
    }));

    createGroupedBarChart(ctx, splits, datasets);
}

function renderSentimentByExperienceChart(data) {
    const ctx = document.getElementById('sentiment-by-experience-chart').getContext('2d');
    const experiences = Object.keys(data.sentiment_by_experience);

    // Get all unique sentiments
    const allSentiments = new Set();
    for (const exp of experiences) {
        for (const sentiment of Object.keys(data.sentiment_by_experience[exp])) {
            allSentiments.add(sentiment);
        }
    }

    const sentiments = Array.from(allSentiments);
    const datasets = sentiments.map(sentiment => ({
        label: sentiment,
        data: experiences.map(exp => data.sentiment_by_experience[exp][sentiment] || 0),
    }));

    createGroupedBarChart(ctx, experiences, datasets);
}

function renderSampleProjects(data) {
    const container = document.getElementById('sample-projects');
    container.innerHTML = '';

    if (!data.sample_projects || data.sample_projects.length === 0) {
        container.innerHTML = '<div class="loading-message">No project summaries available</div>';
        return;
    }

    for (const project of data.sample_projects) {
        const item = document.createElement('div');
        item.className = 'sample-item';
        item.textContent = project;
        container.appendChild(item);
    }
}

function renderSampleJobs(data) {
    const container = document.getElementById('sample-jobs');
    container.innerHTML = '';

    if (!data.sample_job_titles || data.sample_job_titles.length === 0) {
        container.innerHTML = '<div class="loading-message">No job titles available</div>';
        return;
    }

    for (const job of data.sample_job_titles) {
        const tag = document.createElement('span');
        tag.className = 'tag';
        tag.textContent = job;
        container.appendChild(tag);
    }
}

async function refreshSampleProjects() {
    const data = await fetchSummary();
    renderSampleProjects(data);
}

async function refreshSampleJobs() {
    const data = await fetchSummary();
    renderSampleJobs(data);
}

async function init() {
    try {
        const data = await fetchSummary();

        // Update total count
        document.getElementById('total-count').textContent =
            `${data.total_transcripts} transcripts`;

        // Render all charts
        renderSentimentChart(data);
        renderExperienceChart(data);
        renderSplitChart(data);
        renderIndustriesChart(data);
        renderToolsChart(data);
        renderUseCasesChart(data);
        renderPainPointsChart(data);
        renderSentimentBySplitChart(data);
        renderSentimentByExperienceChart(data);

        // Render sample content
        renderSampleProjects(data);
        renderSampleJobs(data);

        // Add shuffle button handlers
        document.getElementById('refresh-projects').addEventListener('click', refreshSampleProjects);
        document.getElementById('refresh-jobs').addEventListener('click', refreshSampleJobs);

    } catch (error) {
        console.error('Failed to load summary data:', error);
        document.getElementById('total-count').textContent = 'Error loading data';
    }
}

init();
