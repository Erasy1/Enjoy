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
    const stepWide = 560 + 16;
    document.querySelectorAll(".arrow").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetId = btn.getAttribute("data-target");
        const dir = parseInt(btn.getAttribute("data-dir") || "1", 10);
        const track = document.getElementById(targetId);
        if (!track) return;
        track.scrollBy({ left: dir * stepWide, behavior: "smooth" });
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
  
    async function fetchJSON(url, opts) {
      const r = await fetch(url, { headers: { Accept: "application/json" }, ...opts });
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }
  
    function secondsToMMSS(sec){
      sec = Math.max(0, Number(sec||0));
      const m = Math.floor(sec/60);
      const s = Math.floor(sec%60);
      return `${m}:${String(s).padStart(2,"0")}`;
    }
  
    // Tracks
    const watchNowTrack = document.getElementById("watchNowTrack");
    const planningTrack = document.getElementById("planningTrack");
  
    // state: planning ids for toggle button
    const planningSet = new Set(); // key = `${media_type}:${tmdb_id}`
  
    function keyOf(media_type, tmdb_id){
      return `${media_type}:${tmdb_id}`;
    }
  
    function wideCardHTML(item){
      const title = esc(item.title || "Untitled");
      const poster = item.poster_url ? esc(item.poster_url) : "";
      const tmdbId = esc(item.tmdb_id);
      const mediaType = esc(item.media_type || "movie");
      const progress = Math.max(0, Math.min(100, Number(item.progress || 0)));
  
      // NOTE: time строку ты хранишь не в DB, поэтому делаем просто progress%
      return `
        <a class="cardWide" href="#"
           data-tmdb-id="${tmdbId}"
           data-media-type="${mediaType}"
           data-title="${title}"
           data-poster="${poster}">
          ${poster ? `<img src="${poster}" alt="${title}" loading="lazy">`
                   : `<div class="poster-placeholder">No image</div>`}
  
          <div>
            <div class="title">${title}</div>
            <div class="subtitle">${mediaType === "tv" ? "Series" : "Movie"}</div>
  
            <div class="metaRow">
              <div class="progressWrap" title="${progress}%">
                <div class="progressBar" style="width:${progress}%"></div>
              </div>
              <button class="badgeBtn" type="button"
                data-action="continue"
                data-tmdb-id="${tmdbId}"
                data-media-type="${mediaType}">
                Continue
              </button>
            </div>
  
            <div class="smallHint">Progress: ${progress}%</div>
          </div>
        </a>
      `;
    }
  
    function planCardHTML(item){
      const title = esc(item.title || "Untitled");
      const poster = item.poster_url ? esc(item.poster_url) : "";
      const tmdbId = esc(item.tmdb_id);
      const mediaType = esc(item.media_type || "movie");
  
      return `
        <a class="cardWide" href="#"
           data-tmdb-id="${tmdbId}"
           data-media-type="${mediaType}"
           data-title="${title}"
           data-poster="${poster}">
          ${poster ? `<img src="${poster}" alt="${title}" loading="lazy">`
                   : `<div class="poster-placeholder">No image</div>`}
  
          <div>
            <div class="title">${title}</div>
            <div class="subtitle">${mediaType === "tv" ? "Series" : "Movie"}</div>
  
            <div class="metaRow">
              <button class="badgeBtn" type="button"
                data-action="watch"
                data-tmdb-id="${tmdbId}"
                data-media-type="${mediaType}">
                Watch
              </button>
  
              <button class="badgeBtn" type="button"
                data-action="remove"
                data-tmdb-id="${tmdbId}"
                data-media-type="${mediaType}">
                Remove
              </button>
            </div>
  
            <div class="smallHint">Planning</div>
          </div>
        </a>
      `;
    }
  
    async function loadWatchingNow(){
      if(!watchNowTrack) return;
      watchNowTrack.innerHTML = `<div class="empty">Loading...</div>`;
      try{
        const d = await fetchJSON(`/api/continue_watching?limit=20`);
        const items = Array.isArray(d.items) ? d.items : [];
        watchNowTrack.innerHTML = items.length
          ? items.map(wideCardHTML).join("")
          : `<div class="empty">Nothing yet</div>`;
      }catch(e){
        console.error(e);
        watchNowTrack.innerHTML = `<div class="empty">Failed</div>`;
      }
    }
  
    async function loadPlanning(){
      if(!planningTrack) return;
      planningTrack.innerHTML = `<div class="empty">Loading...</div>`;
      try{
        const d = await fetchJSON(`/api/my_list?limit=60`);
        const items = Array.isArray(d.items) ? d.items : [];
  
        planningSet.clear();
        for(const it of items){
          planningSet.add(keyOf(it.media_type || "movie", it.tmdb_id));
        }
  
        planningTrack.innerHTML = items.length
          ? items.map(planCardHTML).join("")
          : `<div class="empty">Planning list is empty</div>`;
      }catch(e){
        console.error(e);
        planningTrack.innerHTML = `<div class="empty">Failed</div>`;
      }
    }
  
    // Modal (reuse как у тебя)
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
    const btnListToggle = document.getElementById("btnListToggle");
  
    let current = { tmdb_id: null, media_type: "movie", title: "", poster_url: "" };
  
    function openModal(){
      if(!mediaModal) return;
      mediaModal.classList.add("open");
      mediaModal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    }
    function closeModal(){
      if(!mediaModal) return;
      mediaModal.classList.remove("open");
      mediaModal.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
      if (mTrailer){ mTrailer.innerHTML=""; mTrailer.classList.add("hidden"); }
      if (mPoster) mPoster.classList.remove("hidden");
    }
    if(mediaBackdrop) mediaBackdrop.addEventListener("click", closeModal);
    if(mediaClose) mediaClose.addEventListener("click", closeModal);
    document.addEventListener("keydown", (e)=>{ if(e.key==="Escape") closeModal(); });
  
    async function openTrailerInline(tmdbId){
      try{
        const d = await fetchJSON(`/api/tmdb/trailer/${tmdbId}?lang=ru-RU`);
        if(!d.key) return alert("Trailer not found");
  
        if(mPoster) mPoster.classList.add("hidden");
        if(mTrailer){
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
      }catch(e){
        console.error(e);
        alert("Trailer not found");
      }
    }
  
    function refreshListToggle(){
      if(!btnListToggle) return;
      const k = keyOf(current.media_type, current.tmdb_id);
      const inList = planningSet.has(k);
      btnListToggle.textContent = inList ? "✓ In My List" : "＋ My List";
    }
  
    async function openMediaDetails(tmdbId, mediaType, titleFallback, posterUrl){
      current = { tmdb_id: Number(tmdbId), media_type: mediaType || "movie", title: titleFallback || "", poster_url: posterUrl || "" };
  
      if (mTrailer){ mTrailer.innerHTML=""; mTrailer.classList.add("hidden"); }
      if (mPoster){ mPoster.classList.remove("hidden"); mPoster.innerHTML=""; }
      if (mTitle) mTitle.textContent = "Loading...";
      if (mMeta) mMeta.textContent = "—";
      if (mDesc) mDesc.textContent = "—";
  
      openModal();
  
      try{
        const data = await fetchJSON(`/api/tmdb/details/${tmdbId}?lang=ru-RU`);
        const title = data.title || titleFallback || "Untitled";
        const year = data.release_date ? String(data.release_date).slice(0,4) : "";
        const genres = Array.isArray(data.genres) ? data.genres : [];
        const overview = data.overview || "No description.";
        const poster = data.poster_url || posterUrl || "";
  
        current.title = title;
        current.poster_url = poster;
  
        if(mTitle) mTitle.textContent = title;
        if(mMeta) mMeta.textContent = `${year ? year + " · " : ""}${genres.length ? genres.join(", ") : ""}`;
        if(mDesc) mDesc.textContent = overview;
  
        if(mPoster){
          mPoster.innerHTML = poster
            ? `<img src="${esc(poster)}" alt="${esc(title)}" loading="lazy">`
            : `<div class="poster-placeholder">No image</div>`;
        }
  
        if(btnWatch) btnWatch.onclick = () => (window.location.href = `/watch/${current.media_type}/${tmdbId}`);
        if(btnTrailer) btnTrailer.onclick = () => openTrailerInline(tmdbId);
  
        if(btnListToggle){
          refreshListToggle();
          btnListToggle.onclick = async () => {
            const k = keyOf(current.media_type, current.tmdb_id);
            const inList = planningSet.has(k);
  
            try{
              if(inList){
                await fetchJSON(`/api/my_list/remove`, {
                  method: "POST",
                  headers: { "Content-Type":"application/json", Accept:"application/json" },
                  body: JSON.stringify({ tmdb_id: current.tmdb_id, media_type: current.media_type })
                });
                planningSet.delete(k);
              }else{
                await fetchJSON(`/api/my_list/add`, {
                  method: "POST",
                  headers: { "Content-Type":"application/json", Accept:"application/json" },
                  body: JSON.stringify({
                    tmdb_id: current.tmdb_id,
                    media_type: current.media_type,
                    title: current.title,
                    poster_url: current.poster_url
                  })
                });
                planningSet.add(k);
              }
              refreshListToggle();
              await loadPlanning();
            }catch(e){
              console.error(e);
              alert("My List update failed");
            }
          };
        }
  
      }catch(e){
        console.error(e);
        if(mTitle) mTitle.textContent = titleFallback || "Failed to load";
        if(mDesc) mDesc.textContent = "Try again later.";
        refreshListToggle();
      }
    }
  
    // click handlers: card + buttons in card
    document.addEventListener("click", async (e) => {
      const actBtn = e.target.closest("button[data-action]");
      if(actBtn){
        e.preventDefault();
        const action = actBtn.getAttribute("data-action");
        const tmdbId = actBtn.getAttribute("data-tmdb-id");
        const mediaType = actBtn.getAttribute("data-media-type") || "movie";
  
        if(action === "continue" || action === "watch"){
          window.location.href = `/watch/${mediaType}/${tmdbId}`;
          return;
        }
        if(action === "remove"){
          try{
            await fetchJSON(`/api/my_list/remove`, {
              method:"POST",
              headers:{ "Content-Type":"application/json", Accept:"application/json" },
              body: JSON.stringify({ tmdb_id: Number(tmdbId), media_type: mediaType })
            });
            planningSet.delete(keyOf(mediaType, Number(tmdbId)));
            await loadPlanning();
          }catch(err){
            console.error(err);
            alert("Remove failed");
          }
          return;
        }
      }
  
      const card = e.target.closest("a.cardWide");
      if(!card) return;
  
      const tmdbId = card.getAttribute("data-tmdb-id");
      const mediaType = card.getAttribute("data-media-type") || "movie";
      const title = card.getAttribute("data-title") || "";
      const poster = card.getAttribute("data-poster") || "";
      if(!tmdbId) return;
  
      e.preventDefault();
      openMediaDetails(tmdbId, mediaType, title, poster);
    });
  
    // Topbar (search/notif/profile) — копия как у тебя
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
  
    function openSimpleModal(modal){
      if(!modal) return;
      modal.classList.add("open");
      modal.setAttribute("aria-hidden","false");
      document.body.style.overflow="hidden";
    }
    function closeSimpleModal(modal){
      if(!modal) return;
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden","true");
      document.body.style.overflow="";
    }
  
    if(btnSearch) btnSearch.onclick = ()=>{
      openSimpleModal(searchModal);
      if(searchInput){ searchInput.value=""; searchInput.focus(); }
      if(searchResults) searchResults.innerHTML="";
    };
    if(searchBackdrop) searchBackdrop.onclick = ()=>closeSimpleModal(searchModal);
    if(searchClose) searchClose.onclick = ()=>closeSimpleModal(searchModal);
  
    if(btnNotif) btnNotif.onclick = ()=>openSimpleModal(notifModal);
    if(notifBackdrop) notifBackdrop.onclick = ()=>closeSimpleModal(notifModal);
    if(notifClose) notifClose.onclick = ()=>closeSimpleModal(notifModal);
  
    if(btnProfile && profileMenu){
      btnProfile.onclick = (e)=>{
        e.preventDefault(); e.stopPropagation();
        profileMenu.classList.toggle("open");
      };
      document.addEventListener("click",(e)=>{
        if(!profileMenu.classList.contains("open")) return;
        const inside = e.target.closest("#profileMenu") || e.target.closest("#btnProfile");
        if(!inside) profileMenu.classList.remove("open");
      });
    }
  
    let searchTimer = null;
    async function doSearch(q){
      if(!searchResults) return;
      const query = (q||"").trim();
      if(query.length < 2){
        searchResults.innerHTML = `<div class="empty">Type 2+ chars</div>`;
        return;
      }
      try{
        const d = await fetchJSON(`/api/tmdb/search?q=${encodeURIComponent(query)}&lang=ru-RU`);
        const items = Array.isArray(d.results) ? d.results : [];
        // simple cards (как в movies): показываем, клики откроют modal (media_type из data-media-type)
        searchResults.innerHTML = items.length ? items.map((it)=>{
          const title = esc(it.title || "Untitled");
          const year = esc(it.year || "");
          const poster = it.poster_url ? esc(it.poster_url) : "";
          const mt = esc(it.media_type || "movie");
          return `
            <a class="card" href="#"
               data-tmdb-id="${esc(it.tmdb_id)}"
               data-media-type="${mt}">
              ${poster ? `<img src="${poster}" alt="${title}" loading="lazy">`
                       : `<div class="poster-placeholder">No image</div>`}
              <span>${title}${year ? " ("+year+")" : ""}</span>
            </a>
          `;
        }).join("") : `<div class="empty">No results</div>`;
      }catch(e){
        console.error(e);
        searchResults.innerHTML = `<div class="empty">Search failed</div>`;
      }
    }
  
    if(searchInput){
      searchInput.addEventListener("input", ()=>{
        clearTimeout(searchTimer);
        searchTimer = setTimeout(()=>doSearch(searchInput.value), 250);
      });
    }
  
    // init
    (async function init(){
      await loadWatchingNow();
      await loadPlanning();
    })();
  
  })();
  