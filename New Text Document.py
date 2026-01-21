import streamlit as st
import os
from PIL import Image
import base64
import io
import json
from openai import OpenAI

# --- 1. Page Configuration & Mobile Optimization ---
st.set_page_config(
    page_title="VisionAI", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for standard Streamlit layout (Non-immersive)
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    
    /* Result Styling */
    .results-container {
        background: #1c1c1e;
        border-radius: 20px;
        padding: 20px;
        margin-top: 20px;
        border: 1px solid #30363d;
    }

    .food-header {
        text-align: center;
        color: white;
        font-weight: 800;
        font-size: 1.6rem;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
    }
    
    .health-badge {
        background: linear-gradient(90deg, #238636 0%, #2ea043 100%);
        padding: 12px;
        border-radius: 15px;
        text-align: center;
        color: white;
        font-weight: 800;
        margin: 1rem 0;
    }
    
    .macro-container {
        background: #2c2c2e;
        padding: 15px;
        border-radius: 15px;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }
    
    .macro-item { text-align: center; color: #a1a1a6; font-size: 0.7rem; }
    .macro-value { color: white; font-weight: 800; font-size: 1.1rem; display: block; }

    .stButton>button { 
        width: 100%; 
        height: 3.5rem;
        border-radius: 12px; 
        background-color: #238636; 
        color: white; 
        font-weight: 700;
        border: none;
    }
    
    /* Hide default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. Configuration ---
AI_INTEGRATIONS_OPENROUTER_API_KEY = os.environ.get("AI_INTEGRATIONS_OPENROUTER_API_KEY")
AI_INTEGRATIONS_OPENROUTER_BASE_URL = os.environ.get("AI_INTEGRATIONS_OPENROUTER_BASE_URL")

def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# Initialize session state for page management
if 'page' not in st.session_state:
    st.session_state.page = 'input'
if 'data' not in st.session_state:
    st.session_state.data = None

# --- 3. Page Logic ---

if st.session_state.page == 'input':
    st.title("VisionAI")
    
    # Use tabs for selection
    tab1, tab2 = st.tabs(["📷 Camera", "📁 Gallery"])

    image_to_process = None

    with tab1:
        # Check camera input
        camera_photo = st.camera_input("Take a photo", key="camera_widget")
        if camera_photo:
            image_to_process = camera_photo
    
    with tab2:
        # Check gallery input
        gallery_photo = st.file_uploader("Upload from gallery", type=["jpg", "jpeg", "png"], key="gallery_widget")
        if gallery_photo:
            image_to_process = gallery_photo

    # Only process if we have an image AND it's a new interaction
    if image_to_process:
        img = Image.open(image_to_process)
        
        if not AI_INTEGRATIONS_OPENROUTER_API_KEY:
            st.error("API Error: Missing credentials.")
            st.stop()

        try:
            with st.spinner("Analyzing meal..."):
                base64_image = encode_image(img)
                prompt = (
                    "Analyze this food image. Return a JSON OBJECT. "
                    "Fields: name, health_score (0-100), calories (int), protein (int), carbs (int), fats (int), ingredients (list), health_summary. "
                )

                client = OpenAI(
                    api_key=AI_INTEGRATIONS_OPENROUTER_API_KEY,
                    base_url=AI_INTEGRATIONS_OPENROUTER_BASE_URL
                )
                
                response = client.chat.completions.create(
                    model="google/gemini-2.0-flash-001",
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]}],
                    response_format={ "type": "json_object" }
                )
                
                raw_content = response.choices[0].message.content
                parsed_data = json.loads(raw_content)
                
                if isinstance(parsed_data, list):
                    parsed_data = parsed_data[0]
                
                if isinstance(parsed_data, dict):
                    st.session_state.data = parsed_data
                    st.session_state.page = 'results'
                    st.rerun()

        except Exception as e:
            st.error(f"Analysis failed. Please try again.")

elif st.session_state.page == 'results':
    data = st.session_state.data
    
    if data:
        h_score = data.get("health_score", 0)
        if 0 < h_score <= 10:
            h_score *= 10
            
        st.markdown(f"""
            <div class="results-container">
                <div class="food-header">{data.get("name", "Dish")}</div>
                <div class="health-badge">HEALTH SCORE: {h_score}/100</div>
                <div class="macro-container">
                    <div class="macro-item"><span class="macro-value">{data.get("calories", "0")}</span>CALS</div>
                    <div class="macro-item"><span class="macro-value">{data.get("protein", "0")}G</span>PROT</div>
                    <div class="macro-item"><span class="macro-value">{data.get("carbs", "0")}G</span>CARBS</div>
                    <div class="macro-item"><span class="macro-value">{data.get("fats", "0")}G</span>FATS</div>
                </div>
                <div style="color: #e6edf3; font-size: 0.95rem; line-height: 1.6; margin-bottom: 25px;">
                    <b style="color: #58a6ff; text-transform: uppercase; font-size: 0.8rem;">Ingredients:</b><br>{", ".join(data.get("ingredients", []))}<br><br>
                    <b style="color: #58a6ff; text-transform: uppercase; font-size: 0.8rem;">Analysis:</b><br>{data.get("health_summary", "")}
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("NEW ANALYSIS"):
            # Clear state and reset
            for key in ["camera_widget", "gallery_widget"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.page = 'input'
            st.session_state.data = None
            st.rerun()
    else:
        st.session_state.page = 'input'
        st.rerun()
