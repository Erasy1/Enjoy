(function () {
  "use strict";

  // ----------------------------
  // Sidebar open/close
  // ----------------------------
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("sidebarToggle");
  if (toggle && sidebar) {
    toggle.addEventListener("click", (e) => {
      e.preventDefault();
      sidebar.classList.toggle("closed");
    });
  }

  // ----------------------------
  // Carousel left/right
  // ----------------------------
  const stepSmall = 380 + 16;
  const stepRelease = 600 + 16;

  document.querySelectorAll(".arrow").forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-target");
      const dir = parseInt(btn.getAttribute("data-dir") || "1", 10);
      const track = document.getElementById(targetId);
      if (!track) return;

      const localStep = targetId === "relTrack" ? stepRelease : stepSmall;
      track.scrollBy({ left: dir * localStep, behavior: "smooth" });
    });
  });

  // ----------------------------
  // Helpers
  // ----------------------------
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

  function smallCardHTML(item) {
    const title = esc(item.title || "Untitled");
    const year = esc(item.year || "");
    const poster = item.poster_url ? esc(item.poster_url) : "";
    const tmdbId = esc(item.tmdb_id);
    const mediaType = esc(item.media_type || "movie");

    return `
      <a class="card"
         href="#"
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

  function releaseCardHTML(item, idx, isActive) {
    const title = esc(item.title || "Untitled");
    const year = esc(item.year || "");
    const img = item.img_url ? esc(item.img_url) : "";
    const tmdbId = esc(item.tmdb_id);
    const mediaType = esc(item.media_type || "movie");

    return `
      <a class="card releaseCard ${isActive ? "active" : ""}"
         href="#"
         data-idx="${idx}"
         data-tmdb-id="${tmdbId}"
         data-media-type="${mediaType}">
        ${
          img
            ? `<img src="${img}" alt="${title}" loading="lazy">`
            : `<div class="poster-placeholder">No image</div>`
        }
        <span>${title}${year ? " (" + year + ")" : ""}</span>
      </a>
    `;
  }

  // ----------------------------
  // Media Modal (Watch / Trailer)
  // ----------------------------
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

  function openMediaModal() {
    if (!mediaModal) return;
    mediaModal.classList.add("open");
    mediaModal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeMediaModal() {
    if (!mediaModal) return;
    mediaModal.classList.remove("open");
    mediaModal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";

    // stop trailer
    if (mTrailer) {
      mTrailer.innerHTML = "";
      mTrailer.classList.add("hidden");
    }
    if (mPoster) {
      mPoster.classList.remove("hidden");
    }
  }

  if (mediaBackdrop) mediaBackdrop.addEventListener("click", closeMediaModal);
  if (mediaClose) mediaClose.addEventListener("click", closeMediaModal);

  async function openTrailerInline(tmdbId) {
    try {
      const d = await fetchJSON(`/api/tmdb/trailer/${tmdbId}?lang=ru-RU`);
      if (!d.key) {
        alert("Trailer not found");
        return;
      }

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
      console.error("trailer error:", e);
      alert("Trailer not found");
    }
  }

  async function openMediaDetails(tmdbId, mediaType, titleFallback) {
    // reset
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

    openMediaModal();

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

      if (btnWatch) btnWatch.onclick = () => (window.location.href = `/watch/${mediaType}/${tmdbId}`);
      if (btnTrailer) btnTrailer.onclick = () => openTrailerInline(tmdbId);
    } catch (e) {
      console.error("details error:", e);
      if (mTitle) mTitle.textContent = titleFallback || "Failed to load";
      if (mDesc) mDesc.textContent = "Try again later.";
    }
  }

  // ----------------------------
  // Topbar actions: Search / Notifications / Profile
  // ----------------------------
  const btnSearch = document.getElementById("btnSearch");
  const btnNotif = document.getElementById("btnNotif");
  const btnProfile = document.getElementById("btnProfile");

  // Search modal refs
  const searchModal = document.getElementById("searchModal");
  const searchBackdrop = document.getElementById("searchBackdrop");
  const searchClose = document.getElementById("searchClose");
  const searchInput = document.getElementById("searchInput");
  const searchResults = document.getElementById("searchResults");

  // Notif modal refs
  const notifModal = document.getElementById("notifModal");
  const notifBackdrop = document.getElementById("notifBackdrop");
  const notifClose = document.getElementById("notifClose");

  // Profile menu
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

  // Search open/close
  if (btnSearch) btnSearch.onclick = () => {
    if (profileMenu) profileMenu.classList.remove("open");
    openSimpleModal(searchModal);
    if (searchInput) {
      searchInput.value = "";
      searchInput.focus();
    }
    if (searchResults) searchResults.innerHTML = "";
  };
  if (searchBackdrop) searchBackdrop.onclick = () => closeSimpleModal(searchModal);
  if (searchClose) searchClose.onclick = () => closeSimpleModal(searchModal);

  // Notif open/close
  if (btnNotif) btnNotif.onclick = () => {
    if (profileMenu) profileMenu.classList.remove("open");
    openSimpleModal(notifModal);
  };
  if (notifBackdrop) notifBackdrop.onclick = () => closeSimpleModal(notifModal);
  if (notifClose) notifClose.onclick = () => closeSimpleModal(notifModal);

  // Profile dropdown
  if (btnProfile && profileMenu) {
    btnProfile.onclick = (e) => {
      e.preventDefault();
      profileMenu.classList.toggle("open");
    };

    document.addEventListener("click", (e) => {
      if (!profileMenu.classList.contains("open")) return;
      const inside = e.target.closest("#profileMenu") || e.target.closest("#btnProfile");
      if (!inside) profileMenu.classList.remove("open");
    });
  }

  // Search logic (debounce)
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
      const items = Array.isArray(data.results) ? data.results : [];
      if (!items.length) {
        searchResults.innerHTML = `<div class="empty">No results</div>`;
        return;
      }
      searchResults.innerHTML = items.map(smallCardHTML).join("");
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


  
  // ----------------------------
  // Global click: open media modal by clicking on cards
  // ----------------------------
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a.card");
    if (!a) return;

    // do not open modal on release cards (they have selection logic)
    if (a.classList.contains("releaseCard")) return;

    const tmdbId = a.getAttribute("data-tmdb-id");
    const mediaType = a.getAttribute("data-media-type") || "movie";
    if (!tmdbId) return;

    e.preventDefault();

    // if clicked from search modal -> close it first
    closeSimpleModal(searchModal);

    const titleText = a.querySelector("span") ? a.querySelector("span").textContent : "";
    openMediaDetails(tmdbId, mediaType, titleText);
  });

  // ----------------------------
  // Recommendations
  // ----------------------------
  async function loadRecommendations() {
    const recTrack = document.getElementById("recTrack");
    if (!recTrack) return;

    try {
      const data = await fetchJSON("/api/recommendations?limit=20");
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) {
        recTrack.innerHTML = `<div class="empty">No recommendations yet</div>`;
        return;
      }
      recTrack.innerHTML = items.map(smallCardHTML).join("");
    } catch (e) {
      console.error("recommendations error:", e);
      recTrack.innerHTML = `<div class="empty">Failed to load recommendations</div>`;
    }
  }

  // ----------------------------
  // Trending
  // ----------------------------
  async function loadTrending() {
    const trTrack = document.getElementById("trTrack");
    if (!trTrack) return;

    try {
      const data = await fetchJSON("/api/trending?limit=20");
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) return;
      trTrack.innerHTML = items.map(smallCardHTML).join("");
    } catch (e) {
      console.error("trending error:", e);
    }
  }

  // ----------------------------
  // Continue Watching
  // ----------------------------
  async function loadContinueWatching() {
    const cwTrack = document.getElementById("cwTrack");
    if (!cwTrack) return;

    try {
      const data = await fetchJSON("/api/continue_watching?limit=20");
      const items = Array.isArray(data.items) ? data.items : [];

      if (!items.length) {
        cwTrack.innerHTML = `<div class="empty">No history yet</div>`;
        return;
      }

      cwTrack.innerHTML = items
        .map((it) => {
          const title = esc(it.title || "Untitled");
          const poster = it.poster_url ? esc(it.poster_url) : "";
          const mediaType = esc(it.media_type || "movie");
          const tmdbId = esc(it.tmdb_id);
          const progress = Math.max(0, Math.min(100, parseInt(it.progress || 0, 10)));

          return `
            <a class="card"
               href="/watch/${mediaType}/${tmdbId}"
               data-tmdb-id="${tmdbId}"
               data-media-type="${mediaType}">
              ${
                poster
                  ? `<img src="${poster}" alt="${title}" loading="lazy">`
                  : `<div class="poster-placeholder">No image</div>`
              }
              <span>${title}</span>
              <div class="cwBar"><div class="cwFill" style="width:${progress}%"></div></div>
            </a>
          `;
        })
        .join("");
    } catch (e) {
      console.error("continue watching error:", e);
      cwTrack.innerHTML = `<div class="empty">Failed to load history</div>`;
    }
  }

  // ----------------------------
  // Releases carousel + right info panel
  // ----------------------------
  async function loadReleasesCarousel() {
    const track = document.getElementById("relTrack");
    if (!track) return;

    const nameEl = document.getElementById("relName");
    const metaEl = document.getElementById("relMeta");
    const descEl = document.getElementById("relDesc");
    const moreBtn = document.getElementById("relMore");

    try {
      const data = await fetchJSON("/api/releases?kind=movie&limit=12");
      const items = Array.isArray(data.items) ? data.items : [];

      if (!items.length) {
        track.innerHTML = `<div class="empty">No releases</div>`;
        return;
      }

      track.innerHTML = items.map((it, idx) => releaseCardHTML(it, idx, idx === 0)).join("");

      function setActive(index) {
        const it = items[index];
        if (!it) return;

        track.querySelectorAll(".releaseCard").forEach((el) => el.classList.remove("active"));
        const activeEl = track.querySelector(`.releaseCard[data-idx="${index}"]`);
        if (activeEl) activeEl.classList.add("active");

        if (nameEl) nameEl.textContent = it.title || "";
        if (metaEl) metaEl.textContent = `${it.year || ""}${it.year ? " · " : ""}16+`;
        if (descEl) descEl.textContent = it.overview || "No description.";

        if (moreBtn) moreBtn.onclick = () => openMediaDetails(it.tmdb_id, it.media_type || "movie", it.title);
      }

      setActive(0);

      track.addEventListener("click", (e) => {
        const a = e.target.closest(".releaseCard");
        if (!a) return;
        e.preventDefault();
        const idx = parseInt(a.getAttribute("data-idx"), 10);
        if (!Number.isNaN(idx)) setActive(idx);
      });
    } catch (e) {
      console.error("releases carousel error:", e);
      track.innerHTML = `<div class="empty">Failed to load releases</div>`;
    }
  }

  // ----------------------------
  // Escape closes everything
  // ----------------------------
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;

    closeMediaModal();
    closeSimpleModal(searchModal);
    closeSimpleModal(notifModal);
    if (profileMenu) profileMenu.classList.remove("open");
  });

  // ----------------------------
  // Run
  // ----------------------------
  loadReleasesCarousel();
  loadRecommendations();
  loadTrending();
  loadContinueWatching();
})();

  