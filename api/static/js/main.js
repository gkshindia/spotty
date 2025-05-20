/**
 * SpottyCloud UI - Main JavaScript
 */

// API endpoint base URL
const API_BASE_URL = '/api';

/**
 * Utility function to make API calls
 * @param {string} endpoint - API endpoint path
 * @param {Object} options - Fetch options
 * @returns {Promise} - Fetch promise
 */
async function fetchAPI(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };
    
    const fetchOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, fetchOptions);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `API Error: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API Error (${url}):`, error);
        throw error;
    }
}

/**
 * Format a timestamp (epoch seconds) to readable date/time
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {string} - Formatted date/time string
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

/**
 * Format a duration in seconds to readable format
 * @param {number} seconds - Duration in seconds
 * @returns {string} - Formatted duration string
 */
function formatDuration(seconds) {
    if (!seconds) return '-';
    
    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

/**
 * Create a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, error, warning, info)
 */
function showToast(message, type = 'info') {
    // Check if toast container exists
    let toastContainer = document.getElementById('toast-container');
    
    // Create container if it doesn't exist
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = `toast-${Date.now()}`;
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add toast to container
    toastContainer.appendChild(toast);
    
    // Initialize and show the toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 5000
    });
    bsToast.show();
    
    // Remove from DOM after hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

/**
 * Initialize the page based on the current path
 */
function initPage() {
    const path = window.location.pathname;
    
    // Common initialization for all pages
    setupNavigation(path);
    
    // Page-specific initialization
    if (path === '/dashboard' || path === '/') {
        initDashboard();
    } else if (path.startsWith('/instances')) {
        initInstancesPage();
    } else if (path.startsWith('/workloads')) {
        initWorkloadsPage();
    } else if (path.startsWith('/scripts')) {
        initScriptsPage();
    } else if (path.startsWith('/costs')) {
        initCostsPage();
    }
}

/**
 * Set up navigation highlighting
 * @param {string} currentPath - Current page path
 */
function setupNavigation(currentPath) {
    // Reset all navigation links
    document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Highlight the current page's navigation link
    let activePath = currentPath;
    if (currentPath === '/') {
        activePath = '/dashboard';
    }
    
    const activeLink = document.querySelector(`.navbar-nav .nav-link[href="${activePath}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
}

/**
 * Initialize the dashboard page
 */
function initDashboard() {
    console.log('Dashboard page initialized');
    
    // Add any dashboard-specific initialization here
    // This is just a placeholder since the actual dashboard initialization
    // is already included in the dashboard.html template
}

/**
 * Initialize instances page
 */
function initInstancesPage() {
    console.log('Instances page initialized');
    // This would be implemented when we have the instances page template
}

/**
 * Initialize workloads page
 */
function initWorkloadsPage() {
    console.log('Workloads page initialized');
    // This would be implemented when we have the workloads page template
}

/**
 * Initialize scripts page
 */
function initScriptsPage() {
    console.log('Scripts page initialized');
    // This would be implemented when we have the scripts page template
}

/**
 * Initialize costs page
 */
function initCostsPage() {
    console.log('Costs page initialized');
    // This would be implemented when we have the costs page template
}

// Initialize the page when DOM is fully loaded
document.addEventListener('DOMContentLoaded', initPage);
