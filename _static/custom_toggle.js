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

// Force Jupyter Book to always use light mode
window.addEventListener("DOMContentLoaded", function () {
    if (document.documentElement.getAttribute("data-theme") !== "light") {
      document.documentElement.setAttribute("data-theme", "light");
      // Remove dark mode class if present
      document.documentElement.classList.remove("theme-dark");
      document.documentElement.classList.add("theme-light");
    }
    // Remove theme switcher if you want (optional)
    // var switcher = document.querySelector('.theme-switch-button, .toggle-switch');
    // if (switcher) {
    //   switcher.style.display = "none";
    // }
  });