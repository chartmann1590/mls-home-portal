const form = document.getElementById("searchForm");
const submitBtn = document.getElementById("submitBtn");
const saveSearchBtn = document.getElementById("saveSearchBtn");
const resultMeta = document.getElementById("resultMeta");
const listingGrid = document.getElementById("listingGrid");
const listingTemplate = document.getElementById("listingTemplate");
const savedSearchesEl = document.getElementById("savedSearches");
const savedListingsEl = document.getElementById("savedListings");

const modal = document.getElementById("listingModal");
const modalBackdrop = document.getElementById("modalBackdrop");
const modalClose = document.getElementById("modalClose");
const modalMainImage = document.getElementById("modalMainImage");
const thumbStrip = document.getElementById("thumbStrip");
const prevPhoto = document.getElementById("prevPhoto");
const nextPhoto = document.getElementById("nextPhoto");
const modalAddress = document.getElementById("modalAddress");
const modalPrice = document.getElementById("modalPrice");
const modalFacts = document.getElementById("modalFacts");
const modalFit = document.getElementById("modalFit");
const modalAiWhy = document.getElementById("modalAiWhy");
const modalDescription = document.getElementById("modalDescription");
const modalRealtor = document.getElementById("modalRealtor");
const modalListingLink = document.getElementById("modalListingLink");

let lastSearchData = null;
let activePhotos = [];
let activePhotoIndex = 0;

const money = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n || 0);

function currentPayloadFromForm() {
  const formData = new FormData(form);
  const payload = Object.fromEntries(formData.entries());
  ["max_price", "annual_income", "monthly_debt", "down_payment", "interest_rate", "loan_term_years"].forEach((k) => {
    payload[k] = Number(payload[k]);
  });
  return payload;
}

function applyPayloadToForm(payload) {
  Object.entries(payload).forEach(([k, v]) => {
    const input = form.elements.namedItem(k);
    if (input) input.value = String(v);
  });
}

function renderMeta(data) {
  const aff = data.ai_affordability;
  resultMeta.classList.remove("hidden");
  resultMeta.innerHTML = [
    ["Requested Cap", money(data.requested_max_price)],
    ["AI Affordable", money(aff.max_affordable_home_price)],
    ["Effective Cap", money(data.effective_price_cap)],
    ["Listings Found", String(data.listing_count)],
  ]
    .map(
      ([label, value]) => `
      <article class="stat">
        <p class="label">${label}</p>
        <p class="value">${value}</p>
      </article>
    `,
    )
    .join("");

  const note = document.createElement("article");
  note.className = "stat";
  note.style.gridColumn = "1 / -1";
  note.innerHTML = `<p class="label">AI Rationale</p><p>${aff.rationale}</p><p class="label">Notes: ${data.notes.join(" | ")}</p>`;
  resultMeta.appendChild(note);
}

function renderPhotos() {
  if (!activePhotos.length) {
    modalMainImage.src = "https://picsum.photos/seed/fallback-modal/1400/900";
    thumbStrip.innerHTML = "";
    return;
  }
  activePhotoIndex = Math.max(0, Math.min(activePhotoIndex, activePhotos.length - 1));
  modalMainImage.src = activePhotos[activePhotoIndex];
  thumbStrip.innerHTML = activePhotos
    .map(
      (url, i) =>
        `<img src="${url}" class="thumb ${i === activePhotoIndex ? "active" : ""}" data-idx="${i}" alt="photo ${i + 1}" />`,
    )
    .join("");
}

function openModal() {
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal() {
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

async function loadDetails(home, budgetContext = null) {
  const effectiveCap =
    budgetContext?.effective_price_cap || lastSearchData?.effective_price_cap || home.price;
  const monthlyLimit =
    budgetContext?.monthly_payment_limit || lastSearchData?.ai_affordability?.estimated_monthly_payment_limit || 0;

  modalAddress.textContent = `${home.address}, ${home.city || ""} ${home.state || ""}`.trim();
  modalPrice.textContent = money(home.price);
  modalFacts.textContent = `${home.beds ?? "?"} bd • ${home.baths ?? "?"} ba • ${home.sqft ?? "?"} sqft`;
  modalFit.textContent = home.ai_is_good_choice === true ? "Good Choice" : home.ai_is_good_choice === false ? "Use Caution" : "Fit: Unknown";
  modalAiWhy.textContent = home.ai_reason || home.ai_summary || "Assessing this property...";
  modalDescription.textContent = "Loading listing description...";
  modalRealtor.textContent = "Loading realtor info...";
  modalListingLink.href = home.listing_url || "#";

  activePhotos = [home.image_url].filter(Boolean);
  activePhotoIndex = 0;
  renderPhotos();
  openModal();

  if (!home.listing_url) {
    modalDescription.textContent = "No listing URL available for detailed scrape.";
    modalRealtor.textContent = "Not available.";
    return;
  }

  try {
    const res = await fetch("/api/listing-details", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        listing_url: home.listing_url,
        address: home.address,
        city: home.city || "",
        state: home.state || "",
        price: home.price,
        beds: home.beds,
        baths: home.baths,
        sqft: home.sqft,
        effective_price_cap: effectiveCap,
        monthly_payment_limit: monthlyLimit,
        ai_reason: home.ai_reason || null,
        broker_name: home.broker_name || null,
      }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const detail = await res.json();

    activePhotos = (detail.photos || []).length ? detail.photos : [home.image_url].filter(Boolean);
    activePhotoIndex = 0;
    renderPhotos();

    modalDescription.textContent = detail.description || "No listing description found.";
    const r = detail.realtor || {};
    modalRealtor.textContent = [
      r.broker_name && `Broker: ${r.broker_name}`,
      r.agent_name && `Agent: ${r.agent_name}`,
      r.agent_phone && `Phone: ${r.agent_phone}`,
      r.agent_email && `Email: ${r.agent_email}`,
      r.mls_name && `MLS: ${r.mls_name}${r.mls_id ? ` (${r.mls_id})` : ""}`,
    ]
      .filter(Boolean)
      .join(" | ") || (home.broker_name ? `Broker: ${home.broker_name}` : "Not available.");

    modalFit.textContent = detail.ai_is_good_choice === true ? "Good Choice" : detail.ai_is_good_choice === false ? "Use Caution" : "Fit: Unknown";
    modalAiWhy.textContent = detail.ai_explanation || home.ai_reason || home.ai_summary || "No detailed AI explanation available.";
    modalListingLink.href = detail.listing_url || home.listing_url;
  } catch (err) {
    modalDescription.textContent = `Could not load details: ${err.message}`;
    modalRealtor.textContent = "Not available.";
  }
}

async function saveListing(home) {
  const effectiveCap = lastSearchData?.effective_price_cap || null;
  const monthlyLimit = lastSearchData?.ai_affordability?.estimated_monthly_payment_limit || null;
  const res = await fetch("/api/saved-listings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      listing: home,
      effective_price_cap: effectiveCap,
      monthly_payment_limit: monthlyLimit,
    }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  await loadSavedListings();
}

function renderListings(data) {
  listingGrid.innerHTML = "";
  data.listings.forEach((home) => {
    const node = listingTemplate.content.cloneNode(true);
    node.querySelector(".home-img").src = home.image_url || "https://picsum.photos/seed/fallback/900/600";
    node.querySelector(".price").textContent = money(home.price);
    node.querySelector(".address").textContent = `${home.address}, ${home.city || ""} ${home.state || ""}`.trim();
    const bd = home.beds ?? "?";
    const ba = home.baths ?? "?";
    const sqft = home.sqft ?? "?";
    node.querySelector(".facts").textContent = `${bd} bd • ${ba} ba • ${sqft} sqft`;
    const badge = node.querySelector(".fit-badge");
    const good = home.ai_is_good_choice === true;
    badge.textContent = home.ai_is_good_choice === null || home.ai_is_good_choice === undefined ? "Fit: Unknown" : good ? "Good Choice" : "Use Caution";
    badge.classList.add(good ? "good" : "bad");
    node.querySelector(".summary").textContent = home.ai_summary || home.ai_reason || "No AI summary available for this home.";

    const saveBtn = node.querySelector(".save-home-btn");
    saveBtn.addEventListener("click", async () => {
      saveBtn.disabled = true;
      try {
        await saveListing(home);
        saveBtn.textContent = "Saved";
      } catch (err) {
        alert(`Save failed: ${err.message}`);
      } finally {
        saveBtn.disabled = false;
      }
    });

    const detailsBtn = node.querySelector(".details-btn");
    detailsBtn.addEventListener("click", () => loadDetails(home));

    const link = node.querySelector(".cta");
    link.href = home.listing_url || "#";
    link.textContent = home.listing_url ? "View Listing" : "No listing URL";
    if (!home.listing_url) link.style.opacity = "0.5";
    listingGrid.appendChild(node);
  });

  if (!data.listings.length) {
    listingGrid.innerHTML = `<article class="card"><div class="card-body"><h3>No homes found</h3><p>Try a larger area or higher max cost.</p></div></article>`;
  }
}

async function runSearch(payload) {
  const res = await fetch("/api/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `HTTP ${res.status}`);
  }
  const data = await res.json();
  lastSearchData = data;
  renderMeta(data);
  renderListings(data);
}

function renderSavedSearches(items) {
  if (!items.length) {
    savedSearchesEl.innerHTML = `<p class="empty-state">No saved searches yet.</p>`;
    return;
  }

  savedSearchesEl.innerHTML = items
    .map(
      (item) => `
        <article class="saved-item" data-id="${item.id}">
          <p class="saved-title">${item.name}</p>
          <p class="saved-sub">${item.criteria.area} • cap ${money(item.criteria.max_price)} • ${item.criteria.provider}</p>
          <div class="saved-actions">
            <button type="button" class="run-saved-btn">Run</button>
            <button type="button" class="delete-saved-btn secondary-btn">Delete</button>
          </div>
        </article>
      `,
    )
    .join("");

  savedSearchesEl.querySelectorAll(".run-saved-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const root = e.target.closest(".saved-item");
      const id = Number(root.getAttribute("data-id"));
      btn.disabled = true;
      btn.textContent = "Running...";
      try {
        const res = await fetch(`/api/saved-searches/${id}/run`, { method: "POST" });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        const picked = items.find((x) => x.id === id);
        if (picked) applyPayloadToForm(picked.criteria);
        lastSearchData = data;
        renderMeta(data);
        renderListings(data);
      } catch (err) {
        alert(`Run failed: ${err.message}`);
      } finally {
        btn.disabled = false;
        btn.textContent = "Run";
      }
    });
  });

  savedSearchesEl.querySelectorAll(".delete-saved-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const root = e.target.closest(".saved-item");
      const id = Number(root.getAttribute("data-id"));
      try {
        const res = await fetch(`/api/saved-searches/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error(await res.text());
        await loadSavedSearches();
      } catch (err) {
        alert(`Delete failed: ${err.message}`);
      }
    });
  });
}

function renderSavedListings(items) {
  if (!items.length) {
    savedListingsEl.innerHTML = `<p class="empty-state">No saved homes yet.</p>`;
    return;
  }

  savedListingsEl.innerHTML = items
    .map(
      (item) => `
        <article class="saved-item" data-id="${item.id}">
          <p class="saved-title">${money(item.listing.price)} • ${item.listing.address}</p>
          <p class="saved-sub">${item.listing.beds ?? "?"} bd • ${item.listing.baths ?? "?"} ba • ${item.listing.sqft ?? "?"} sqft</p>
          <div class="saved-actions">
            <button type="button" class="open-saved-home-btn">Details</button>
            <a class="cta" href="${item.listing.listing_url || "#"}" target="_blank" rel="noopener noreferrer">Open Listing</a>
            <button type="button" class="delete-saved-home-btn secondary-btn">Delete</button>
          </div>
        </article>
      `,
    )
    .join("");

  savedListingsEl.querySelectorAll(".open-saved-home-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const root = e.target.closest(".saved-item");
      const id = Number(root.getAttribute("data-id"));
      const item = items.find((x) => x.id === id);
      if (!item) return;
      loadDetails(item.listing, {
        effective_price_cap: item.effective_price_cap,
        monthly_payment_limit: item.monthly_payment_limit,
      });
    });
  });

  savedListingsEl.querySelectorAll(".delete-saved-home-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const root = e.target.closest(".saved-item");
      const id = Number(root.getAttribute("data-id"));
      try {
        const res = await fetch(`/api/saved-listings/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error(await res.text());
        await loadSavedListings();
      } catch (err) {
        alert(`Delete failed: ${err.message}`);
      }
    });
  });
}

async function loadSavedSearches() {
  try {
    const res = await fetch("/api/saved-searches");
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    renderSavedSearches(data.items || []);
  } catch (err) {
    savedSearchesEl.innerHTML = `<p class="empty-state">Could not load saved searches: ${err.message}</p>`;
  }
}

async function loadSavedListings() {
  try {
    const res = await fetch("/api/saved-listings");
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    renderSavedListings(data.items || []);
  } catch (err) {
    savedListingsEl.innerHTML = `<p class="empty-state">Could not load saved homes: ${err.message}</p>`;
  }
}

thumbStrip.addEventListener("click", (e) => {
  const target = e.target;
  if (!(target instanceof HTMLElement)) return;
  const idx = target.getAttribute("data-idx");
  if (idx === null) return;
  activePhotoIndex = Number(idx);
  renderPhotos();
});

prevPhoto.addEventListener("click", () => {
  if (!activePhotos.length) return;
  activePhotoIndex = (activePhotoIndex - 1 + activePhotos.length) % activePhotos.length;
  renderPhotos();
});

nextPhoto.addEventListener("click", () => {
  if (!activePhotos.length) return;
  activePhotoIndex = (activePhotoIndex + 1) % activePhotos.length;
  renderPhotos();
});

modalBackdrop.addEventListener("click", closeModal);
modalClose.addEventListener("click", closeModal);

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modal.classList.contains("hidden")) {
    closeModal();
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  submitBtn.disabled = true;
  submitBtn.textContent = "Searching...";

  try {
    await runSearch(currentPayloadFromForm());
  } catch (err) {
    resultMeta.classList.remove("hidden");
    resultMeta.innerHTML = `<article class="stat" style="grid-column:1/-1"><p class="label">Error</p><p>${err.message}</p></article>`;
    listingGrid.innerHTML = "";
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Run AI Home Search";
  }
});

saveSearchBtn.addEventListener("click", async () => {
  const payload = currentPayloadFromForm();
  const defaultName = `${payload.area} up to ${money(payload.max_price)}`;
  const name = window.prompt("Name this search", defaultName);
  if (name === null) return;

  saveSearchBtn.disabled = true;
  try {
    const res = await fetch("/api/saved-searches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, criteria: payload }),
    });
    if (!res.ok) throw new Error(await res.text());
    await loadSavedSearches();
  } catch (err) {
    alert(`Save search failed: ${err.message}`);
  } finally {
    saveSearchBtn.disabled = false;
  }
});

loadSavedSearches();
loadSavedListings();
