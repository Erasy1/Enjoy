(function () {
    "use strict";
  
    // helpers 
    const esc = (s) =>
      String(s ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
  
    async function fetchJSON(url, opts) {
      const r = await fetch(url, { headers: { Accept: "application/json" }, ...opts });
      if (!r.ok) {
        let msg = "HTTP " + r.status;
        try {
          const j = await r.json();
          if (j && j.error) msg = j.error;
        } catch (_) {}
        throw new Error(msg);
      }
      return r.json();
    }
  
    //  modal refs 
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
    const btnArchive = document.getElementById("btnArchive");
  
    if (!mediaModal) return; 
  
    let currentItem = null; 
    function openModal() {
      mediaModal.classList.add("open");
      mediaModal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
    }
  
    function closeModal() {
      mediaModal.classList.remove("open");
      mediaModal.setAttribute("aria-hidden", "true");
      document.body.style.overflow = "";
  
      if (mTrailer) {
        mTrailer.innerHTML = "";
        mTrailer.classList.add("hidden");
      }
      if (mPoster) mPoster.classList.remove("hidden");
  
      if (btnArchive) btnArchive.textContent = "📌 Archive";
      currentItem = null;
    }
  
    if (mediaBackdrop) mediaBackdrop.addEventListener("click", closeModal);
    if (mediaClose) mediaClose.addEventListener("click", closeModal);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });
  
    async function openTrailerInline(tmdbId) {
      try {
        const d = await fetchJSON(`/api/tmdb/trailer/${tmdbId}?lang=ru-RU&type=${encodeURIComponent(currentItem?.media_type || "movie")}`);
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
      // reset UI
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
      if (btnArchive) btnArchive.textContent = "📌 Archive";
  
      openModal();
  
      try {
        const data = await fetchJSON(`/api/tmdb/details/${tmdbId}?lang=ru-RU&type=${encodeURIComponent(mediaType)}`);
  
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
  
        currentItem = {
          tmdb_id: Number(tmdbId),
          media_type: mediaType || "movie",
          title,
          poster_url: poster || null,
        };
  
        if (btnWatch) btnWatch.onclick = () => (window.location.href = `/watch/${currentItem.media_type}/${tmdbId}`);
        if (btnTrailer) btnTrailer.onclick = () => openTrailerInline(tmdbId);
  
        if (btnArchive) {
          btnArchive.onclick = async () => {
            try {
              const resp = await fetchJSON("/api/my_list/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(currentItem),
              });
  
              if (resp && resp.ok) {
                btnArchive.textContent = "✅ Added";
                setTimeout(() => (btnArchive.textContent = "📌 Archive"), 1200);
              }
            } catch (e) {
              console.error("archive error:", e);
              alert("Failed to add to My List");
            }
          };
        }
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
  
      const mediaType = a.getAttribute("data-media-type") || "movie";
      const titleText = a.querySelector("span") ? a.querySelector("span").textContent : "";
  
      e.preventDefault();
      openMediaDetails(tmdbId, mediaType, titleText);
    });
  })();
  
