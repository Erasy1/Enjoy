(function () {
    "use strict";
  
    const sidebar = document.getElementById("sidebar");
    const toggle = document.getElementById("sidebarToggle");
    if (toggle && sidebar) {
      toggle.addEventListener("click", (e) => {
        e.preventDefault();
        sidebar.classList.toggle("closed");
      });
    }
  
    const elQuery = document.getElementById("aiQuery");
    const elType = document.getElementById("aiType");
    const elYear = document.getElementById("aiYear");
    const elGenre = document.getElementById("aiGenre");
    const elBtn = document.getElementById("aiSearchBtn");
    const elClear = document.getElementById("aiClearBtn");
    const elResults = document.getElementById("aiResults");
    const elStatus = document.getElementById("aiStatus");
    const elMeta = document.getElementById("aiMeta");
  
    function setLoading(on) {
      if (!elStatus) return;
      elStatus.hidden = !on;
    }
  
    function escapeHtml(s) {
      return String(s || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }
  
    function makeCard(item) {
      const poster = item.poster_url || "https://via.placeholder.com/500x750?text=No+Poster";
      const title = escapeHtml(item.title);
      const rating = item.vote_average ?? 0;
      const type = item.media_type === "tv" ? "Series" : "Movie";
  
      const div = document.createElement("div");
      div.className = "aiCard";
      div.innerHTML = `
        <img class="aiPoster" src="${poster}" alt="${title}">
        <div class="aiMeta">
          <div class="aiTitle">${title}</div>
          <div class="aiSub">
            <span class="aiBadge">⭐ ${rating}</span>
            <span class="aiBadge">${type}</span>
          </div>
        </div>
      `;
      return div;
    }
  
    async function runSearch() {
      const query = (elQuery?.value || "").trim();
      const media_type = elType?.value || "multi";
  
      const yearRaw = (elYear?.value || "").trim();
      const genreRaw = (elGenre?.value || "").trim();
  
      const year = yearRaw ? parseInt(yearRaw, 10) : null;
      const genre_id = genreRaw ? parseInt(genreRaw, 10) : null;
  
      elResults.innerHTML = "";
      elMeta.textContent = "";
      setLoading(true);
  
      try {
        const resp = await fetch("/api/assistant/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            media_type,
            year,
            genre_id,
            lang: "ru-RU",
            limit: 24
          })
        });
  
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        const data = await resp.json();
        const items = data.items || [];
  
        if (items.length === 0) {
          elMeta.textContent = "Ничего не найдено. Попробуй изменить запрос или убрать фильтры.";
          return;
        }
  
        elMeta.textContent = `Found: ${items.length}`;
        items.forEach((it) => elResults.appendChild(makeCard(it)));
  
      } catch (e) {
        console.error(e);
        elMeta.textContent = "Ошибка поиска. Проверь TMDB_API_KEY и backend.";
      } finally {
        setLoading(false);
      }
    }
  
    function clearAll() {
      if (elQuery) elQuery.value = "";
      if (elYear) elYear.value = "";
      if (elGenre) elGenre.value = "";
      if (elType) elType.value = "multi";
      elResults.innerHTML = "";
      elMeta.textContent = "";
    }
  
    if (elBtn) elBtn.addEventListener("click", runSearch);
    if (elClear) elClear.addEventListener("click", clearAll);
  
    if (elQuery) {
      elQuery.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") runSearch();
      });
    }
  })();
  