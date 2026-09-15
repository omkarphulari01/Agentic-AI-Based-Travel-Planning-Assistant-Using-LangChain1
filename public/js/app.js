/**
 * TRIP PLANER - Dual Interface Client Controller (Mobile Software + Desktop Website)
 * Handles trip planning requests, Leaflet interactive map, 1-click booking,
 * client-side .ics calendar generation, PDF printing, PWA installation & mobile tabs.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const tripForm = document.getElementById('tripForm');
  const submitBtn = document.getElementById('submitBtn');
  const btnText = submitBtn.querySelector('.btn-text');
  const btnLoader = submitBtn.querySelector('.btn-loader');

  const emptyState = document.getElementById('emptyState');
  const loadingState = document.getElementById('loadingState');
  const resultsContent = document.getElementById('resultsContent');

  const tripMetaTags = document.getElementById('tripMetaTags');
  const bookingLinksGrid = document.getElementById('bookingLinksGrid');
  const itineraryOutput = document.getElementById('itineraryOutput');

  const downloadPdfBtn = document.getElementById('downloadPdfBtn');
  const downloadIcsBtn = document.getElementById('downloadIcsBtn');
  const copyMarkdownBtn = document.getElementById('copyMarkdownBtn');

  const startDateInput = document.getElementById('startDate');
  const endDateInput = document.getElementById('endDate');
  const installAppBtn = document.getElementById('installAppBtn');

  let currentPlanData = null;
  let leafletMap = null;
  let mapLayers = [];
  let deferredPrompt = null;

  // 1. PWA Service Worker Registration & Installation Prompt
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js').then(
        (reg) => console.log('ServiceWorker registered with scope: ', reg.scope),
        (err) => console.log('ServiceWorker registration failed: ', err)
      );
    });
  }

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (installAppBtn) {
      installAppBtn.style.display = 'inline-flex';
    }
  });

  if (installAppBtn) {
    installAppBtn.addEventListener('click', async () => {
      if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`User response to the install prompt: ${outcome}`);
        deferredPrompt = null;
        installAppBtn.style.display = 'none';
      } else {
        alert('To install on iOS: Tap the Share button in Safari and select "Add to Home Screen".');
      }
    });
  }

  // 2. Mobile Tab Switching Navigation
  function switchMobileTab(targetTabId) {
    // Update all tab buttons (top & bottom bar)
    document.querySelectorAll('.m-tab-btn, .mobile-bottom-nav .nav-item').forEach((btn) => {
      if (btn.dataset.tab === targetTabId) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update active tab pane
    document.querySelectorAll('.app-tab-pane').forEach((pane) => {
      if (pane.id === targetTabId) {
        pane.classList.add('active');
      } else {
        pane.classList.remove('active');
      }
    });

    // If switching to Map tab, invalidate Leaflet map size
    if (targetTabId === 'tab-map' && leafletMap) {
      setTimeout(() => {
        leafletMap.invalidateSize();
      }, 150);
    }
  }

  // Attach tab click listeners to both top and bottom mobile navigation bars
  document.querySelectorAll('.m-tab-btn, .mobile-bottom-nav .nav-item').forEach((btn) => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      if (tabId) {
        switchMobileTab(tabId);
      }
    });
  });

  // 3. Initialize Default Dates (Tomorrow + 7 days)
  const today = new Date();
  const startDefault = new Date(today);
  startDefault.setDate(today.getDate() + 7);
  const endDefault = new Date(startDefault);
  endDefault.setDate(startDefault.getDate() + 3);

  startDateInput.value = startDefault.toISOString().split('T')[0];
  endDateInput.value = endDefault.toISOString().split('T')[0];

  // 4. Quick Starter Presets
  document.querySelectorAll('.preset-pill').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.getElementById('origin').value = btn.dataset.origin;
      document.getElementById('destination').value = btn.dataset.dest;
      document.getElementById('budget').value = btn.dataset.budget;

      const days = parseInt(btn.dataset.days || '3', 10);
      const newEnd = new Date(startDateInput.value);
      newEnd.setDate(newEnd.getDate() + days);
      endDateInput.value = newEnd.toISOString().split('T')[0];
    });
  });

  // 5. Form Submission
  tripForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const origin = document.getElementById('origin').value.trim();
    const destination = document.getElementById('destination').value.trim();
    const startDate = startDateInput.value;
    const endDate = endDateInput.value;
    const budget = parseInt(document.getElementById('budget').value, 10);
    const travelers = parseInt(document.getElementById('travelers').value, 10);
    const transportMode = document.querySelector('input[name="transportMode"]:checked').value;
    const interests = document.getElementById('interests').value.trim();

    if (!origin || !destination || !startDate || !endDate) {
      alert('Please fill out all required fields.');
      return;
    }

    // Enter Loading State
    setLoading(true);
    startProgressAnimation();

    const payload = {
      origin,
      destination,
      start_date: startDate,
      end_date: endDate,
      budget,
      travelers,
      transport_mode: transportMode,
      interests,
    };

    try {
      let res;
      try {
        res = await fetch('/api/plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } catch (networkErr) {
        res = await fetch('/.netlify/functions/plan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.error || `Server responded with status ${res.status}`);
      }

      const data = await res.json();
      currentPlanData = data;
      renderResults(data, payload);

      // On mobile, automatically switch to Itinerary or Map tab after successful generation
      if (window.innerWidth <= 768) {
        switchMobileTab('tab-itinerary');
      }
    } catch (err) {
      console.error('Plan generation failed:', err);
      alert(`Could not generate itinerary: ${err.message}\n\nPlease check serverless function logs.`);
      showEmptyState();
    } finally {
      setLoading(false);
    }
  });

  // 6. Render Results
  function renderResults(data, requestPayload) {
    emptyState.style.display = 'none';
    loadingState.style.display = 'none';
    resultsContent.style.display = 'block';

    // A. Meta Chips
    tripMetaTags.innerHTML = `
      <span class="meta-chip"><i class="fa-solid fa-route text-emerald"></i> ${requestPayload.origin} → ${requestPayload.destination}</span>
      <span class="meta-chip"><i class="fa-regular fa-calendar"></i> ${requestPayload.start_date} to ${requestPayload.end_date}</span>
      <span class="meta-chip"><i class="fa-solid fa-indian-rupee-sign text-amber"></i> ₹${requestPayload.budget.toLocaleString('en-IN')}</span>
      <span class="meta-chip"><i class="fa-solid fa-users text-cyan"></i> ${requestPayload.travelers} Guest(s)</span>
      <span class="meta-chip"><i class="fa-solid fa-train-subway text-indigo"></i> ${requestPayload.transport_mode}</span>
    `;

    // B. 1-Click Booking Shortcuts
    renderBookingShortcuts(data.booking_links);

    // C. Render Leaflet Map
    renderMap(data.map_data, requestPayload);

    // D. Stream / Parse Markdown
    streamItineraryMarkdown(data.itinerary);
  }

  // Render 1-Click Booking Links
  function renderBookingShortcuts(linksObj) {
    bookingLinksGrid.innerHTML = '';
    if (!linksObj) return;

    const iconMap = {
      Flights: 'fa-solid fa-plane text-emerald',
      Hotels: 'fa-solid fa-hotel text-cyan',
      Trains: 'fa-solid fa-train text-indigo',
      Buses: 'fa-solid fa-bus text-amber',
    };

    Object.entries(linksObj).forEach(([category, links]) => {
      links.forEach((item) => {
        const a = document.createElement('a');
        a.href = item.url;
        a.target = '_blank';
        a.rel = 'noopener noreferrer';
        a.className = 'booking-link-pill';
        const iconClass = iconMap[category] || 'fa-solid fa-arrow-up-right-from-square';
        a.innerHTML = `<i class="${iconClass}"></i> ${item.label}`;
        bookingLinksGrid.appendChild(a);
      });
    });
  }

  // Render Leaflet Map
  function renderMap(mapData, requestPayload) {
    const mapContainer = document.getElementById('leafletMap');
    if (!mapContainer) return;

    if (!leafletMap) {
      leafletMap = L.map('leafletMap', {
        zoomControl: true,
        attributionControl: true,
      });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '© OpenStreetMap',
      }).addTo(leafletMap);
    }

    // Clear previous markers
    mapLayers.forEach((l) => leafletMap.removeLayer(l));
    mapLayers = [];

    const origin = mapData.origin || { lat: 28.6139, lon: 77.2090, name: requestPayload.origin };
    const dest = mapData.destination || { lat: 15.2993, lon: 74.1240, name: requestPayload.destination };

    const createCustomIcon = (color, faIcon) => {
      return L.divIcon({
        className: 'custom-leaflet-marker',
        html: `<div style="background: ${color}; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 14px; box-shadow: 0 0 10px ${color}; border: 2px solid #fff;"><i class="${faIcon}"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });
    };

    // 1. Origin Marker
    const originMarker = L.marker([origin.lat, origin.lon], {
      icon: createCustomIcon('#10b981', 'fa-solid fa-plane-departure'),
    }).bindPopup(`<b>🛫 Departure Origin:</b><br>${origin.name}`);
    originMarker.addTo(leafletMap);
    mapLayers.push(originMarker);

    // 2. Destination Marker
    const destMarker = L.marker([dest.lat, dest.lon], {
      icon: createCustomIcon('#ef4444', 'fa-solid fa-flag-checkered'),
    }).bindPopup(`<b>🎯 Destination:</b><br>${dest.name}`);
    destMarker.addTo(leafletMap);
    mapLayers.push(destMarker);

    // 3. Route Line
    const routeLine = L.polyline(
      [[origin.lat, origin.lon], [dest.lat, dest.lon]],
      { color: '#6366f1', weight: 3.5, dashArray: '6, 8', opacity: 0.85 }
    ).addTo(leafletMap);
    mapLayers.push(routeLine);

    // 4. Hotel Marker
    if (mapData.hotel) {
      const hotelMarker = L.marker([mapData.hotel.lat, mapData.hotel.lon], {
        icon: createCustomIcon('#3b82f6', 'fa-solid fa-bed'),
      }).bindPopup(`<b>🏨 Recommended Stay:</b><br>${mapData.hotel.name}`);
      hotelMarker.addTo(leafletMap);
      mapLayers.push(hotelMarker);
    }

    // 5. Sightseeing Attractions Pins
    if (mapData.attractions && Array.isArray(mapData.attractions)) {
      mapData.attractions.forEach((spot) => {
        const spotMarker = L.marker([spot.lat, spot.lon], {
          icon: createCustomIcon('#f59e0b', 'fa-solid fa-location-dot'),
        }).bindPopup(`<b>📍 ${spot.day || 'Day Activity'}</b><br><strong>${spot.name}</strong><br><small>${spot.detail || ''}</small>`);
        spotMarker.addTo(leafletMap);
        mapLayers.push(spotMarker);
      });
    }

    // Fit map bounds
    const bounds = L.latLngBounds([[origin.lat, origin.lon], [dest.lat, dest.lon]]);
    leafletMap.fitBounds(bounds, { padding: [40, 40] });

    setTimeout(() => {
      leafletMap.invalidateSize();
    }, 200);
  }

  // Markdown Streaming & Parsing
  function streamItineraryMarkdown(fullText) {
    if (typeof marked !== 'undefined') {
      itineraryOutput.innerHTML = marked.parse(fullText);
    } else {
      itineraryOutput.innerText = fullText;
    }
  }

  // Progress Animation Steps
  let animTimer = null;
  function startProgressAnimation() {
    const steps = [
      document.getElementById('step1'),
      document.getElementById('step2'),
      document.getElementById('step3'),
      document.getElementById('step4'),
    ];
    steps.forEach((s) => {
      s.className = 'loading-step';
      s.querySelector('i').className = 'fa-regular fa-circle';
    });

    let current = 0;
    if (steps[0]) {
      steps[0].classList.add('active');
      steps[0].querySelector('i').className = 'fa-solid fa-spinner fa-spin';
    }

    clearInterval(animTimer);
    animTimer = setInterval(() => {
      if (current < steps.length) {
        steps[current].className = 'loading-step done';
        steps[current].querySelector('i').className = 'fa-solid fa-circle-check';
        current++;
        if (current < steps.length) {
          steps[current].classList.add('active');
          steps[current].querySelector('i').className = 'fa-solid fa-spinner fa-spin';
        }
      }
    }, 2500);
  }

  function setLoading(isLoading) {
    if (isLoading) {
      submitBtn.disabled = true;
      btnText.style.display = 'none';
      btnLoader.style.display = 'inline-block';
      emptyState.style.display = 'none';
      resultsContent.style.display = 'none';
      loadingState.style.display = 'flex';
    } else {
      submitBtn.disabled = false;
      btnText.style.display = 'inline-block';
      btnLoader.style.display = 'none';
      clearInterval(animTimer);
    }
  }

  function showEmptyState() {
    emptyState.style.display = 'flex';
    loadingState.style.display = 'none';
    resultsContent.style.display = 'none';
  }

  // Action Button Listeners
  downloadPdfBtn.addEventListener('click', () => {
    window.print();
  });

  downloadIcsBtn.addEventListener('click', () => {
    if (!currentPlanData) return;
    const req = currentPlanData.trip_summary || {};
    const dest = req.destination || 'Destination';
    const startStr = (req.start_date || '2026-03-15').replace(/-/g, '');
    const endStr = (req.end_date || '2026-03-18').replace(/-/g, '');

    const icsContent = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//TRIP PLANER//EN',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'BEGIN:VEVENT',
      `UID:tripplaner-trip-${Date.now()}@tripplaner.com`,
      `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, '').split('.')[0]}Z`,
      `DTSTART;VALUE=DATE:${startStr}`,
      `DTEND;VALUE=DATE:${endStr}`,
      `SUMMARY:✈️ Trip to ${dest}`,
      `DESCRIPTION:AI planned trip with TRIP PLANER.\\nBudget: ₹${req.budget || 25000}\\nTransport: ${req.transport_mode || 'All'}`,
      `LOCATION:${dest}`,
      'STATUS:CONFIRMED',
      'END:VEVENT',
      'END:VCALENDAR',
    ].join('\r\n');

    const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
    const link = document.createElement('a');
    link.href = window.URL.createObjectURL(blob);
    link.setAttribute('download', `${dest.toLowerCase()}_trip_schedule.ics`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });

  copyMarkdownBtn.addEventListener('click', () => {
    if (!currentPlanData || !currentPlanData.itinerary) return;
    navigator.clipboard.writeText(currentPlanData.itinerary).then(() => {
      copyMarkdownBtn.innerHTML = '<i class="fa-solid fa-check text-emerald"></i> Copied!';
      setTimeout(() => {
        copyMarkdownBtn.innerHTML = '<i class="fa-regular fa-copy"></i> Copy';
      }, 2000);
    });
  });
});
