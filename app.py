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

cam_image = st.camera_input("SCANNER ACTIVE")

if cam_image:
    image = Image.open(cam_image).convert("RGB")
    
    with st.spinner('MATH MAN IS LISTING CARDS...'):
        # Keep confidence low (0.15) while we test accuracy
        results = model.infer(image, confidence=0.15)[0]
        
        draw = ImageDraw.Draw(image)
        detected_cards = []
        
        for prediction in results.predictions:
            label = prediction.class_name
            detected_cards.append(label)
            
            # Box Coordinates
            x, y, w, h = prediction.x, prediction.y, prediction.width, prediction.height
            left, top, right, bottom = x - w/2, y - h/2, x + w/2, y + h/2
            
            # Draw simple, clear boxes
            draw.rectangle([left, top, right, bottom], outline="#00E676", width=5)
            draw.text((left, top - 20), label, fill="white")

    # --- 6. DISPLAY LIST INSTEAD OF SCORE ---
    st.image(image, width='stretch')
    
    st.markdown("### 🗃️ Detected Inventory")
    
    if detected_cards:
        # Create a nice vertical list
        for i, card in enumerate(detected_cards, 1):
            st.write(f"**{i}.** {card}")
        
        st.info(f"Total Cards Found: {len(detected_cards)}")
    else:
        st.warning("No cards detected. Try adjusting the light or distance!")