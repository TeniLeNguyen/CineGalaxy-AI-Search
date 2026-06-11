// =========================================================================
// 1. CẤU HÌNH NGÀN NGÔI SAO LẤP LÁNH BAY LƯỢN (PARTICLES.JS)
// =========================================================================
particlesJS("particles-js", {
    "particles": {
        "number": { "value": 120, "density": { "enable": true, "value_area": 800 } },
        "color": { "value": "#ffffff" },
        "shape": { "type": "circle" },
        "opacity": {
            "value": 0.5,
            "random": true,
            "anim": { "enable": true, "speed": 1, "opacity_min": 0.1, "sync": false }
        },
        "size": {
            "value": 3,
            "random": true,
            "anim": { "enable": true, "speed": 2, "size_min": 0.1, "sync": false }
        },
        "line_linked": { "enable": false },
        "move": {
            "enable": true,
            "speed": 0.5,
            "direction": "none",
            "random": true,
            "straight": false,
            "out_mode": "out",
            "bounce": false
        }
    },
    "interactivity": {
        "detect_on": "canvas",
        "events": {
            "onhover": { "enable": true, "mode": "bubble" },
            "onclick": { "enable": true, "mode": "push" }
        },
        "modes": {
            "bubble": {
                "distance": 100,
                "size": 6,
                "duration": 2,
                "opacity": 0.8,
                "speed": 3
            },
            "push": {
                "particles_nb": 4
            }
        }
    },
    "retina_detect": true
});


// =========================================================================
// 2. DOM ELEMENTS
// =========================================================================
const searchBtn = document.getElementById('search-btn');
const searchInput = document.getElementById('search-input');
const resultsContainer = document.getElementById('results-container');
const aiBox = document.getElementById("ai-response");

// Modal
const movieModal = document.getElementById("movie-modal");
const modalTitle = document.getElementById("modal-title");
const modalGenre = document.getElementById("modal-genre");
const modalOrigin = document.getElementById("modal-origin");
const modalYear = document.getElementById("modal-year");
const modalDirector = document.getElementById("modal-director");
const modalCast = document.getElementById("modal-cast");
const modalPlot = document.getElementById("modal-plot");
const closeModal = document.getElementById("close-modal");


// =========================================================================
// 3. MAIN SEARCH (GỘP AI + MOVIE SEARCH)
// =========================================================================
async function scanCineGalaxy(keyword) {

    const query = keyword?.trim();

    if (!query) return;

    resultsContainer.innerHTML = `
        <p style="grid-column: 1/-1; color: #06b6d4;">
            🤖 CineGalaxy AI Assistant is analyzing "${query}"...
        </p>
    `;

    try {

        const response = await fetch(
            `http://127.0.0.1:8000/api/chat?query=${encodeURIComponent(query)}`
        );

        const data = await response.json();

        if (data.error) {

            resultsContainer.innerHTML = `
                <p style="grid-column: 1/-1; color: #ef4444;">
                    ⚠️ Error: ${data.error}
                </p>
            `;

            return;
        }

        // =========================
        // AI RESPONSE
        // =========================
        if (aiBox) {

            aiBox.classList.remove("hidden");

            aiBox.innerHTML = `
                <h3>🤖 CineGalaxy AI Assistant</h3>
                <p>${data.answer || "No AI response"}</p>
            `;
        }

        // =========================
        // MOVIES
        // =========================
        renderMovies(data.movies || []);

    }
    catch (error) {

        console.error(error);

        resultsContainer.innerHTML = `
            <p style="grid-column: 1/-1; color: #ef4444;">
                ⚠️ Cannot connect to Galaxy Core.
                Please ensure backend is running.
            </p>
        `;
    }
}


// =========================================================================
// 4. RENDER MOVIES
// =========================================================================
function renderMovies(movies) {

    resultsContainer.innerHTML = '';

    if (!movies || movies.length === 0) {

        resultsContainer.innerHTML = `
            <p style="grid-column: 1/-1; color: #64748b;">
                No cosmic anomalies found matching your criteria.
            </p>
        `;

        return;
    }

    movies.forEach((movie, index) => {

        const card = document.createElement('div');

        card.className = 'movie-card';

        card.style.animation =
            `fadeInUp 0.4s ease forwards ${index * 0.05}s`;

        card.style.opacity = '0';

        const rawTitle =
            movie.Title || movie.title || "UNKNOWN";

        const rawOrigin =
            movie.Origin || movie.origin || "Unknown";

        const rawGenre =
            movie.Genre || movie.genre || "Unknown";

        const year =
            movie.Year || movie.year || "N/A";

        const plot =
            movie.Plot || movie.plot || "";

        const title =
            String(rawTitle).toUpperCase();

        const origin =
            String(rawOrigin).charAt(0).toUpperCase()
            + String(rawOrigin).slice(1);

        const genre =
            String(rawGenre).charAt(0).toUpperCase()
            + String(rawGenre).slice(1);

        const director =
            movie.Director ||
            movie.director ||
            "Unknown";

        const cast =
            movie.Cast ||
            movie.cast ||
            "Unknown";

        card.innerHTML = `
            <div class="movie-year">${year}</div>

            <div class="movie-title">
                ${title}
            </div>

            <div class="movie-meta">
                <span>🛸 ${origin}</span>
                <span>✨ ${genre}</span>
            </div>

            <div class="movie-plot">
                ${plot}
            </div>
        `;

        // =========================
        // OPEN MODAL
        // =========================
        card.addEventListener('click', () => {

            modalTitle.textContent = rawTitle;

            modalYear.textContent =
                `📅 Year: ${year}`;

            modalOrigin.textContent =
                `🌍 Origin: ${origin}`;

            modalGenre.textContent =
                `🎭 Genre: ${genre}`;

            modalDirector.textContent =
                `🎬 Director: ${director}`;

            modalCast.textContent =
                `⭐ Cast: ${cast}`;

            modalPlot.textContent =
                plot || "No plot available.";

            movieModal.classList.remove('hidden');
        });

        resultsContainer.appendChild(card);
    });
}


// =========================================================================
// 5. EVENT LISTENERS
// =========================================================================
if (searchBtn) {

    searchBtn.addEventListener('click', () => {

        scanCineGalaxy(searchInput.value);

    });
}

if (searchInput) {

    searchInput.addEventListener('keypress', (e) => {

        if (e.key === 'Enter') {

            scanCineGalaxy(searchInput.value);

        }
    });
}


// =========================================================================
// 6. MODAL EVENTS
// =========================================================================
if (closeModal) {

    closeModal.addEventListener('click', () => {

        movieModal.classList.add('hidden');

    });
}

if (movieModal) {

    movieModal.addEventListener('click', (e) => {

        if (e.target === movieModal) {

            movieModal.classList.add('hidden');

        }
    });
}

document.addEventListener('keydown', (e) => {

    if (
        e.key === 'Escape'
        &&
        movieModal
    ) {

        movieModal.classList.add('hidden');

    }
});


// =========================================================================
// 7. ANIMATION STYLE
// =========================================================================
const style = document.createElement('style');

style.innerHTML = `
@keyframes fadeInUp {

    from {
        opacity: 0;
        transform: translateY(20px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}
`;

document.head.appendChild(style);