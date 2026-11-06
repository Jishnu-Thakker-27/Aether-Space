# 🌟 Aether Space — AI Chatbot Companion
### FastAPI + Vite Architecture

A full-stack, tactile conversational AI companion application designed for mindfulness, focus, and daily guidance with a claymorphic design and high-performance modern web framework architecture.

- **Frontend:** Semantic HTML5 + Pure CSS3 (Claymorphic Design System) + Vanilla JavaScript (ES6+) bundled with **Vite**
- **Backend:** **FastAPI** + **Uvicorn** with automatic OpenAPI/Swagger documentation (`/docs`)
- **AI Engine:** Google Gemini API (via `google-genai` SDK with sub-second `gemini-3.1-flash-lite` and instant fast-path)
- **Database:** Dual-Engine Relational Architecture: MySQL with automated SQLite local fallback (`chatbot_local.db`)
- **Audio Engine:** Browser Web Audio API (432Hz ambient soundscapes, haptic pops, Tibetan singing bowl chime)

---

## 📁 Project Structure

```
Aether Space/
├── index.html              # Frontend user interface (Auth & Chatbot screens)
├── style.css               # Complete claymorphic stylesheet (pure CSS)
├── app.js                  # Frontend logic, Web Audio engine, IST time, & REST client
├── main.py                 # FastAPI backend application with Uvicorn & OpenAPI docs
├── server.py               # Server runner alias (runs FastAPI / Uvicorn)
├── vite.config.js          # Vite build & development server configuration (proxies /api)
├── package.json            # Node/Vite dependency configuration
├── database.py             # Dual-engine database persistence (MySQL + SQLite WAL mode)
├── ai_service.py           # Google Gemini AI client with instant fast-path & clean formatting
├── setup_database.sql      # Optional MySQL schema creation script
├── requirements.txt        # Python dependencies (fastapi, uvicorn, google-genai, etc.)
├── run.bat                 # One-click Windows launch script (starts server & opens browser)
├── .env                    # Environment variables (GEMINI_API_KEY, MySQL credentials)
├── .env.example            # Environment variables template
├── chatbot_local.db        # SQLite database for zero-configuration local development
└── README.md               # Project documentation & setup instructions
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** installed
- **Node.js (v18+)** installed
- Optional: **MySQL Server** (if not installed, the app automatically uses local SQLite with zero setup!)

### 2. Configure Environment (`.env`)
Create or edit `.env` in the root directory:

```env
# 1. Google Gemini API Key (Get a free key from https://aistudio.google.com/)
GEMINI_API_KEY=your_actual_gemini_api_key

# 2. Local MySQL Database Credentials (Optional)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=chatbot_db
PORT=8000
```

### 3. Install Dependencies

**Python Dependencies:**
```bash
pip install -r requirements.txt
```

**Frontend Dependencies (Vite):**
```bash
npm install
```

---

### 4. Running the Application

#### Option A: One-Click Launch (Windows)
Double-click `run.bat` or run:
```bash
python main.py
```
* **Frontend UI:** `http://127.0.0.1:8000`
* **Swagger API Documentation:** `http://127.0.0.1:8000/docs`
* **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`

#### Option B: Full-Stack Development Mode (FastAPI + Vite Dev Server)
1. **Start FastAPI Backend:**
   ```bash
   python main.py 8000
   ```
2. **Start Vite Dev Server with HMR:**
   ```bash
   npm run dev
   ```
   * Open `http://localhost:5173` (Vite dev server automatically proxies `/api` calls to FastAPI on port 8000).

#### Option C: Production Build
```bash
npm run build
python main.py
```
Vite compiles optimized production assets into `dist/`, which FastAPI automatically serves on port 8000.

---

## 🌟 Key Features

1. **FastAPI High-Performance Backend:**
   - Asynchronous request handling with Uvicorn.
   - Pydantic schema validation for strict type safety.
   - Interactive Swagger UI (`/docs`) and ReDoc (`/redoc`) API explorer.
   - Complete REST API: `/api/register`, `/api/login`, `/api/google-auth`, `/api/phone-auth`, `/api/reset-password`, `/api/chat`, and `/api/history`.

2. **Vite Modern Frontend Tooling:**
   - Instant cold server start with Hot Module Replacement (HMR).
   - Rollup-optimized production bundling (`npm run build`) in `dist/`.
   - Built-in proxy configuration to backend API.

3. **Claymorphic UI Aesthetic:**
   - 3D tactile clay buttons, recessed inset input fields, and smooth debossed text shadows.
   - Animated custom 3D clay avatar with headphones, cheerful expressions, and online indicator pip.
   - Responsive card container that scales effortlessly between desktop laptops and mobile viewports.

4. **Enterprise-Grade Authentication & Security:**
   - **Bcrypt Password Hashing:** Passwords hashed with salted bcrypt (rounds=12). Passwords are never stored plain-text or in browser `localStorage`.
   - **Token-Verified Password Reset:** 2-step reset flow requiring a cryptographically random 6-digit verification code with 10-minute validity, eliminating unauthorized account takeovers.
   - **Official Google OAuth 2.0:** Integrated with Google Identity Services (GSI). Users authenticate on Google's domain; backend verifies signed ID tokens without collecting user passwords.
   - **Strict Password Rules:** Minimum 8 characters enforced on both frontend and backend Pydantic schemas.
   - **Server-Side API Key Isolation:** `GEMINI_API_KEY` is strictly confined to server-side environment variables and is never exposed to client-side scripts.
   - **WCAG 2.1 Accessibility:** Viewport metadata allows pinch-to-zoom for responsive accessibility compliance.

5. **Sub-Second AI Inference & IST Sync:**
   - Prioritized `gemini-3.1-flash-lite` responding in ~0.7s - 1.0s.
   - Sub-30ms instant fast-path for conversational greetings (*"hi"*, *"how are you"*, *"what can you do"*).
   - Strict Indian Standard Time (IST, UTC+5:30) calculations for daily greetings.
   - Clean markdown output without raw hash symbols (`#`) or awkward personalizations.

6. **Integrated Web Audio Engine:**
   - **Haptic Clicks:** Client-side oscillator clicks synthesized on keypresses and button taps.
   - **Meditation Chime:** 432Hz sine tone with harmonic 5th overtone and bandpass filter on auth success.
   - **Ambient Soundscape:** Continuous 432Hz/438Hz binaural theta brainwave audio generator for deep focus.
   - **Text-to-Speech (TTS):** Browser SpeechSynthesis utterance integration on every assistant message.
