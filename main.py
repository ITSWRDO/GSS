import streamlit as st

import os
from PIL import Image
import base64
import io
import json
import datetime
from openai import OpenAI

# --- 1. Page Configuration & UI Theme ---
st.set_page_config(
    page_title="NutriSnapAI", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Force Dark Mode (as specified in architectural preferences or common for mobile-first AI apps)
# but we will keep the light green accents.
st.session_state.theme = 'dark' 

theme_colors = {
    'dark': {
        'bg': '#0e1117',
        'card_bg': '#161b22',
        'text': '#f0f6fc',
        'subtext': '#8b949e',
        'border': '#30363d',
        'macro_bg': '#0d1117'
    }
}

tc = theme_colors['dark']

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    .stApp {{
        background-color: {tc['bg']};
        font-family: 'Inter', sans-serif;
        color: {tc['text']};
    }}

    .main .block-container {{
        max-width: 600px;
        padding-top: 1rem;
    }}

    .app-card {{
        background-color: {tc['card_bg']};
        border-radius: 24px;
        padding: 32px 24px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.05);
        border: 1px solid {tc['border']};
        text-align: center;
    }}

    .logo-text {{
        font-weight: 800;
        color: {tc['text']};
        letter-spacing: -1px;
        font-size: clamp(2.5rem, 8vw, 3.8rem);
    }}
    .logo-text span {{ color: #8eb384; }}

    .app-title {{
        font-size: 1.6rem;
        font-weight: 800;
        color: {tc['text']};
        margin-bottom: 8px;
    }}
    .app-subtitle {{
        font-size: 0.95rem;
        color: {tc['subtext']};
        margin-bottom: 32px;
    }}

    /* Snap Button Styling */
    .stButton>button {{
        width: 100%;
        height: 52px;
        border-radius: 12px;
        background-color: #8eb384 !important; 
        color: #000000 !important; 
        font-weight: 700;
        font-size: 1rem;
        border: none;
        box-shadow: 0 4px 12px rgba(142, 179, 132, 0.3);
        transition: all 0.2s;
        margin-top: 16px;
    }}

    .stButton>button:hover {{
        transform: translateY(-1px);
        filter: brightness(0.95);
    }}

    /* Specific fix for the Camera "Take Photo" button background and text */
    [data-testid="stCameraInput"] button {{
        background-color: #8eb384 !important;
        color: #000000 !important;
        border: none !important;
    }}

    /* Camera Input Styling */
    [data-testid="stCameraInput"] {{
        border: 2px dashed {tc['border']};
        border-radius: 16px;
        padding: 8px;
    }}

    /* Camera Label Styling - Force white per user request */
    [data-testid="stCameraInput"] label {{
        color: #ffffff !important;
        font-weight: 600;
        margin-bottom: 10px;
        text-shadow: 0px 0px 3px rgba(0,0,0,0.3);
    }}

    .macro-row {{
        display: flex;
        justify-content: space-between;
        background-color: {tc['macro_bg']};
        border-radius: 16px;
        padding: 15px;
        margin-bottom: 20px;
        border: 1px solid {tc['border']};
    }}
    .macro-val {{
        font-size: 1.2rem;
        font-weight: 800;
        color: {tc['text']};
    }}

    .report-box {{
        background-color: #e8f4e8;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 20px;
        border: 1px solid #d9ead3;
        color: #000000 !important;
        font-size: 0.9rem;
        font-style: italic;
    }}

    .health-score-pill {{
        display: inline-block;
        background: #d9ead3;
        color: #000000;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        margin-bottom: 12px;
        border: 1px solid rgba(0,0,0,0.1);
    }}

    /* File Uploader styling */
    [data-testid="stFileUploader"] button {{
        color: #000000 !important;
        background-color: #8eb384 !important;
        border: none !important;
        border-radius: 8px !important;
    }}

    /* Hide Streamlit Branding/Menu/Deploy */
    #MainMenu {{visibility: hidden;}}
    .stDeployButton {{display:none;}}
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 2. Configuration & Logic ---
# Prioritize the key provided by user, as the env var was found to be stale/invalid
API_KEY = "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"
BASE_URL = "https://openrouter.ai/api/v1"

HISTORY_FILE = "history.json"

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_history(username, entry):
    # Do not save history for the default Guest user
    if username == "Guest":
        return

    history = load_history()
    if username not in history:
        history[username] = []

    # Add timestamp
    entry['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    history[username].append(entry)

    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def process_image_fast(image_file):
    img = Image.open(image_file)
    img.thumbnail((800, 800))
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

if 'page' not in st.session_state:
    st.session_state.page = 'input'
if 'data' not in st.session_state:
    st.session_state.data = None

# --- 3. UI Layout ---

# Sidebar for History
with st.sidebar:
    st.title("👤 User Profile")
    username = st.text_input("Username", value="Guest", help="Enter your name to save/view history")

    st.divider()

    st.subheader("📜 Meal History")
    # Only show history if not Guest
    if username == "Guest":
        st.info("Log in with a username to track your meal history.")
    else:
        history_data = load_history()
        user_history = history_data.get(username, [])

        if not user_history:
            st.info("No meals tracked yet.")
        else:
            for item in reversed(user_history): # Show newest first
                with st.expander(f"{item.get('name', 'Meal')} - {item.get('timestamp')}"):
                    st.write(f"**Health Score:** {item.get('health_score')}/100")
                    st.write(f"**Calories:** {item.get('calories')}")
                    st.write(f"_{item.get('short_report')}_")


# Logo (centered)
st.markdown(f"""
    <div class="logo-container" style="display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 16px;">
        <svg style="width: 50px; height: 50px;" viewBox="0 0 24 24" fill="none" stroke="#8eb384" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.5 1.9 9.2A7 7 0 0 1 11 20z"></path><path d="M11 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"></path><path d="M11 20v-7"></path></svg>
        <div class="logo-text">Nutri<span>SnapAI</span></div>
    </div>
""", unsafe_allow_html=True)

if st.session_state.page == 'input':
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.markdown('<div class="app-title">Snap Your Meal</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Get an instant nutritional analysis of your food.</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📷 Take Photo", "📤 Upload"])

    image_to_process = None

    with tab1:
        # Reverted to standard camera input for UI consistency
        camera_photo = st.camera_input("Take a picture")
        if camera_photo:
            image_to_process = camera_photo

    with tab2:
        gallery_photo = st.file_uploader("Select an image from your device", type=["jpg", "jpeg", "png"], key="gallery_widget")
        if gallery_photo:
            image_to_process = gallery_photo

    if image_to_process:
        if st.button("Analyze Meal"):
            if not API_KEY:
                st.error("API Error: Missing credentials.")
            else:
                try:
                    with st.spinner("Calculating nutrients..."):
                        base64_image = process_image_fast(image_to_process)
                        prompt = (
                            "Analyze this image. First, determine if it is a food item suitable for consumption. "
                            "Provide a JSON object with: "
                            "is_food (boolean), "
                            "name, health_score (0-100, set to 0 if not food), calories (set to 0 if not food), "
                            "protein, carbs, fats, ingredients (list), health_summary, "
                            "short_report (a very concise 1-sentence summary of the food's health impact, or a witty remark if it's not food)."
                        )

                        client = OpenAI(
                            api_key=API_KEY, 
                            base_url=BASE_URL,
                            default_headers={
                                "HTTP-Referer": "http://localhost:8501", # Required by OpenRouter
                                "X-Title": "NutriSnapAI"
                            }
                        )

                        response = client.chat.completions.create(
                            model="google/gemini-2.0-flash-001",
                            messages=[{"role": "user", "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]}],
                            response_format={ "type": "json_object" },
                            temperature=0.1
                        )

                        data = json.loads(response.choices[0].message.content)
                        st.session_state.data = data

                        # Save to history
                        save_history(username, data)

                        st.session_state.page = 'results'
                        st.rerun()

                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")
                    # Debug advice if 401
                    if "401" in str(e):
                        st.info("ℹ️ Tip: A 401 error usually means your OpenRouter API Key is invalid, expired, or out of credits. Please check your dashboard at openrouter.ai/keys.")
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.page == 'results':
    data = st.session_state.data
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="app-title">{data.get("name", "Analysis Result")}</div>', unsafe_allow_html=True)

    is_food = data.get("is_food", True)

    st.markdown(f'<div class="report-box">{data.get("short_report", "")}</div>', unsafe_allow_html=True)

    if is_food:
        st.markdown(f'<div class="health-score-pill">HEALTH SCORE: {data.get("health_score", 0)}/100</div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div class="macro-row">
            <div class="macro-box">
                <div style="font-size: 0.75rem; font-weight: 600; opacity: 0.7;">CALORIES</div>
                <div class="macro-val">{data.get("calories", 0)}</div>
            </div>
            <div class="macro-box">
                <div style="font-size: 0.75rem; font-weight: 600; opacity: 0.7;">PROTEIN</div>
                <div class="macro-val">{data.get("protein", 0)}g</div>
            </div>
            <div class="macro-box">
                <div style="font-size: 0.75rem; font-weight: 600; opacity: 0.7;">CARBS</div>
                <div class="macro-val">{data.get("carbs", 0)}g</div>
            </div>
            <div class="macro-box">
                <div style="font-size: 0.75rem; font-weight: 600; opacity: 0.7;">FATS</div>
                <div class="macro-val">{data.get("fats", 0)}g</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="text-align: left; background: rgba(128, 128, 128, 0.03); border-radius: 16px; padding: 20px; border: 1px solid {tc['border']}; margin-top: 16px;">
        <b>Ingredients:</b><br>{', '.join(data.get('ingredients', [])) if isinstance(data.get('ingredients'), list) else data.get('ingredients', 'None')}<br><br>
        <b>AI Analysis:</b><br>{data.get('health_summary', '')}
    </div>
    """, unsafe_allow_html=True)

    if st.button("Snap Another Meal"):
        st.session_state.page = 'input'
        st.session_state.data = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
