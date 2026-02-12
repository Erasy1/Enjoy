(function () {
  "use strict";

  // Sidebar toggle
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("sidebarToggle");
  if (toggle && sidebar) {
    toggle.addEventListener("click", (e) => {
      e.preventDefault();
      sidebar.classList.toggle("closed");
    });
  }

  // Carousel arrows
  const stepSmall = 380 + 16;
  const stepPoster = 110 + 16;

  document.querySelectorAll(".arrow").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      const dir = parseInt(btn.getAttribute("data-dir") || "1", 10);
      const track = document.getElementById(targetId);
      if (!track) return;

      const localStep = targetId === "tvRecoTrack" ? stepPoster : stepSmall;
      track.scrollBy({ left: dir * localStep, behavior: "smooth" });
    });
  });

  // Helpers
  const esc = (s) =>
    String(s ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");

  async function fetchJSON(url) {
    const r = await fetch(url, { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return r.json();
  }

  const isTV = (x) => (x?.media_type || "") === "tv";
  const onlyTV = (items) => (Array.isArray(items) ? items : []).filter(isTV);

  function cardHTML(item) {
    const title = esc(item.title || "Untitled");
    const year = esc(item.year || "");
    const poster = item.poster_url ? esc(item.poster_url) : "";
    const tmdbId = esc(item.tmdb_id);
    const mediaType = esc(item.media_type || "tv");

    return `
      <a class="card" href="#"
         data-tmdb-id="${tmdbId}"
         data-media-type="${mediaType}">
        ${
          poster
            ? `<img src="${poster}" alt="${title}" loading="lazy">`
            : `<div class="poster-placeholder">No image</div>`
        }
        <span>${title}${year ? " (" + year + ")" : ""}</span>
      </a>
    `;
  }

  function posterMiniHTML(item) {
    const poster = item.poster_url ? esc(item.poster_url) : "";
    const tmdbId = esc(item.tmdb_id);
    const title = esc(item.title || "Untitled");
    const mediaType = esc(item.media_type || "tv");

    return `
      <a class="card" href="#"
         data-tmdb-id="${tmdbId}"
         data-media-type="${mediaType}">
        ${
          poster
            ? `<img src="${poster}" alt="${title}" loading="lazy">`
            : `<div class="poster-placeholder">No image</div>`
        }
        <span>${title}</span>
      </a>
    `;
  }

  // Media Modal
  const mediaModal = document.getElementById("mediaModal");
  const mediaBackdrop = document.getElementById("mediaModalBackdrop");
  const mediaClose = document.getElementById("mediaModalClose");

  const mPoster = document.getElementById("mediaModalPoster");
  const mTrailer = document.getElementById("mediaModalTrailer");
  const mTitle = document.getElementById("mediaModalTitle");
  const mMeta = document.getElementById("mediaModalMeta");
  const mDesc = document.getElementById("mediaModalDesc");
  const btnWatch = document.getElementById("btnWatch");
  const btnTrailer = document.getElementById("btnTrailer");

  let currentTmdbId = null;
  let currentMediaType = "tv";

  function openModal() {
    if (!mediaModal) return;
    mediaModal.classList.add("open");
    mediaModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    if (!mediaModal) return;
    mediaModal.classList.remove("open");
    mediaModal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";

    if (mTrailer) {
      mTrailer.innerHTML = "";
      mTrailer.classList.add("hidden");
    }
    if (mPoster) mPoster.classList.remove("hidden");

    currentTmdbId = null;
    currentMediaType = "tv";
  }

  if (mediaBackdrop) mediaBackdrop.addEventListener("click", closeModal);
  if (mediaClose) mediaClose.addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  async function openTrailerInline(tmdbId) {
    try {
      const d = await fetchJSON(`/api/tmdb/trailer/${tmdbId}?lang=ru-RU`);
      if (!d.key) return alert("Trailer not found");

      if (mPoster) mPoster.classList.add("hidden");
      if (mTrailer) {
        mTrailer.classList.remove("hidden");
        mTrailer.innerHTML = `
          <iframe
            src="https://www.youtube.com/embed/${esc(d.key)}?autoplay=1&rel=0"
            title="Trailer"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowfullscreen
          ></iframe>
        `;
      }
    } catch (e) {
      console.error(e);
      alert("Trailer not found");
    }
  }

  async function openMediaDetails(tmdbId, mediaType, titleFallback) {
    currentTmdbId = tmdbId;
    currentMediaType = mediaType === "movie" ? "movie" : "tv";

    if (mTrailer) {
      mTrailer.innerHTML = "";
      mTrailer.classList.add("hidden");
    }
    if (mPoster) {
      mPoster.classList.remove("hidden");
      mPoster.innerHTML = "";
    }
    if (mTitle) mTitle.textContent = "Loading...";
    if (mMeta) mMeta.textContent = "—";
    if (mDesc) mDesc.textContent = "—";

    openModal();

    try {
      const data = await fetchJSON(`/api/tmdb/details/${tmdbId}?lang=ru-RU`);
      const title = data.title || titleFallback || "Untitled";
      const year = data.release_date ? String(data.release_date).slice(0, 4) : "";
      const genres = Array.isArray(data.genres) ? data.genres : [];
      const overview = data.overview || "No description.";
      const poster = data.poster_url || "";

      if (mTitle) mTitle.textContent = title;
      if (mMeta) mMeta.textContent = `${year ? year + " · " : ""}${genres.length ? genres.join(", ") : ""}`;
      if (mDesc) mDesc.textContent = overview;

      if (mPoster) {
        mPoster.innerHTML = poster
          ? `<img src="${esc(poster)}" alt="${esc(title)}" loading="lazy">`
          : `<div class="poster-placeholder">No image</div>`;
      }

      if (btnWatch) btnWatch.onclick = () => {
        if (!currentTmdbId) return;
        window.location.href = `/watch/${currentMediaType}/${currentTmdbId}`;
      };

      if (btnTrailer) btnTrailer.onclick = () => openTrailerInline(tmdbId);
    } catch (e) {
      console.error(e);
      if (mTitle) mTitle.textContent = titleFallback || "Failed to load";
      if (mDesc) mDesc.textContent = "Try again later.";
    }
  }

  document.addEventListener("click", (e) => {
    const a = e.target.closest("a.card");
    if (!a) return;

    const tmdbId = a.getAttribute("data-tmdb-id");
    if (!tmdbId) return;

    const mediaType = (a.getAttribute("data-media-type") || "tv").trim();
    const titleText = a.querySelector("span") ? a.querySelector("span").textContent : "";

    e.preventDefault();
    openMediaDetails(tmdbId, mediaType, titleText);
  });

  // Genres UI
  const genresGrid = document.getElementById("genresGrid");
  const selected = new Set();

  function renderGenres(items) {
    if (!genresGrid) return;

    genresGrid.innerHTML = (items || [])
      .map((g) => {
        const id = String(g.id);
        const name = esc(g.name).toUpperCase();
        return `
          <div class="genreItem" data-id="${id}">
            <span class="genreDot"></span>
            <span>${name}</span>
          </div>
        `;
      })
      .join("");

    genresGrid.addEventListener("click", (e) => {
      const el = e.target.closest(".genreItem");
      if (!el) return;

      const id = el.getAttribute("data-id");
      if (!id) return;

      if (selected.has(id)) {
        selected.delete(id);
        el.classList.remove("active");
      } else {
        selected.add(id);
        el.classList.add("active");
      }
    });
  }

  // Filters
  const yearSelect = document.getElementById("yearSelect");
  const countrySelect = document.getElementById("countrySelect");
  const btnApply = document.getElementById("btnApply");

  function fillYears() {
    if (!yearSelect) return;
    const now = new Date().getFullYear();
    let html = `<option value="">YEAR</option>`;
    for (let y = now; y >= now - 40; y--) html += `<option value="${y}">${y}</option>`;
    yearSelect.innerHTML = html;
  }

  const tvRecoTrack = document.getElementById("tvRecoTrack");
  const tvResTrack = document.getElementById("tvResTrack");
  const resultsBlock = document.getElementById("resultsBlock");

  function scrollToResults() {
    if (!resultsBlock) return;
    resultsBlock.scrollIntoView({ behavior: "smooth", block: "start" });
    resultsBlock.classList.remove("fadeInUp");
    void resultsBlock.offsetWidth;
    resultsBlock.classList.add("fadeInUp");
  }

  async function loadRecommendationRow() {
    if (!tvRecoTrack) return;
    tvRecoTrack.innerHTML = `<div class="empty">Loading...</div>`;

    try {
      const d = await fetchJSON(`/api/recommendations?limit=30&type=tv`);
      const items = onlyTV(d.items);
      if (items.length) {
        tvRecoTrack.innerHTML = items.slice(0, 12).map(posterMiniHTML).join("");
        return;
      }
    } catch (e) {
      console.warn("tv reco failed -> fallback", e);
    }

    try {
      const top = await fetchJSON(`/api/tv/top?kind=top30&lang=ru-RU`);
      const items = onlyTV(top.items);
      tvRecoTrack.innerHTML =
        items.slice(0, 12).map(posterMiniHTML).join("") || `<div class="empty">No recommendations</div>`;
    } catch (e) {
      console.error("tv fallback top failed", e);
      tvRecoTrack.innerHTML = `<div class="empty">No recommendations</div>`;
    }
  }

  async function loadResults() {
    if (!tvResTrack) return;

    const genres = Array.from(selected).join(",");
    const year = yearSelect ? yearSelect.value : "";
    const region = countrySelect ? countrySelect.value : "";

    const url =
      `/api/tv/discover?lang=ru-RU&genres=${encodeURIComponent(genres)}` +
      `&year=${encodeURIComponent(year)}&region=${encodeURIComponent(region)}&page=1`;

    tvResTrack.innerHTML = `<div class="empty">Loading...</div>`;

    try {
      const data = await fetchJSON(url);
      const items = onlyTV(data.items);
      tvResTrack.innerHTML = items.length ? items.map(cardHTML).join("") : `<div class="empty">No results</div>`;
      scrollToResults();
    } catch (e) {
      console.error("TV DISCOVER ERROR:", e);
      tvResTrack.innerHTML = `<div class="empty">Discover failed</div>`;
      scrollToResults();
    }
  }

  if (btnApply) btnApply.onclick = () => loadResults();

  const btnTop30Tv = document.getElementById("btnTop30Tv");
  const btnTop60Tv = document.getElementById("btnTop60Tv");

  async function loadTopForYou(limit){
    if (!tvResTrack) return;
    tvResTrack.innerHTML = `<div class="empty">Loading...</div>`;
  
    try{
      const d = await fetchJSON(`/api/recommendations?limit=${limit}&type=tv`);
      const items = Array.isArray(data.items) ? data.items : [];
      if (items.length) {
        tvResTrack.innerHTML = items.map(cardHTML).join("");
        scrollToResults();
        return;
      }
    }catch(e){
      console.warn("TV reco failed -> fallback", e);
    }
  
    try {
      const kind = limit === 60 ? "top60" : "top30";
      const top = await fetchJSON(`/api/tv/top?kind=${kind}&lang=ru-RU`);
      const items = onlyTV(top.items);
      tvResTrack.innerHTML = items.length
        ? items.slice(0, limit).map(cardHTML).join("")
        : `<div class="empty">No results</div>`;
    } catch (e) {
      console.error("TV fallback top failed", e);
      tvResTrack.innerHTML = `<div class="empty">No results</div>`;
    }
  
    scrollToResults();
  }
  

  if (btnTop30Tv) btnTop30Tv.onclick = () => loadTopForYou(30);
  if (btnTop60Tv) btnTop60Tv.onclick = () => loadTopForYou(60);

  // Topbar: Search, Notif, Profile
  const btnSearch = document.getElementById("btnSearch");
  const btnNotif = document.getElementById("btnNotif");
  const btnProfile = document.getElementById("btnProfile");

  const searchModal = document.getElementById("searchModal");
  const searchBackdrop = document.getElementById("searchBackdrop");
  const searchClose = document.getElementById("searchClose");
  const searchInput = document.getElementById("searchInput");
  const searchResults = document.getElementById("searchResults");

  const notifModal = document.getElementById("notifModal");
  const notifBackdrop = document.getElementById("notifBackdrop");
  const notifClose = document.getElementById("notifClose");

  const profileMenu = document.getElementById("profileMenu");

  function openSimpleModal(modal) {
    if (!modal) return;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }
  function closeSimpleModal(modal) {
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  if (btnSearch)
    btnSearch.onclick = () => {
      openSimpleModal(searchModal);
      if (searchInput) {
        searchInput.value = "";
        searchInput.focus();
      }
      if (searchResults) searchResults.innerHTML = "";
    };
  if (searchBackdrop) searchBackdrop.onclick = () => closeSimpleModal(searchModal);
  if (searchClose) searchClose.onclick = () => closeSimpleModal(searchModal);

  if (btnNotif) btnNotif.onclick = () => openSimpleModal(notifModal);
  if (notifBackdrop) notifBackdrop.onclick = () => closeSimpleModal(notifModal);
  if (notifClose) notifClose.onclick = () => closeSimpleModal(notifModal);

  if (btnProfile && profileMenu) {
    btnProfile.onclick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      profileMenu.classList.toggle("open");
    };

    document.addEventListener("click", (e) => {
      if (!profileMenu.classList.contains("open")) return;
      const inside = e.target.closest("#profileMenu") || e.target.closest("#btnProfile");
      if (!inside) profileMenu.classList.remove("open");
    });
  }

  let searchTimer = null;
  async function doSearch(q) {
    if (!searchResults) return;
    const query = (q || "").trim();
    if (query.length < 2) {
      searchResults.innerHTML = `<div class="empty">Type 2+ chars</div>`;
      return;
    }
    try {
      const data = await fetchJSON(`/api/tmdb/search?q=${encodeURIComponent(query)}&lang=ru-RU`);
      const items = onlyTV(data.results);
      searchResults.innerHTML = items.length ? items.map(cardHTML).join("") : `<div class="empty">No results</div>`;
    } catch (e) {
      console.error("search error:", e);
      searchResults.innerHTML = `<div class="empty">Search failed</div>`;
    }
  }

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => doSearch(searchInput.value), 250);
    });
  }

  // Init
  (async function init() {
    fillYears();

    try {
      const g = await fetchJSON("/api/genres/tv?lang=ru-RU");
      renderGenres(g.items || []);
    } catch (e) {
      console.error("tv genres error", e);
    }

    try {
      await loadRecommendationRow();
    } catch (e) {
      console.error(e);
    }

    try {
      await loadResults();
    } catch (e) {
      console.error(e);
    }
  })();
})();
