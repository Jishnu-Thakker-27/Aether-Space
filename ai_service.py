import os
import re
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Global client cache to avoid expensive TLS/TCP reconnections on each prompt
_CLIENT_CACHE = None
_CACHED_API_KEY = None

# Primary ultra-fast models prioritized for sub-second and low-latency responses.
ALL_CANDIDATE_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-pro-latest"
]

_LAST_WORKING_MODEL = "gemini-3.1-flash-lite"

def _get_api_key() -> str | None:
    """Safely retrieves and cleans GEMINI_API_KEY from .env or environment."""
    env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_file):
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(override=True)

    key = os.getenv("GEMINI_API_KEY")
    if not key or key == "your_gemini_api_key_here":
        return None

    # Clean potential UTF-8 BOM, surrounding quotes, and whitespace
    clean_key = key.replace("\ufeff", "").strip().strip("'\"")
    return clean_key if clean_key else None

def _get_client():
    """Returns a cached, connection-pooled GenAI client."""
    global _CLIENT_CACHE, _CACHED_API_KEY
    api_key = _get_api_key()
    if not api_key:
        return None, None

    if _CLIENT_CACHE is None or _CACHED_API_KEY != api_key:
        _CLIENT_CACHE = genai.Client(api_key=api_key)
        _CACHED_API_KEY = api_key

    return _CLIENT_CACHE, api_key

def clean_ai_reply(text: str, user_message: str, display_name: str = "") -> str:
    """
    Cleans output so it matches the authentic, professional style of ChatGPT and Gemini:
    - Removes awkward personalizations from titles (e.g., '**Key Context for User:**' -> '**Key Context:**')
    - Strips raw markdown hashes (###)
    - Removes unnecessary repetitive greetings on factual questions ('Hello User!')
    """
    if not text:
        return text

    # 1. Normalize headings like "**Key Context for John Doe:**" -> "**Key Context:**"
    text = re.sub(
        r'\*\*([A-Za-z0-9\s]+?)\s+for\s+[A-Za-z0-9\s._-]+:\*\*',
        r'**\1:**',
        text,
        flags=re.IGNORECASE
    )

    # 2. If a specific display_name was passed, remove any residual "for <Name>" in headings/titles
    if display_name and display_name.lower() not in ["friend", "user", "guest"]:
        text = re.sub(
            rf'\s+for\s+{re.escape(display_name)}',
            '',
            text,
            flags=re.IGNORECASE
        )

    # 3. Strip any residual raw leading hash signs like "### " or "## " at start of lines
    text = re.sub(r'(?m)^#{1,6}\s*', '', text)

    # 4. If the user asked a factual/direct question (not a greeting like 'hi' or 'hello'),
    # and the model starts with an awkward greeting like "Hello Jishnu! " or "Hello Jishnu, I am Aether.",
    # strip that prefix so it reads naturally like ChatGPT and Gemini.
    msg_clean = user_message.strip().lower()
    is_user_greeting = any(msg_clean.startswith(g) for g in ["hi", "hello", "hey", "good morning", "good evening", "good afternoon"])
    if not is_user_greeting:
        text = re.sub(
            r'^(?:Hello|Hi|Hey)(?:\s+[A-Za-z0-9_]+(?:\s+[A-Za-z0-9_]+)?)?[!,.]\s*(?:I am Aether[!,.]\s*)?',
            '',
            text,
            flags=re.IGNORECASE
        ).strip()

    return text.strip()

def try_fast_instant_reply(message: str, display_name: str) -> str | None:
    """
    Sub-millisecond instant responder for pure conversational chit-chat, greetings,
    and bot capability questions. Does NOT intercept real questions (e.g., 'hi, what is 2+2?').
    """
    raw = message.strip()
    clean = raw.lower().rstrip("!?. ,")
    if not clean:
        return "Hello! How can I help you today?"

    first_name = display_name.strip().split()[0] if display_name and display_name.strip().lower() not in ["friend", "user", "guest"] else ""
    name_greet = f", {first_name}" if first_name else ""

    # Pure greetings
    if clean in ["hi", "hello", "hey", "hiya", "howdy", "heya", "greetings"]:
        return (
            f"Hello{name_greet}! 🌅 How can I help you today?\n\n"
            f"Feel free to ask questions, work on code, solve problems, or explore mindful focus routines."
        )

    # Time-based greetings
    if clean in ["good morning", "morning"]:
        return f"Good morning{name_greet}! ☀️ Wishing you a productive day. What are we diving into first?"
    if clean in ["good afternoon", "afternoon"]:
        return f"Good afternoon{name_greet}! 🌤️ Hope your day is going well. How can I help you right now?"
    if clean in ["good evening", "evening"]:
        return f"Good evening{name_greet}! 🌇 As the day winds down, how can I assist you?"
    if clean in ["good night", "night"]:
        return f"Good night{name_greet}! 🌙 Rest well. I'll be here whenever you're ready to pick back up."

    # Well-being questions
    if clean in ["how are you", "how are you doing", "how are things", "what's up", "whats up", "how's it going", "hows it going"]:
        return (
            f"I'm feeling focused and ready to assist{name_greet}! 😊\n\n"
            f"How is your day going? What would you like to work on or explore?"
        )

    # Identity and capability queries
    if clean in ["who are you", "what is your name", "whats your name", "who made you", "what are you"]:
        return (
            "I am **Aether**, an advanced AI companion in Aether Space.\n\n"
            "I can assist you with answering complex or simple questions, writing and debugging code, solving math problems, summarizing concepts, and exploring mindful study routines. What would you like to explore today?"
        )
    if clean in ["what can you do", "help", "what do you do", "commands", "menu"]:
        return (
            "Here is what I can help you with:\n\n"
            "* 💡 **Direct Questions & Explanations**: Science, history, philosophy, culture, and general knowledge\n"
            "* 💻 **Coding & Debugging**: Python, JavaScript, HTML/CSS, SQL, algorithms, and web tools\n"
            "* 📐 **Math & Problem Solving**: Step-by-step arithmetic, algebra, calculus, and logic\n"
            "* 🎧 **Sound & Focus**: Built-in 432Hz ambient soundscape synthesis for deep work\n"
            "* 📝 **Writing & Summarizing**: Outlines, drafts, essays, and notes\n\n"
            "Just ask whatever is on your mind!"
        )

    # Appreciation
    if clean in ["thank you", "thanks", "thanks a lot", "thank you so much", "thx", "ty"]:
        return f"You're very welcome{name_greet}! Let me know if you need anything else. ✨"

    if clean in ["bye", "goodbye", "cya", "see you", "see ya"]:
        return f"Goodbye for now{name_greet}! Have a great rest of your day! 🚀"

    return None

def generate_fallback_reply(message: str, display_name: str) -> str:
    """Provides a warm, mindful fallback response if Gemini API is unreachable."""
    lower_msg = message.lower().strip()

    if any(g in lower_msg for g in ["hello", "hi", "hey", "morning", "evening", "afternoon"]):
        return "Hello! How can I support your thoughts, day planning, or studies today?"

    if any(w in lower_msg for w in ["focus", "study", "work", "task", "project", "pomodoro"]):
        return "Deep focus begins by setting gentle boundaries with distractions. Would you like to set a 25-minute Pomodoro timer, or break down your main goal into 3 clear steps?"

    if any(w in lower_msg for w in ["meditat", "breath", "calm", "anxious", "stress", "relax"]):
        return "Let's take a slow breath together. Inhale deeply through your nose for 4 seconds, hold gently for 4, and softly release for 6. Every breath is a reset. What's on your mind?"

    if any(w in lower_msg for w in ["music", "sound", "spatial", "audio", "432"]):
        return "Sound deeply influences our nervous system. I recommend tuning into 432Hz ambient frequencies to ground your attention while studying or relaxing!"

    # Informative response when offline
    return (
        f"I hear you asking: \"{message}\".\n\n"
        f"My cloud connection to the Gemini API is momentarily offline or unreachable. "
        f"Please check your internet connection or verify that `GEMINI_API_KEY` is configured in your `.env` file, and I'll jump right back in with complete answers!"
    )

def build_chat_contents(message: str, history: list = None) -> list[types.Content]:
    """
    Constructs clean, alternating multi-turn types.Content turns for Gemini.
    Deduplicates consecutive turns and trims trailing duplicate user prompts.
    """
    contents = []

    if history and isinstance(history, list):
        cleaned_history = []
        for item in history:
            if not isinstance(item, dict):
                continue
            role = "user" if item.get("role") == "user" else "model"
            text = (item.get("content") or "").strip()
            if not text:
                continue

            # Merge consecutive messages from same role to maintain strict alternation
            if cleaned_history and cleaned_history[-1]["role"] == role:
                cleaned_history[-1]["text"] += f"\n{text}"
            else:
                cleaned_history.append({"role": role, "text": text})

        # If the last history item is already this exact user prompt, avoid repeating it
        if cleaned_history and cleaned_history[-1]["role"] == "user" and cleaned_history[-1]["text"] == message.strip():
            cleaned_history.pop()

        # Keep last 6 conversational turns (3 exchanges) for ultra-fast, low-latency context
        for item in cleaned_history[-6:]:
            contents.append(
                types.Content(
                    role=item["role"],
                    parts=[types.Part.from_text(text=item["text"])]
                )
            )

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=message.strip())]
        )
    )
    return contents

def get_ai_response(message: str, display_name: str = "Friend", history: list = None) -> tuple[str, str]:
    """
    Sends message + multi-turn context to Google Gemini API with high-speed connection reuse.
    Returns: (reply_text, source) where source is 'instant', 'gemini' or 'fallback'.
    """
    global _LAST_WORKING_MODEL

    # 1. Fast-path check: instant response for simple greetings / conversational questions
    fast_reply = try_fast_instant_reply(message, display_name)
    if fast_reply is not None:
        return fast_reply, "instant"

    # 2. Gemini API Client
    client, api_key = _get_client()

    if not client or not api_key:
        print("[Gemini Notice] GEMINI_API_KEY not configured or empty. Using fallback.")
        return generate_fallback_reply(message, display_name), "fallback"

    try:
        system_instruction = (
            "You are Aether, an advanced, highly capable AI assistant matching the natural, polished style of state-of-the-art conversational AI like ChatGPT and Gemini.\n\n"
            "Crucial Guidelines:\n"
            "1. Direct & Natural: Jump straight into the answer without repetitive greetings ('Hello [User]!') or preamble unless the user specifically greeted you. Never refer to yourself as 'As an AI' or 'As Aether'.\n"
            "2. No Awkward Personalization: NEVER inject or append the user's name into section titles, headers, bullet points, or summaries (e.g. NEVER write 'Key Context for [Name]:' or 'Takeaways for [Name]:' — simply write 'Key Context:' or 'Overview:'). Do not repeat the user's name.\n"
            "3. Heading Formatting: Do NOT use markdown hash signs (#, ##, ###) for section headers. Use bold text for titles and section headings (e.g., **1. The Allied Powers**).\n"
            "4. Clean Markdown: Structure answers with crisp paragraphs, bold labels, clean bullet points, numbered lists, and fenced code blocks with language tags when showing code.\n"
            "5. Depth & Tone: Be concise for simple questions, and structured, objective, and thorough for complex inquiries."
        )

        gen_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
            max_output_tokens=700,
        )

        # Prioritize the model that succeeded previously for lowest possible latency
        candidate_models = [_LAST_WORKING_MODEL] + [m for m in ALL_CANDIDATE_MODELS if m != _LAST_WORKING_MODEL]

        structured_contents = build_chat_contents(message, history)

        # Flat string fallback prompt in case structured contents schema is rejected
        flat_prompt = "\n".join([
            f"{c.role}: {' '.join([p.text for p in c.parts if hasattr(p, 'text') and p.text])}"
            for c in structured_contents
        ])

        # Attempt call across candidate models
        for attempt in range(2):
            for model_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=structured_contents,
                        config=gen_config,
                    )
                    reply = response.text
                    if reply and reply.strip():
                        _LAST_WORKING_MODEL = model_name
                        cleaned_reply = clean_ai_reply(reply, message, display_name)
                        return cleaned_reply, "gemini"
                except Exception as err:
                    err_msg = str(err)
                    # If structured contents had an issue, attempt flat prompt with this model
                    if "contents" in err_msg.lower() or "role" in err_msg.lower():
                        try:
                            response = client.models.generate_content(
                                model=model_name,
                                contents=flat_prompt,
                                config=gen_config,
                            )
                            reply = response.text
                            if reply and reply.strip():
                                _LAST_WORKING_MODEL = model_name
                                cleaned_reply = clean_ai_reply(reply, message, display_name)
                                return cleaned_reply, "gemini"
                        except Exception:
                            pass
                    print(f"[Gemini Notice] Model {model_name} unavailable: {err_msg[:60]}... Trying next...")
                    continue

            # Short backoff before second attempt if all models experienced temporary spikes
            if attempt == 0:
                time.sleep(0.2)

    except Exception as e:
        print(f"[Gemini API Error] {e}")

    # Mindful fallback if all API calls were unreachable
    return generate_fallback_reply(message, display_name), "fallback"

