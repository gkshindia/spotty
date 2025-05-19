/**
 * SpottyCloud Dashboard JavaScript
 * Main application logic for the distributed computing dashboard
 */

// Global variables
let instanceData = {};
let workloadData = {};
let costData = {};
let systemStatus = {};
let charts = {};

// API endpoints
const API = {
    status: '/api/status',
    instances: '/api/instances',
    workloads: '/api/workloads',
    costs: '/api/costs',
    costHistory: '/api/costs/history',
    templates: '/api/templates'
};

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupEventListeners();
    initializeCharts();
    refreshDashboard();
    
    // Set up refresh intervals
    setInterval(refreshDashboard, 30000); // Refresh every 30 seconds
});

// Setup navigation between sections
function setupNavigation() {
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            
            // Remove active class from all links and sections
            navLinks.forEach(l => l.classList.remove('active'));
            document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
            
            // Add active class to clicked link and corresponding section
            link.classList.add('active');
            const targetSection = link.getAttribute('data-bs-target');
            document.getElementById(`${targetSection}-section`).classList.add('active');
        });
    });
}

// Setup event listeners for buttons and controls
function setupEventListeners() {
    // Refresh buttons
    document.getElementById('refresh-instances-btn').addEventListener('click', () => refreshInstances());
    document.getElementById('refresh-workloads-btn').addEventListener('click', () => refreshWorkloads());
    
    // Instance filtering
    const instanceFilterButtons = document.querySelectorAll('[data-filter]');
    instanceFilterButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            instanceFilterButtons.forEach(b => b.classList.remove('active'));
            button.classList.add('active');
            filterInstances(button.getAttribute('data-filter'));
        });
    });
    
    // Instance search
    document.getElementById('instance-search').addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        searchInstances(searchTerm);
    });
    
    // Workload submission
    document.getElementById('submit-workload-btn').addEventListener('click', submitNewWorkload);
    
    // Workload template selection
    document.getElementById('workload-template').addEventListener('change', (e) => {
        const templateId = e.target.value;
        if (templateId) {
            populateTemplateValues(templateId);
        }
    });
    
    // Resilience testing
    document.getElementById('terminate-instance-btn').addEventListener('click', terminateSelectedInstance);
    document.getElementById('start-random-failures-btn').addEventListener('click', startRandomFailures);
    document.getElementById('stop-random-failures-btn').addEventListener('click', stopRandomFailures);
    
    // Failure rate slider
    const failureSlider = document.getElementById('failure-percent');
    const failureValue = document.getElementById('failure-percent-value');
    failureSlider.addEventListener('input', () => {
        failureValue.textContent = `${failureSlider.value}%`;
    });
    
    // Cost history period selection
    const costPeriodButtons = document.querySelectorAll('[data-period]');
    costPeriodButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            costPeriodButtons.forEach(b => b.classList.remove('active'));
            button.classList.add('active');
            const period = parseInt(button.getAttribute('data-period'));
            updateCostHistoryChart(period);
        });
    });
}

// Initialize charts with empty data
function initializeCharts() {
    // Instance distribution chart
    const instanceDistCtx = document.getElementById('instance-distribution-chart').getContext('2d');
    charts.instanceDistribution = new Chart(instanceDistCtx, {
        type: 'pie',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
    
    // Cost history chart
    const costHistoryCtx = document.getElementById('cost-history-chart').getContext('2d');
    charts.costHistory = new Chart(costHistoryCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Spot Cost',
                    data: [],
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.1)',
                    fill: true
                },
                {
                    label: 'On-Demand Cost',
                    data: [],
                    borderColor: '#e74a3b',
                    backgroundColor: 'rgba(231, 74, 59, 0.1)',
                    borderDash: [5, 5],
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Cost ($)'
                    }
                }
            }
        }
    });
    
    // Cost trend chart
    const costTrendCtx = document.getElementById('cost-trend-chart').getContext('2d');
    charts.costTrend = new Chart(costTrendCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Spot Cost',
                    data: [],
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.1)',
                    fill: true
                },
                {
                    label: 'On-Demand Equivalent',
                    data: [],
                    borderColor: '#e74a3b',
                    backgroundColor: 'rgba(231, 74, 59, 0.1)',
                    borderDash: [5, 5],
                    fill: false
                },
                {
                    label: 'Savings',
                    data: [],
                    borderColor: '#1cc88a',
                    backgroundColor: 'rgba(28, 200, 138, 0.1)',
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Cost ($)'
                    }
                }
            }
        }
    });
    
    // Cost by instance type chart
    const costByTypeCtx = document.getElementById('cost-by-type-chart').getContext('2d');
    charts.costByType = new Chart(costByTypeCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Spot Cost',
                    data: [],
                    backgroundColor: '#4e73df'
                },
                {
                    label: 'On-Demand Cost',
                    data: [],
                    backgroundColor: '#e74a3b'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Cost ($)'
                    }
                }
            }
        }
    });
}

// Refresh the dashboard data
async function refreshDashboard() {
    try {
        // Fetch system status
        await refreshSystemStatus();
        
        // Fetch instances
        await refreshInstances();
        
        // Fetch workloads
        await refreshWorkloads();
        
        // Fetch costs
        await refreshCosts();
        
        // Fetch templates
        await fetchTemplates();
        
        // Update last refresh time
        updateLastRefreshTime();
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showError('Failed to refresh dashboard data');
    }
}

// Refresh system status
async function refreshSystemStatus() {
    try {
        const response = await fetch(API.status);
        if (!response.ok) throw new Error('Failed to fetch system status');
        
        systemStatus = await response.json();
        updateSystemStatusUI(systemStatus);
    } catch (error) {
        console.error('Error fetching system status:', error);
        showError('Failed to fetch system status');
    }
}

// Update system status UI elements
function updateSystemStatusUI(status) {
    // Update status indicator
    const statusIndicator = document.getElementById('system-status-indicator');
    const statusText = document.getElementById('system-status');
    
    statusIndicator.className = 'status-indicator';
    if (status.health === 'healthy') {
        statusIndicator.classList.add('healthy');
        statusText.textContent = 'Healthy';
    } else if (status.health === 'degraded') {
        statusIndicator.classList.add('degraded');
        statusText.textContent = 'Degraded';
    } else {
        statusIndicator.classList.add('unhealthy');
        statusText.textContent = 'Unhealthy';
    }
    
    // Update counters
    document.getElementById('instance-counter').textContent = status.active_instances || 0;
    document.getElementById('workload-counter').textContent = status.running_workloads || 0;
    document.getElementById('pending-workloads').textContent = status.queued_workloads || 0;
    document.getElementById('running-workloads').textContent = status.running_workloads || 0;
    
    // Update instance progress
    const instanceProgress = document.getElementById('instance-progress');
    const progressPercent = status.active_instances / 20 * 100; // Assuming max 20 instances
    instanceProgress.style.width = `${Math.min(progressPercent, 100)}%`;
    
    // Update cost data if available
    if (status.cost_data) {
        const costData = status.cost_data;
        document.getElementById('savings-percentage').textContent = `${costData.savings_percent || 0}%`;
        document.getElementById('spot-cost').textContent = costData.total_spot_cost.toFixed(2);
        document.getElementById('ondemand-cost').textContent = costData.total_ondemand_cost.toFixed(2);
    }
}
