(function () {
    "use strict";
  
    function initSidebarToggle() {
      const sidebar = document.getElementById("sidebar");
      const toggle = document.getElementById("sidebarToggle");
  
      if (!sidebar || !toggle) return;
  
      toggle.addEventListener("click", (e) => {
        e.preventDefault();
        sidebar.classList.toggle("closed");
  
        try {
          localStorage.setItem("sidebarClosed", sidebar.classList.contains("closed") ? "1" : "0");
        } catch (_) {}
      });
  
      try {
        const saved = localStorage.getItem("sidebarClosed");
        if (saved === "1") sidebar.classList.add("closed");
      } catch (_) {}
    }
  
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initSidebarToggle);
    } else {
      initSidebarToggle();
    }
  })();
  