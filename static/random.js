document.addEventListener("DOMContentLoaded", function () {
    const btn = document.getElementById("randomDayBtn");
    const moreBtn = document.getElementById("randomDayMore");
    const card = document.getElementById("randomDayCard");
    const poster = document.getElementById("randomDayPoster");
    const nameEl = document.getElementById("randomDayName");
    const badge = document.getElementById("randomDayBadge");
    const dateEl = document.getElementById("randomDayDate");
    const voteEl = document.getElementById("randomDayVote");
    const overviewEl = document.getElementById("randomDayOverview");
    const overlay = document.getElementById("rdmOverlay");
    const closeBtn = document.getElementById("rdmClose");
    const mPoster = document.getElementById("rdmPoster");
    const mTitle = document.getElementById("rdmTitle");
    const mMeta = document.getElementById("rdmMeta");
    const mOverview = document.getElementById("rdmOverview");
    const watchBtn = document.getElementById("rdmWatchBtn");
    const trailerBtn = document.getElementById("rdmTrailerBtn");
    const archiveBtn = document.getElementById("rdmArchiveBtn");
    const trailerContainer = document.getElementById("rdmTrailerContainer");
    const trailerFrame = document.getElementById("rdmTrailerFrame");
  
    if (!btn) return;
  
    let lastRandomData = null;
  
    function safe(v, fb = "—") {
      return (v == null || String(v).trim() === "") ? fb : String(v);
    }
  
    function year(d) {
      if (!d) return "";
      const y = String(d).slice(0, 4);
      return /^\d{4}$/.test(y) ? y : "";
    }
  
    
    async function loadRandom() {
      btn.disabled = true;
      const old = btn.textContent;
      btn.textContent = "Loading...";
  
      try {
        const res = await fetch("/api/random");
        if (!res.ok) throw new Error("GET /api/random -> " + res.status);
  
        const data = await res.json();
        lastRandomData = data;
  
        if (data.poster_url) {
          poster.src = data.poster_url;
          poster.style.display = "block";
        } else {
          poster.removeAttribute("src");
          poster.style.display = "none";
        }
  
        nameEl.textContent = safe(data.title, "Untitled");
        badge.textContent = (data.media_type === "tv") ? "TV" : "Movie";
        dateEl.textContent = safe(data.date, "");
        voteEl.textContent = "⭐ " + Number(data.vote || 0).toFixed(1);
        overviewEl.textContent = safe(data.overview, "No overview.");
  
        card.classList.remove("hidden");
  
      } catch (e) {
        console.error(e);
        alert("Could not load random title.");
      } finally {
        btn.disabled = false;
        btn.textContent = old;
      }
    }
  
    function openModal() {
      if (!lastRandomData) {
        alert("First click Get random.");
        return;
      }
  
      const d = lastRandomData;
  
      mPoster.src = d.poster_url || "";
      mTitle.textContent = safe(d.title, "Untitled");
  
      const typeLabel = (d.media_type === "tv") ? "TV Series" : "Movie";
      const rating = Number(d.vote || 0).toFixed(1);
  
      mMeta.textContent = [
        year(d.date),
        typeLabel,
        `⭐ ${rating}`
      ].filter(Boolean).join(" · ");
  
      mOverview.textContent = safe(d.overview, "No overview.");
  
      overlay.classList.remove("hidden");
      document.body.style.overflow = "hidden";
    }
  
    function closeModal() {
      overlay.classList.add("hidden");
      document.body.style.overflow = "";
  
      if (trailerFrame) trailerFrame.src = "";
      if (trailerContainer) trailerContainer.classList.add("hidden");
    }
  
    
    watchBtn && watchBtn.addEventListener("click", () => {
      if (!lastRandomData) return;
  
      const d = lastRandomData;
      closeModal();
  
      window.location.href = `/watch/${d.media_type}/${d.id}`;
    });
  
    
    trailerBtn && trailerBtn.addEventListener("click", async () => {
      if (!lastRandomData) return;
  
      const d = lastRandomData;
  
      try {
        const res = await fetch(`/api/trailer/${d.media_type}/${d.id}`);
        if (!res.ok) throw new Error();
  
        const t = await res.json();
  
        if (t.ok && t.url) {
          const videoId = new URL(t.url).searchParams.get("v");
  
          trailerFrame.src = `https://www.youtube.com/embed/${videoId}?autoplay=1`;
          trailerContainer.classList.remove("hidden");
        } else {
          alert("Trailer not found.");
        }
  
      } catch (e) {
        alert("Could not load trailer.");
      }
    });
  
    
archiveBtn && archiveBtn.addEventListener("click", async () => {
  if (!lastRandomData) return;

  const d = lastRandomData;

  try {
    const res = await fetch("/api/my_list/add", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({
        tmdb_id: d.id,
        media_type: d.media_type === "tv" ? "tv" : "movie",
        title: d.title,
        poster_url: d.poster_url
      })
    });

    if (!res.ok) {
      const txt = await res.text();
      throw new Error("API error: " + res.status + " " + txt);
    }

    alert("Added to My List ✅");
  } catch (e) {
    console.error(e);
    alert("Failed to add to My List ❌");
  }
});

  
    
    btn.addEventListener("click", loadRandom);
    moreBtn && moreBtn.addEventListener("click", openModal);
    closeBtn && closeBtn.addEventListener("click", closeModal);
  
    overlay && overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal();
    });
  
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && overlay && !overlay.classList.contains("hidden")) {
        closeModal();
      }
    });
  
  });
  