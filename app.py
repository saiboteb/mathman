import streamlit as st
import cv2
import numpy as np
from inference import get_model
from PIL import Image, ImageDraw

# --- 1. CONFIGURATION ---
# Replace with your actual Private API Key (starts with rf_)
API_KEY = "azLr1W9xyQ4Kp3Zenuqf" 
MODEL_ID = "playing-cards-ow27d/4"

# --- 2. THE BRAIN ---
@st.cache_resource
def load_math_man_brain():
    # This pulls the model from Roboflow and keeps it in memory
    return get_model(model_id=MODEL_ID, api_key=API_KEY)

model = load_math_man_brain()

# --- 3. SCORING LOGIC ---
def calculate_rummy_score(cards):
    """
    Rummy Math: 
    Faces (K, Q, J) = 10
    Aces = 15
    Numbers = Face Value
    """
    total = 0
    for card in cards:
        # Standard labels are usually '10S', 'KH', 'AS'
        # We take everything except the last character (the suit)
        rank = card[:-1].upper() 
        
        if rank in ['K', 'Q', 'J']:
            total += 10
        elif rank == 'A':
            total += 15
        elif rank.isdigit():
            total += int(rank)
    return total

# --- 4. THE UI (Neo-Brutalist Style) ---
st.set_page_config(page_title="Math Man", page_icon="🃏")
st.markdown("""
    <style>
    .stApp { background-color: #FFEB3B; color: black; font-family: 'Courier New', Courier, monospace; }
    .stButton>button { 
        border: 4px solid black !important; 
        box-shadow: 8px 8px 0px 0px #000 !important;
        background-color: #00E676 !important;
        color: black !important;
        font-weight: 900 !important;
        width: 100%;
    }
    .score-box {
        background-color: #3D5AFE;
        border: 5px solid black;
        box-shadow: 10px 10px 0px 0px #000;
        padding: 20px;
        color: white;
        text-align: center;
        margin-top: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🃏 MATH MAN v3.12")
st.write("### *'Show me the cards, Tobias.'*")

# --- 5. CAMERA INPUT ---
cam_image = st.camera_input("SCANNER ACTIVE")

if cam_image:
    # Convert camera stream to PIL Image
    image = Image.open(cam_image).convert("RGB")
    
    with st.spinner('MATH MAN IS CRUNCHING THE NUMBERS...'):
        # --- 6. INFERENCE (The AI part) ---
        # The SDK handles the API call and image processing automatically
        results = model.infer(image)[0]
        
        draw = ImageDraw.Draw(image)
        detected_cards = []
        
        for prediction in results.predictions:
            # Extract data from the SDK object
            label = prediction.class_name
            x, y, w, h = prediction.x, prediction.y, prediction.width, prediction.height
            detected_cards.append(label)
            
            # Math: Calculate box corners for drawing
            left, top, right, bottom = x - w/2, y - h/2, x + w/2, y + h/2
            
            # Draw Neo-Brutalist boxes (Black border + Green inner)
            draw.rectangle([left, top, right, bottom], outline="black", width=7)
            draw.rectangle([left, top, right, bottom], outline="#00E676", width=2)
            draw.text((left, top - 20), label, fill="black")

        # --- 7. FINAL CALCULATION ---
        score = calculate_rummy_score(detected_cards)

    # Display Result
    st.image(image, caption="MATH MAN'S VISION", use_container_width=True)
    
    st.markdown(f"""
        <div class="score-box">
            <h1 style="font-size: 80px; margin: 0;">{score}</h1>
            <p style="letter-spacing: 3px; font-weight: bold;">TOTAL RUMMY POINTS</p>
            <p style="font-size: 14px;">DETECTED: {', '.join(detected_cards) if detected_cards else 'NONE'}</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("LOG THIS ROUND"):
        st.balloons()