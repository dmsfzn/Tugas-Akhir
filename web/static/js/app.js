/* MotorMind — app.js
   Global JavaScript for the main dashboard application. */

'use strict';

/* TOAST */
/**
 * Displays a toast notification on the screen.
 * @param {string} msg - The message to display.
 * @param {string} [type='info'] - The type of toast ('success', 'danger', 'warning', 'info').
 */
function showToast(msg, type) {
  // Default to 'info' type if no specific type is provided
  type = type || 'info';
  
  // Map toast types to Bootstrap icons and specific colors
  const icons = {
    success: '<i class="bi bi-check-circle-fill" style="color:#22c55e"></i>',
    danger:  '<i class="bi bi-exclamation-circle-fill" style="color:#ef4444"></i>',
    warning: '<i class="bi bi-exclamation-triangle-fill" style="color:#fbbf24"></i>',
    info:    '<i class="bi bi-info-circle-fill" style="color:#818cf8"></i>',
  };
  
  // Find the designated toast container on the page
  const c = document.getElementById('toastContainer');
  if (!c) return; // Exit silently if there's no container (e.g., on a page without toasts)
  
  // Construct the toast DOM element
  const t = document.createElement('div');
  t.className = 'mm-toast';
  t.innerHTML = (icons[type] || icons.info) + '<span>' + msg + '</span>';
  
  // Inject the toast into the container
  c.appendChild(t);
  
  // Automatically remove the toast element from the DOM after 4 seconds (4000ms)
  setTimeout(function () { t.remove(); }, 4000);
}

/* CONFIRM DELETE */
/**
 * Prompts the user with a confirmation dialog before submitting a delete form.
 * @param {string} formId - The ID of the HTML form element to submit.
 */
function confirmDelete(formId) {
  if (confirm('Yakin ingin menghapus data ini?')) {
    document.getElementById(formId).submit();
  }
}

/* REPORT POPUP OPENER */
/**
 * Opens a centered popup window for displaying printable reports.
 * @param {string} url - The URL of the report to open.
 */
function openReport(url) {
  // Calculate window size: cap the max width at 960px and max height at 800px, but don't exceed screen size
  var w = Math.min(window.screen.width, 960);
  var h = Math.min(window.screen.height, 800);
  
  // Calculate center coordinates for the popup window
  var left = Math.round((window.screen.width  - w) / 2);
  var top  = Math.round((window.screen.height - h) / 2);
  
  // Open the report URL in a new popup window with specific dimensions and positions
  window.open(
    url,
    '_blank',
    'width=' + w + ',height=' + h + ',left=' + left + ',top=' + top +
    ',scrollbars=yes,resizable=yes'
  );
}

/* SIDEBAR ACTIVE LINK */
/**
 * Automatically highlights the active sidebar link based on the current window URL path.
 * Executes immediately on load.
 */
(function highlightActive() {
  // Get the current URL path from the browser
  var path = window.location.pathname;
  
  // Iterate over all sidebar navigation items
  document.querySelectorAll('.mm-sidebar .nav-item').forEach(function (link) {
    // If the link's href matches the current path, add the 'active' class to highlight it
    if (link.getAttribute('href') === path) {
      link.classList.add('active');
    }
  });
})();
