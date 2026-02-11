class WasteCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    set hass(hass) {
        this._hass = hass;

        // Initialize card content if not exists
        if (!this.content) {
            const card = document.createElement('ha-card');
            this.content = document.createElement('div');
            this.content.className = 'waste-card-content';
            this.content.style.padding = '16px';
            this.content.style.textAlign = 'center';
            card.appendChild(this.content);
            this.shadowRoot.appendChild(card);
        }

        const entityId = this.config.entity;
        const state = hass.states[entityId];

        if (!state) {
            this.content.innerHTML = `
                <div class="card-content">
                    <div class="entity-not-found">Entity not found: ${entityId}</div>
                </div>
            `;
            return;
        }

        try {
            const attributes = state.attributes;
            const wasteType = attributes.waste_type || "default";
            const wasteTypes = attributes.waste_types || [];
            const daysUntil = attributes.days_until;
            const upcomingSchedule = attributes.upcoming_schedule || [];
            const collectionStart = attributes.collection_start;
            const collectionEnd = attributes.collection_end;

            // Time window string
            let timeString = "";
            if (collectionStart && collectionEnd) {
                timeString = `Esporre dalle ${collectionStart} alle ${collectionEnd}`;
            } else if (collectionStart) {
                timeString = `Esporre dalle ${collectionStart}`;
            }

            const wasteIcons = attributes.waste_icons || {};
            const wasteColors = attributes.waste_colors || {};

            // Helper to get icon
            const getIcon = (type) => {
                if (!type) return "default.png";
                if (wasteIcons[type]) {
                    return wasteIcons[type];
                }
                const typeLower = type.toLowerCase();
                if (typeLower.includes("plastica")) return "plastica.png";
                if (typeLower.includes("carta")) return "carta.png";
                if (typeLower.includes("umido")) return "umido.png";
                if (typeLower.includes("vetro")) return "vetro.png";
                if (typeLower.includes("indifferenziata") || typeLower.includes("secco")) return "indifferenziata.png";
                if (typeLower.includes("metallo")) return "metallo.png";
                if (typeLower.includes("verde") || typeLower.includes("sfalci")) return "verde.png";
                return "default.png";
            };

            // Determine main image and color
            let mainImage = "default.png";
            let mainColor = "transparent";
            let mainTextColor = "var(--primary-text-color)";

            if (wasteType) {
                const mainType = (wasteTypes.length > 0) ? wasteTypes[0] : wasteType;
                mainImage = getIcon(mainType);

                if (wasteColors[mainType] && wasteColors[mainType] !== "default") {
                    mainColor = wasteColors[mainType];
                    if (["#FFEB3B", "#FFFFFF", "#FF9800"].includes(mainColor)) {
                        mainTextColor = "#000000"; // unused but ready logic
                    } else {
                        mainTextColor = "#FFFFFF";
                    }
                }
            }

            // Generate forecast HTML
            let forecastHtml = upcomingSchedule.slice(0, 5).map(item => {
                let icon = "default.png";
                if (item.waste_types.length > 0) {
                    icon = getIcon(item.waste_types[0]);
                }

                const dateObj = new Date(item.date);
                const dateStr = `${dateObj.getDate()}/${dateObj.getMonth() + 1}`;

                return `
                <div class="forecast-item" style="display: flex; flex-direction: column; align-items: center; width: 60px;">
                    <span class="day-name" style="font-size: 12px; font-weight: bold;">${item.day.substring(0, 3)}</span>
                    <span class="date" style="font-size: 10px; color: var(--secondary-text-color);">${dateStr}</span>
                    <img src="/local/waste_manager/rifiuti/${icon}" style="width: 32px; height: 32px; margin: 4px 0;">
                    <span class="waste-type" style="font-size: 10px; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; width: 100%;" title="${item.waste_types.join(', ')}">${item.waste_types.join(', ')}</span>
                </div>
                `;
            }).join('');

            // Prepare Timer HTML Placeholder if needed
            let timerHtml = "";
            let showTimer = false;

            if (daysUntil === 0 && collectionStart && collectionEnd) {
                showTimer = true;
                timerHtml = `
                    <div class="countdown-container">
                        <div class="countdown-timer" id="waste-timer">--:--:--</div>
                        <div class="countdown-label" id="waste-timer-label">...</div>
                    </div>
                 `;
            }

            this.content.innerHTML = `
            <style>
                .top-container { display: flex; flex-direction: row; align-items: center; justify-content: center; gap: 20px; margin-bottom: 10px; }
                .main-icon { width: 100px; height: 100px; object-fit: contain; }
                .countdown-container { display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(0,0,0,0.05); padding: 10px; border-radius: 10px; min-width: 100px; }
                .countdown-timer { font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1.2; }
                .countdown-label { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; color: var(--secondary-text-color); }
                .main-state { font-size: 24px; font-weight: 500; margin-top: 10px; text-align: center; }
                .pickup-details { font-size: 14px; color: var(--secondary-text-color); margin-top: 4px; }
                .pickup-time { font-size: 12px; color: var(--primary-color); font-weight: bold; margin-top: 4px; background: var(--secondary-background-color, #eee); padding: 2px 8px; border-radius: 12px; display: inline-block; }
                .forecast-container { display: flex; justify-content: space-around; margin-top: 20px; border-top: 1px solid var(--divider-color, #eee); padding-top: 10px; }
                .action-btn { background-color: var(--success-color, #4CAF50); color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; margin-top: 10px; width: 100%; }
                .status-badge { background-color: var(--success-color, #4CAF50); color: white; padding: 4px 8px; border-radius: 4px; font-size: 14px; margin-top: 5px; display: inline-block; }
            </style>
            
            <div class="top-container">
                <img class="main-icon" src="/local/waste_manager/rifiuti/${mainImage}">
                ${timerHtml}
            </div>
            
            <div class="info-container" style="${mainColor !== 'transparent' ? `background-color: ${mainColor}20; border: 2px solid ${mainColor}; border-radius: 12px; padding: 10px;` : ''}">
                <div class="main-state">${daysUntil === 0 ? "Oggi: " : daysUntil === 1 ? "Domani: " : ""} ${wasteType || "Nessun ritiro"}</div>
                
                
                ${daysUntil > 1 ? `<div class="pickup-details">Tra ${daysUntil} giorni</div>` : ""}
                ${timeString ? `<div class="pickup-time">${timeString}</div>` : ''}
            </div>

            <div class="forecast-container">
                ${forecastHtml}
            </div>
            `;


            // Start Timer Logic
            if (showTimer) {
                this._startTimer(collectionStart, collectionEnd);
            } else {
                this._stopTimer();
            }

        } catch (e) {
            console.error("Waste Card Error:", e);
            this.content.innerHTML = `
                <div style="color: red; padding: 10px;">
                    Card Error: ${e.message}
                </div>
            `;
        }
    }

    _startTimer(startStr, endStr) {
        if (this._timerInterval) clearInterval(this._timerInterval);

        const update = () => {
            const now = new Date();
            const timerEl = this.content.querySelector('#waste-timer');
            const labelEl = this.content.querySelector('#waste-timer-label');

            if (!timerEl || !labelEl) return;

            const [startH, startM] = startStr.split(':').map(Number);
            const [endH, endM] = endStr.split(':').map(Number);

            const startTime = new Date(now);
            startTime.setHours(startH, startM, 0, 0);

            const endTime = new Date(now);
            endTime.setHours(endH, endM, 0, 0);

            if (endTime < startTime) {
                endTime.setDate(endTime.getDate() + 1);
            }

            let targetTime;
            let label;

            if (now < startTime) {
                targetTime = startTime;
                label = "All'uscita";
            } else if (now < endTime) {
                targetTime = endTime;
                label = "Al rientro";
            } else {
                timerEl.innerHTML = "Terminato";
                labelEl.innerHTML = "";
                return;
            }

            const diff = targetTime - now;
            if (diff <= 0) return;

            const h = Math.floor(diff / (1000 * 60 * 60));
            const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const s = Math.floor((diff % (1000 * 60)) / 1000);

            const pad = (n) => n.toString().padStart(2, '0');
            timerEl.innerHTML = `${pad(h)}:${pad(m)}:${pad(s)}`;
            labelEl.innerHTML = label;
        };

        update();
        this._timerInterval = setInterval(update, 1000);
    }

    _stopTimer() {
        if (this._timerInterval) {
            clearInterval(this._timerInterval);
            this._timerInterval = null;
        }
    }

    disconnectedCallback() {
        this._stopTimer();
    }

    setConfig(config) {
        if (!config.entity) {
            throw new Error('You need to define an entity');
        }
        this.config = config;
    }

    getCardSize() {
        return 3;
    }
}

customElements.define('waste-card', WasteCard);

