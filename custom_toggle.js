// custom_toggle.js
window.addEventListener("DOMContentLoaded", function () {
    // Find the sidebar toggle button (hamburger menu)
    var toggle = document.querySelector(
        ".sidebar-toggle, .bd-sidebar-primary-toggle"
    );
    // If the sidebar is open, click to close it
    if (toggle) {
        if (document.body.classList.contains("bd-sidebar-primary--visible")) {
            toggle.click();
        }
    }
});
