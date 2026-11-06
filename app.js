/**
 * AETHER SPACE — FRONTEND JAVASCRIPT LOGIC
 * Pure Vanilla JavaScript (ES6+) with zero npm/node dependencies.
 * Implements Web Audio Engine, IST synchronization, state management,
 * modals, speech synthesis, and REST API communication with Python backend.
 */

// ============================================================================
// 1. Tactile Web Audio Engine (Pure Web Audio API)
// ============================================================================

class TactileAudioEngine {
  constructor() {
    this.ctx = null;
    this.ambientNodes = [];
    this.isSoundscapePlaying = false;
    this.ambientGain = null;
  }

  initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  // Soft organic tactile pop / click
  playHapticClick(frequency = 320, duration = 0.04) {
    try {
      this.initContext();
      if (!this.ctx) return;

      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      const filter = this.ctx.createBiquadFilter();

      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(800, this.ctx.currentTime);
      filter.frequency.exponentialRampToValueAtTime(100, this.ctx.currentTime + duration);

      osc.type = 'triangle';
      osc.frequency.setValueAtTime(frequency, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(60, this.ctx.currentTime + duration);

      gain.gain.setValueAtTime(0.25, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);

      osc.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start();
      osc.stop(this.ctx.currentTime + duration);
    } catch {
      // Audio might be blocked before first user gesture
    }
  }

  // Harmonic Tibetan Singing Bowl Chime (432Hz focus tone)
  playChime(freq = 432, duration = 1.8) {
    try {
      this.initContext();
      if (!this.ctx) return;

      const now = this.ctx.currentTime;
      const osc1 = this.ctx.createOscillator();
      const osc2 = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      const filter = this.ctx.createBiquadFilter();

      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(freq, now);

      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(freq * 1.502, now); // harmonic fifth

      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(freq * 1.2, now);
      filter.Q.setValueAtTime(2, now);

      gain.gain.setValueAtTime(0.001, now);
      gain.gain.exponentialRampToValueAtTime(0.3, now + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

      osc1.connect(filter);
      osc2.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);

      osc1.start(now);
      osc2.start(now);
      osc1.stop(now + duration);
      osc2.stop(now + duration);
    } catch {
      // Ignored if audio context is not permitted
    }
  }

  // 432Hz Theta Focus Soundscape Synthesis
  playSoundscape() {
    try {
      this.initContext();
      if (!this.ctx) return;
      this.stopSoundscape();

      const now = this.ctx.currentTime;
      this.ambientGain = this.ctx.createGain();
      this.ambientGain.gain.setValueAtTime(0.001, now);
      this.ambientGain.gain.exponentialRampToValueAtTime(0.2, now + 1.5);
      this.ambientGain.connect(this.ctx.destination);

      // 432Hz Base Binaural Carrier
      const oscBase = this.ctx.createOscillator();
      oscBase.type = 'sine';
      oscBase.frequency.setValueAtTime(432, now);

      // 438Hz Detuned Oscillator (creates 6Hz theta wave brainwave pulse)
      const oscTheta = this.ctx.createOscillator();
      oscTheta.type = 'sine';
      oscTheta.frequency.setValueAtTime(438, now);

      // Gentle sub-bass ground
      const oscSub = this.ctx.createOscillator();
      oscSub.type = 'sine';
      oscSub.frequency.setValueAtTime(108, now);

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'lowpass';
      filter.frequency.setValueAtTime(500, now);

      oscBase.connect(filter);
      oscTheta.connect(filter);
      oscSub.connect(filter);
      filter.connect(this.ambientGain);

      oscBase.start(now);
      oscTheta.start(now);
      oscSub.start(now);

      this.ambientNodes = [oscBase, oscTheta, oscSub];
      this.isSoundscapePlaying = true;
    } catch {
      this.isSoundscapePlaying = false;
    }
  }

  stopSoundscape() {
    if (this.ambientNodes.length > 0 && this.ctx) {
      try {
        const now = this.ctx.currentTime;
        if (this.ambientGain) {
          this.ambientGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.6);
        }
        setTimeout(() => {
          this.ambientNodes.forEach((node) => {
            try { node.stop(); } catch {}
          });
          this.ambientNodes = [];
        }, 700);
      } catch {
        this.ambientNodes = [];
      }
    }
    this.isSoundscapePlaying = false;
  }
}

const audio = new TactileAudioEngine();

// ============================================================================
// 2. State & Indian Standard Time (IST) Helpers
// ============================================================================

const state = {
  screen: 'auth', // 'auth' | 'chatbot'
  authMode: 'signin', // 'signin' | 'signup'
  currentUser: {
    username: '',
    email: ''
  },
  showPassword: false,
  ambientAudioOn: false,
  isLoading: false,
  speakingId: null,
  copiedId: null,
  generatedOtp: '',
  messages: []
};

// Returns formatted time string in IST (e.g. "10:30 AM")
function getISTFormattedTime() {
  return new Date().toLocaleTimeString('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
}

// Returns hour (0-23) in IST
function getISTHour() {
  const istDateString = new Date().toLocaleString('en-US', { timeZone: 'Asia/Kolkata' });
  return new Date(istDateString).getHours();
}

// Dynamic greeting calculated in IST
function getGreeting() {
  const hour = getISTHour();
  if (hour >= 4 && hour < 12) return 'Good morning';
  if (hour >= 12 && hour < 17) return 'Good afternoon';
  return 'Good evening';
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Helper to render markdown, code blocks, bold text, headings, and lists cleanly
function renderFormattedContent(content) {
  if (!content) return '';

  // Handle multi-line code blocks using non-hash delimiters
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const processed = content.replace(codeBlockRegex, (match, lang, code) => {
    const escapedCode = escapeHtml(code.trim());
    const langBadge = lang
      ? `<div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 4px;">${escapeHtml(lang)}</div>`
      : '';
    return `§§§CODEBLOCK_START§§§${langBadge}<pre style="margin: 6px 0; padding: 10px 12px; background: rgba(30, 41, 59, 0.08); border-radius: 10px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; overflow-x: auto; color: #1e293b; line-height: 1.45; border: 1px solid rgba(148, 163, 184, 0.25);"><code>${escapedCode}</code></pre>§§§CODEBLOCK_END§§§`;
  });

  const lines = processed.split('\n');
  let inCodeBlock = false;
  const outputLines = [];

  for (let line of lines) {
    if (line.includes('§§§CODEBLOCK_START§§§')) {
      inCodeBlock = true;
      line = line.replace('§§§CODEBLOCK_START§§§', '');
    }
    if (line.includes('§§§CODEBLOCK_END§§§')) {
      inCodeBlock = false;
      line = line.replace('§§§CODEBLOCK_END§§§', '');
      outputLines.push(line);
      continue;
    }
    if (inCodeBlock) {
      outputLines.push(line);
      continue;
    }

    const trimmed = line.trim();
    if (!trimmed) {
      outputLines.push('<div style="height: 6px;"></div>');
      continue;
    }

    // Check and parse Markdown headings (# Heading, ## Heading, ### Heading, etc.)
    const headerMatch = trimmed.match(/^(#{1,6})\s*(.*)$/);
    if (headerMatch) {
      const level = headerMatch[1].length;
      let titleText = escapeHtml(headerMatch[2].trim());
      // Apply inline bold & code tags inside headings
      titleText = titleText.replace(/\*\*(.*?)\*\*/g, '<strong style="font-weight: 800;">$1</strong>');
      titleText = titleText.replace(/`([^`]+)`/g, '<code style="background: rgba(82, 166, 186, 0.15); color: #0e7490; padding: 1px 4px; border-radius: 4px; font-size: 11px;">$1</code>');

      if (level === 1) {
        outputLines.push(`<div style="font-size: 14px; font-weight: 800; color: #162a3b; margin: 8px 0 3px 0; border-bottom: 1px solid rgba(82, 166, 186, 0.25); padding-bottom: 2px;">${titleText}</div>`);
      } else if (level === 2) {
        outputLines.push(`<div style="font-size: 13px; font-weight: 800; color: #1e3345; margin: 7px 0 3px 0;">${titleText}</div>`);
      } else if (level === 3) {
        outputLines.push(`<div style="font-size: 12.5px; font-weight: 800; color: #22384c; margin: 6px 0 2px 0;">${titleText}</div>`);
      } else {
        outputLines.push(`<div style="font-size: 12px; font-weight: 700; color: #2d4559; margin: 5px 0 2px 0;">${titleText}</div>`);
      }
      continue;
    }

    // Strip any other accidental leading hash signs from the line
    let cleanedLine = trimmed.replace(/^#{1,6}\s*/, '');

    const isBullet = cleanedLine.startsWith('* ') || cleanedLine.startsWith('- ');
    const isNumbered = /^\d+\.\s/.test(cleanedLine);

    let text = cleanedLine;
    if (isBullet) {
      text = cleanedLine.substring(2);
    } else if (isNumbered) {
      text = cleanedLine.replace(/^\d+\.\s/, '');
    }

    // Escape HTML inside standard text lines (code blocks are handled separately)
    text = escapeHtml(text);

    // Bold formatting: **text**
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong style="font-weight: 800; color: #1f3447;">$1</strong>');

    // Inline code formatting: `code`
    text = text.replace(/`([^`]+)`/g, '<code style="background: rgba(82, 166, 186, 0.15); color: #0e7490; padding: 1px 5px; border-radius: 4px; font-family: monospace; font-size: 11px; font-weight: 600;">$1</code>');

    if (isBullet) {
      outputLines.push(`
        <div style="display: flex; align-items: flex-start; gap: 8px; margin-left: 4px; margin-top: 2px; margin-bottom: 2px;">
          <span style="width: 6px; height: 6px; border-radius: 9999px; background-color: #52a6ba; flex-shrink: 0; margin-top: 6px;"></span>
          <span style="flex: 1 1 0%;">${text}</span>
        </div>
      `);
    } else if (isNumbered) {
      const matchNum = cleanedLine.match(/^(\d+)\.\s/);
      const numLabel = matchNum ? matchNum[1] : '•';
      outputLines.push(`
        <div style="display: flex; align-items: flex-start; gap: 6px; margin-left: 4px; margin-top: 2px; margin-bottom: 2px;">
          <span style="font-weight: 700; color: #52a6ba; flex-shrink: 0; min-width: 14px;">${numLabel}.</span>
          <span style="flex: 1 1 0%;">${text}</span>
        </div>
      `);
    } else {
      outputLines.push(`<p style="margin: 2px 0;">${text}</p>`);
    }
  }

  return outputLines.join('');
}

// ============================================================================
// 3. UI DOM Elements
// ============================================================================

const DOM = {
  // Screens
  authScreen: document.getElementById('auth-screen'),
  chatbotScreen: document.getElementById('chatbot-screen'),

  // Auth elements
  authTitle: document.getElementById('auth-title'),
  authSubtitle: document.getElementById('auth-subtitle'),
  tabSignIn: document.getElementById('tab-signin'),
  tabSignUp: document.getElementById('tab-signup'),
  dividerText: document.getElementById('divider-text'),
  fieldUsernameContainer: document.getElementById('field-username-container'),
  fieldConfirmContainer: document.getElementById('field-confirm-container'),
  labelPassword: document.getElementById('label-password'),
  inputUsername: document.getElementById('input-username'),
  inputEmail: document.getElementById('input-email'),
  inputPassword: document.getElementById('input-password'),
  inputConfirmPassword: document.getElementById('input-confirm-password'),
  btnTogglePassword: document.getElementById('btn-toggle-password'),
  iconEyeOn: document.getElementById('icon-eye-on'),
  iconEyeOff: document.getElementById('icon-eye-off'),
  authErrorBox: document.getElementById('auth-error-box'),
  authErrorText: document.getElementById('auth-error-text'),
  btnAuthSubmit: document.getElementById('btn-auth-submit'),
  btnAuthSubmitText: document.getElementById('btn-auth-submit-text'),

  // Modals buttons
  btnOpenGoogle: document.getElementById('btn-open-google'),
  btnFastGuest: document.getElementById('btn-fast-guest'),
  btnOpenForgot: document.getElementById('btn-open-forgot'),
  btnOpenHelp: document.getElementById('btn-open-help'),
  linkTerms: document.getElementById('link-terms'),
  linkPrivacy: document.getElementById('link-privacy'),
  googlePillLabel: document.getElementById('google-pill-label'),

  // Modals overlays
  modalGoogleInfo: document.getElementById('modal-google-info'),
  btnTriggerGsiPrompt: document.getElementById('btn-trigger-gsi-prompt'),
  modalForgot: document.getElementById('modal-forgot'),
  modalHelp: document.getElementById('modal-help'),

  // Secure Token-Verified Password Reset
  forgotStep1: document.getElementById('forgot-step-1'),
  forgotStep2: document.getElementById('forgot-step-2'),
  forgotEmail: document.getElementById('forgot-email'),
  forgotCode: document.getElementById('forgot-code'),
  forgotNewPassword: document.getElementById('forgot-new-password'),
  forgotErrorMsg1: document.getElementById('forgot-error-msg-1'),
  forgotErrorMsg2: document.getElementById('forgot-error-msg-2'),
  btnSendResetCode: document.getElementById('btn-send-reset-code'),
  btnVerifyAndReset: document.getElementById('btn-verify-and-reset'),
  forgotSuccessSection: document.getElementById('forgot-success-section'),

  // Chatbot elements
  btnBackToAuth: document.getElementById('btn-back-to-auth'),
  btnToggleSoundscape: document.getElementById('btn-toggle-soundscape'),
  iconSoundOn: document.getElementById('icon-sound-on'),
  iconSoundOff: document.getElementById('icon-sound-off'),
  audioStatusPip: document.getElementById('audio-status-pip'),
  soundscapeBanner: document.getElementById('soundscape-banner'),
  btnBannerMute: document.getElementById('btn-banner-mute'),
  btnResetChat: document.getElementById('btn-reset-chat'),
  chatGreeting: document.getElementById('chat-greeting'),
  messagesContainer: document.getElementById('messages-container'),
  thinkingIndicator: document.getElementById('thinking-indicator'),
  chatInputForm: document.getElementById('chat-input-form'),
  chatMessageInput: document.getElementById('chat-message-input'),
  btnSendMessage: document.getElementById('btn-send-message')
};

// ============================================================================
// 4. Modal Helpers
// ============================================================================

function openModal(modalEl) {
  if (!modalEl) return;
  audio.playHapticClick(350);
  modalEl.classList.remove('hidden');
}

function closeModal(modalEl) {
  if (!modalEl) return;
  audio.playHapticClick(280);
  modalEl.classList.add('hidden');
}

document.querySelectorAll('.btn-close-modal').forEach((btn) => {
  btn.addEventListener('click', (e) => {
    const modal = e.target.closest('.modal-overlay');
    if (modal) closeModal(modal);
  });
});

document.querySelectorAll('.modal-overlay').forEach((overlay) => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal(overlay);
  });
});

// ============================================================================
// 5. Auth Screen Switching & Actions
// ============================================================================

function setAuthMode(mode) {
  state.authMode = mode;
  audio.playHapticClick(350);
  if (DOM.authErrorBox) DOM.authErrorBox.classList.add('hidden');

  if (mode === 'signin') {
    DOM.tabSignIn.className = 'flex-1 text-xs font-bold clay-badge-active cursor-pointer text-center';
    DOM.tabSignUp.className = 'flex-1 text-xs font-bold cursor-pointer text-center';
    DOM.tabSignUp.style.background = 'transparent';
    DOM.tabSignUp.style.color = '#50677b';

    DOM.authTitle.innerText = 'Welcome';
    DOM.authSubtitle.innerText = 'Sign in to connect with your AI companion.';
    DOM.dividerText.innerText = 'or email sign in';
    DOM.labelPassword.innerText = 'Password';
    DOM.inputPassword.placeholder = 'Enter your password (min 8 chars)';
    DOM.btnAuthSubmitText.innerText = 'Sign In to Chatbot';

    if (DOM.googlePillLabel) DOM.googlePillLabel.innerText = 'Sign In with Google';

    DOM.fieldUsernameContainer.classList.add('hidden');
    DOM.fieldConfirmContainer.classList.add('hidden');
    DOM.btnOpenForgot.classList.remove('hidden');
  } else {
    DOM.tabSignUp.className = 'flex-1 text-xs font-bold clay-badge-active cursor-pointer text-center';
    DOM.tabSignIn.className = 'flex-1 text-xs font-bold cursor-pointer text-center';
    DOM.tabSignIn.style.background = 'transparent';
    DOM.tabSignIn.style.color = '#50677b';

    DOM.authTitle.innerText = 'Create Account';
    DOM.authSubtitle.innerText = 'Join Aether Space to begin your journey.';
    DOM.dividerText.innerText = 'or create with email';
    DOM.labelPassword.innerText = 'Create Password (min 8 chars)';
    DOM.inputPassword.placeholder = 'Choose a password (min 8 chars)';
    DOM.btnAuthSubmitText.innerText = 'Create Account & Start Chat';

    if (DOM.googlePillLabel) DOM.googlePillLabel.innerText = 'Create with Google';

    DOM.fieldUsernameContainer.classList.remove('hidden');
    DOM.fieldConfirmContainer.classList.remove('hidden');
    DOM.btnOpenForgot.classList.add('hidden');
  }
}

DOM.tabSignIn.addEventListener('click', () => setAuthMode('signin'));
DOM.tabSignUp.addEventListener('click', () => setAuthMode('signup'));

// Toggle Password Visibility
DOM.btnTogglePassword.addEventListener('click', () => {
  audio.playHapticClick(350);
  state.showPassword = !state.showPassword;
  DOM.inputPassword.type = state.showPassword ? 'text' : 'password';
  if (DOM.inputConfirmPassword) {
    DOM.inputConfirmPassword.type = state.showPassword ? 'text' : 'password';
  }
  if (state.showPassword) {
    DOM.iconEyeOff.classList.add('hidden');
    DOM.iconEyeOn.classList.remove('hidden');
  } else {
    DOM.iconEyeOff.classList.remove('hidden');
    DOM.iconEyeOn.classList.add('hidden');
  }
});

// Modal Triggers
DOM.btnOpenHelp.addEventListener('click', () => openModal(DOM.modalHelp));
DOM.linkTerms.addEventListener('click', () => openModal(DOM.modalHelp));
DOM.linkPrivacy.addEventListener('click', () => openModal(DOM.modalHelp));

// Fast Guest 1-Tap Entry
if (DOM.btnFastGuest) {
  DOM.btnFastGuest.addEventListener('click', () => {
    audio.playChime(528, 1.2);
    enterChatbot('Explorer', 'guest@aetherspace.local');
  });
}

// ============================================================================
// Official Google Identity Services (OAuth 2.0) Handler
// ============================================================================

window.handleGoogleCredentialResponse = async function(response) {
  if (!response || !response.credential) return;
  audio.playHapticClick(450);
  try {
    const res = await fetch('/api/google-auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential: response.credential })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.error || 'Google authentication failed');
    }
    if (DOM.modalGoogleInfo) closeModal(DOM.modalGoogleInfo);
    audio.playChime(528, 1.2);
    enterChatbot(data.user?.username || 'Google User', data.user?.email || '');
  } catch (err) {
    showAuthError(err.message || 'Google OAuth verification failed. Please try Email & Password.');
  }
};

DOM.btnOpenGoogle.addEventListener('click', () => {
  if (window.google && window.google.accounts && window.google.accounts.id) {
    try {
      window.google.accounts.id.prompt((notification) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          openModal(DOM.modalGoogleInfo);
        }
      });
    } catch {
      openModal(DOM.modalGoogleInfo);
    }
  } else {
    openModal(DOM.modalGoogleInfo);
  }
});

if (DOM.btnTriggerGsiPrompt) {
  DOM.btnTriggerGsiPrompt.addEventListener('click', () => {
    if (window.google && window.google.accounts && window.google.accounts.id) {
      window.google.accounts.id.prompt();
    } else {
      alert('Google Identity Services script is loading or blocked by browser extensions.');
    }
  });
}

// ============================================================================
// Primary Email & Password Authentication Handler (Bcrypt & Min 8 Chars)
// ============================================================================

document.getElementById('auth-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  DOM.authErrorBox.classList.add('hidden');

  const username = DOM.inputUsername.value.trim() || 'Friend';
  const email = DOM.inputEmail.value.trim().toLowerCase();
  const password = DOM.inputPassword.value.trim();
  const confirmPassword = DOM.inputConfirmPassword.value.trim();

  if (!email) {
    showAuthError('Please enter your email address.');
    return;
  }

  // Enforce strict min 8 characters requirement
  if (!password) {
    showAuthError('Password is required. Please enter your password.');
    return;
  }

  if (password.length < 8) {
    showAuthError('Password must be at least 8 characters long for account security.');
    return;
  }

  if (state.authMode === 'signup') {
    if (password !== confirmPassword) {
      showAuthError('Passwords do not match. Please re-enter.');
      return;
    }
  }

  audio.playHapticClick(480, 0.08);
  DOM.btnAuthSubmit.disabled = true;
  DOM.btnAuthSubmitText.innerText = state.authMode === 'signin' ? 'Signing In...' : 'Opening Space...';

  const endpoint = state.authMode === 'signup' ? '/api/register' : '/api/login';
  const payload = state.authMode === 'signup'
    ? { username, email, password }
    : { email, password };

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.error || 'Authentication failed');
    }

    audio.playChime(528, 1.2);
    enterChatbot(data.user?.username || username, data.user?.email || email);
  } catch (err) {
    showAuthError(err.message || 'Authentication failed. Please check your credentials.');
  } finally {
    DOM.btnAuthSubmit.disabled = false;
    DOM.btnAuthSubmitText.innerText = state.authMode === 'signin' ? 'Sign In to Chatbot' : 'Create Account & Start Chat';
  }
});

function showAuthError(msg) {
  audio.playHapticClick(260);
  DOM.authErrorText.innerText = msg;
  DOM.authErrorBox.classList.remove('hidden');
}

// ============================================================================
// Secure Token-Verified Password Reset Flow
// ============================================================================

DOM.btnOpenForgot.addEventListener('click', () => {
  DOM.forgotEmail.value = DOM.inputEmail.value;
  DOM.forgotStep1.classList.remove('hidden');
  DOM.forgotStep2.classList.add('hidden');
  DOM.forgotSuccessSection.classList.add('hidden');
  if (DOM.forgotErrorMsg1) DOM.forgotErrorMsg1.classList.add('hidden');
  if (DOM.forgotErrorMsg2) DOM.forgotErrorMsg2.classList.add('hidden');
  openModal(DOM.modalForgot);
});

// Step 1: Request 6-digit Code
DOM.btnSendResetCode.addEventListener('click', async () => {
  const email = DOM.forgotEmail.value.trim().toLowerCase();
  if (!email) {
    if (DOM.forgotErrorMsg1) {
      DOM.forgotErrorMsg1.innerText = 'Please enter your registered email address.';
      DOM.forgotErrorMsg1.classList.remove('hidden');
    }
    return;
  }

  audio.playHapticClick(420);
  DOM.btnSendResetCode.disabled = true;
  DOM.btnSendResetCode.innerText = 'Generating Secure Code...';
  if (DOM.forgotErrorMsg1) DOM.forgotErrorMsg1.classList.add('hidden');

  try {
    const res = await fetch('/api/forgot-password/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Could not initiate password reset.');
    }

    audio.playChime(528, 0.8);
    DOM.forgotStep1.classList.add('hidden');
    DOM.forgotStep2.classList.remove('hidden');
  } catch (err) {
    if (DOM.forgotErrorMsg1) {
      DOM.forgotErrorMsg1.innerText = err.message;
      DOM.forgotErrorMsg1.classList.remove('hidden');
    }
  } finally {
    DOM.btnSendResetCode.disabled = false;
    DOM.btnSendResetCode.innerText = 'Send 6-Digit Reset Code';
  }
});

// Step 2: Verify Code and Update Password with Bcrypt
DOM.btnVerifyAndReset.addEventListener('click', async () => {
  const email = DOM.forgotEmail.value.trim().toLowerCase();
  const code = DOM.forgotCode.value.trim();
  const newPassword = DOM.forgotNewPassword.value.trim();

  if (!code || code.length !== 6) {
    if (DOM.forgotErrorMsg2) {
      DOM.forgotErrorMsg2.innerText = 'Please enter the 6-digit code sent to your email / server audit log.';
      DOM.forgotErrorMsg2.classList.remove('hidden');
    }
    return;
  }

  if (!newPassword || newPassword.length < 8) {
    if (DOM.forgotErrorMsg2) {
      DOM.forgotErrorMsg2.innerText = 'New password must be at least 8 characters long.';
      DOM.forgotErrorMsg2.classList.remove('hidden');
    }
    return;
  }

  audio.playHapticClick(450);
  DOM.btnVerifyAndReset.disabled = true;
  DOM.btnVerifyAndReset.innerText = 'Verifying & Encrypting...';
  if (DOM.forgotErrorMsg2) DOM.forgotErrorMsg2.classList.add('hidden');

  try {
    const res = await fetch('/api/forgot-password/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code, new_password: newPassword })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Password reset failed. Invalid or expired code.');
    }

    audio.playChime(528, 1.2);
    DOM.forgotStep2.classList.add('hidden');
    DOM.forgotSuccessSection.classList.remove('hidden');

    DOM.inputEmail.value = email;
    DOM.inputPassword.value = newPassword;
  } catch (err) {
    if (DOM.forgotErrorMsg2) {
      DOM.forgotErrorMsg2.innerText = err.message;
      DOM.forgotErrorMsg2.classList.remove('hidden');
    }
  } finally {
    DOM.btnVerifyAndReset.disabled = false;
    DOM.btnVerifyAndReset.innerText = 'Verify & Update Password';
  }
});

// ============================================================================
// 6. Chatbot Screen Logic
// ============================================================================

function enterChatbot(username, email) {
  state.currentUser = { username: username || 'Friend', email: email || '' };
  state.screen = 'chatbot';

  // Save session for automatic re-entry
  try {
    localStorage.setItem('aether_session', JSON.stringify(state.currentUser));
  } catch {}

  DOM.authScreen.classList.add('hidden');
  DOM.chatbotScreen.classList.remove('hidden');

  const greeting = getGreeting();
  DOM.chatGreeting.innerText = `${greeting}, ${state.currentUser.username}!`;
  DOM.chatMessageInput.placeholder = `Message Aether, ${state.currentUser.username}...`;

  loadChatHistory();
}

DOM.btnBackToAuth.addEventListener('click', () => {
  audio.playHapticClick(260);
  try {
    localStorage.removeItem('aether_session');
  } catch {}
  if (state.ambientAudioOn) {
    toggleAmbientSoundscape();
  }
  state.screen = 'auth';
  DOM.chatbotScreen.classList.add('hidden');
  DOM.authScreen.classList.remove('hidden');
});

// Ambient Audio Soundscape Toggle
function toggleAmbientSoundscape() {
  state.ambientAudioOn = !state.ambientAudioOn;
  audio.playHapticClick(state.ambientAudioOn ? 440 : 280);

  if (state.ambientAudioOn) {
    audio.playSoundscape();
    DOM.iconSoundOff.classList.add('hidden');
    DOM.iconSoundOn.classList.remove('hidden');
    DOM.btnToggleSoundscape.className = 'clay-badge-active flex items-center justify-center cursor-pointer';
    DOM.btnToggleSoundscape.style.width = '40px';
    DOM.btnToggleSoundscape.style.height = '40px';
    DOM.btnToggleSoundscape.style.borderRadius = '16px';
    DOM.btnToggleSoundscape.style.border = 'none';

    DOM.audioStatusPip.style.backgroundColor = '#4bb390';
    DOM.audioStatusPip.style.boxShadow = '0 0 8px #4bb390';
    DOM.audioStatusPip.classList.add('animate-pulse');
    DOM.soundscapeBanner.classList.remove('hidden');
  } else {
    audio.stopSoundscape();
    DOM.iconSoundOff.classList.remove('hidden');
    DOM.iconSoundOn.classList.add('hidden');
    DOM.btnToggleSoundscape.className = 'clay-surface-sm flex items-center justify-center cursor-pointer';
    DOM.btnToggleSoundscape.style.width = '40px';
    DOM.btnToggleSoundscape.style.height = '40px';
    DOM.btnToggleSoundscape.style.borderRadius = '16px';
    DOM.btnToggleSoundscape.style.border = 'none';
    DOM.btnToggleSoundscape.style.color = '#4a637a';

    DOM.audioStatusPip.style.backgroundColor = '#52a6ba';
    DOM.audioStatusPip.style.boxShadow = '0 0 6px #52a6ba';
    DOM.audioStatusPip.classList.remove('animate-pulse');
    DOM.soundscapeBanner.classList.add('hidden');
  }
}

DOM.btnToggleSoundscape.addEventListener('click', toggleAmbientSoundscape);
DOM.btnBannerMute.addEventListener('click', toggleAmbientSoundscape);

// Reset / Clear Conversation
DOM.btnResetChat.addEventListener('click', async () => {
  audio.playHapticClick(260);
  try {
    if (state.currentUser.email) {
      await fetch(`/api/history?email=${encodeURIComponent(state.currentUser.email)}`, {
        method: 'DELETE'
      });
    }
  } catch {}

  const greeting = getGreeting();
  state.messages = [
    {
      id: `welcome-${Date.now()}`,
      role: 'assistant',
      content: `${greeting}, ${state.currentUser.username}! Fresh slate. What are we diving into today?`,
      timestamp: getISTFormattedTime()
    }
  ];
  renderMessages();
});

// Load History from Python Backend
async function loadChatHistory() {
  try {
    if (state.currentUser.email) {
      const res = await fetch(`/api/history?email=${encodeURIComponent(state.currentUser.email)}`);
      if (res.ok) {
        const data = await res.json();
        if (data.history && data.history.length > 0) {
          state.messages = data.history.map((h) => ({
            id: `hist-${h.id}`,
            role: h.role,
            content: h.message,
            timestamp: h.created_at || getISTFormattedTime()
          }));
          renderMessages();
          return;
        }
      }
    }
  } catch {}

  const greeting = getGreeting();
  state.messages = [
    {
      id: 'welcome-init',
      role: 'assistant',
      content: `${greeting}, ${state.currentUser.username}! 🌅 I'm Aether, your mindful AI focus and daily guidance companion. How can I support your thoughts, day planning, or studies today?`,
      timestamp: getISTFormattedTime()
    }
  ];
  renderMessages();
}

// Render Messages to DOM
function renderMessages() {
  DOM.messagesContainer.innerHTML = '';

  state.messages.forEach((msg) => {
    const isUser = msg.role === 'user';
    const msgDiv = document.createElement('div');
    msgDiv.className = `flex flex-col ${isUser ? 'items-end' : 'items-start'} gap-1`;

    const bubble = document.createElement('div');
    bubble.style.maxWidth = '88%';
    bubble.style.padding = '14px';
    bubble.style.borderRadius = '16px';
    bubble.style.fontSize = '12px';
    bubble.style.fontWeight = '600';
    bubble.style.lineHeight = '1.625';

    if (isUser) {
      bubble.className = 'clay-badge-active rounded-br-xs';
      bubble.style.whiteSpace = 'pre-wrap';
      bubble.innerText = msg.content;
    } else {
      bubble.className = 'clay-surface-sm rounded-bl-xs';
      bubble.style.color = '#304557';
      bubble.innerHTML = renderFormattedContent(msg.content);
    }

    const meta = document.createElement('div');
    meta.className = 'flex items-center gap-2';
    meta.style.padding = '0 8px';
    meta.style.fontSize = '10px';
    meta.style.color = '#71879a';
    meta.style.fontWeight = '500';

    const timeLabel = document.createElement('span');
    timeLabel.innerText = `${isUser ? state.currentUser.username : 'Aether'} · ${msg.timestamp}`;
    meta.appendChild(timeLabel);

    if (!isUser) {
      const actions = document.createElement('div');
      actions.className = 'flex items-center gap-1.5';
      actions.style.marginLeft = '4px';

      // Text-To-Speech Button
      const speakBtn = document.createElement('button');
      speakBtn.type = 'button';
      speakBtn.title = 'Listen to response';
      speakBtn.style.background = 'none';
      speakBtn.style.border = 'none';
      speakBtn.style.cursor = 'pointer';
      speakBtn.style.padding = '2px';
      speakBtn.style.color = state.speakingId === msg.id ? '#0e7490' : '#698094';
      speakBtn.innerHTML = `
        <svg style="width: 14px; height: 14px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
        </svg>
      `;
      speakBtn.addEventListener('click', () => handleSpeak(msg.id, msg.content));
      actions.appendChild(speakBtn);

      // Copy Button
      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.title = 'Copy response';
      copyBtn.style.background = 'none';
      copyBtn.style.border = 'none';
      copyBtn.style.cursor = 'pointer';
      copyBtn.style.padding = '2px';
      copyBtn.style.color = '#698094';
      const isCopied = state.copiedId === msg.id;
      copyBtn.innerHTML = isCopied
        ? `<svg style="width: 14px; height: 14px; color: #059669;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>`
        : `<svg style="width: 14px; height: 14px;" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
      copyBtn.addEventListener('click', () => handleCopy(msg.id, msg.content));
      actions.appendChild(copyBtn);

      meta.appendChild(actions);
    }

    msgDiv.appendChild(bubble);
    msgDiv.appendChild(meta);
    DOM.messagesContainer.appendChild(msgDiv);
  });

  DOM.messagesContainer.scrollTop = DOM.messagesContainer.scrollHeight;
}

// Speech Synthesis Helper
function handleSpeak(id, text) {
  if (!('speechSynthesis' in window)) return;

  if (state.speakingId === id) {
    window.speechSynthesis.cancel();
    state.speakingId = null;
    renderMessages();
    return;
  }

  window.speechSynthesis.cancel();
  const cleanText = text.replace(/[*#_`]/g, '');
  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;
  utterance.onend = () => {
    state.speakingId = null;
    renderMessages();
  };
  utterance.onerror = () => {
    state.speakingId = null;
    renderMessages();
  };

  state.speakingId = id;
  renderMessages();
  window.speechSynthesis.speak(utterance);
}

// Copy to Clipboard Helper
function handleCopy(id, text) {
  navigator.clipboard.writeText(text);
  state.copiedId = id;
  renderMessages();
  setTimeout(() => {
    state.copiedId = null;
    renderMessages();
  }, 2000);
}

// Send Message Handler
async function sendMessage(textToSend) {
  const message = (textToSend || DOM.chatMessageInput.value).trim();
  if (!message || state.isLoading) return;

  audio.playHapticClick(450, 0.05);

  const userMsg = {
    id: `user-${Date.now()}`,
    role: 'user',
    content: message,
    timestamp: getISTFormattedTime()
  };

  state.messages.push(userMsg);
  DOM.chatMessageInput.value = '';
  renderMessages();

  state.isLoading = true;
  DOM.thinkingIndicator.classList.remove('hidden');
  DOM.messagesContainer.scrollTop = DOM.messagesContainer.scrollHeight;

  try {
    const historyPayload = state.messages.slice(-6).map((m) => ({
      role: m.role === 'user' ? 'user' : 'model',
      content: m.content
    }));

    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: userMsg.content,
        username: state.currentUser.username,
        email: state.currentUser.email,
        history: historyPayload
      })
    });

    if (!response.ok) throw new Error('Server response failed');

    const data = await response.json();
    audio.playChime(528, 1.0);

    const botMsg = {
      id: `bot-${Date.now()}`,
      role: 'assistant',
      content: data.reply || `${getGreeting()}, ${state.currentUser.username}! How else can I help?`,
      timestamp: getISTFormattedTime()
    };
    state.messages.push(botMsg);
  } catch {
    audio.playHapticClick(280);
    const fallbackMsg = {
      id: `bot-fb-${Date.now()}`,
      role: 'assistant',
      content: `⚠️ Could not reach Python backend server (port 8000). Please ensure server.py is running.`,
      timestamp: getISTFormattedTime()
    };
    state.messages.push(fallbackMsg);
  } finally {
    state.isLoading = false;
    DOM.thinkingIndicator.classList.add('hidden');
    renderMessages();
  }
}

DOM.chatInputForm.addEventListener('submit', (e) => {
  e.preventDefault();
  sendMessage();
});

// Quick Focus Suggestion Chips
document.querySelectorAll('.chip-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    const prompt = btn.getAttribute('data-prompt');
    if (prompt) {
      audio.playHapticClick(400);
      sendMessage(prompt);
    }
  });
});

// Initialize default Auth mode to 'signin'
setAuthMode('signin');

// Auto-restore previous user session if available
(function restoreSession() {
  try {
    const saved = localStorage.getItem('aether_session');
    if (saved) {
      const u = JSON.parse(saved);
      if (u && (u.username || u.email)) {
        enterChatbot(u.username, u.email);
      }
    }
  } catch {}
})();
