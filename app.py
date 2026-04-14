import os
import streamlit as st
import streamlit.components.v1 as components
from collections import Counter

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="should we score", layout="centered")

if "ROBOFLOW_API_KEY" in st.secrets:
    API_KEY = st.secrets["ROBOFLOW_API_KEY"]
else:
    st.error("missing api key.")
    st.stop()

# --- 2. THE DECK & MATH DICTIONARIES ---
SUITS = {'S': 'Spades', 'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs'}
RANKS = {'2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', '10': '10', 'J': 'Jack', 'Q': 'Queen', 'K': 'King', 'A': 'Ace'}
FULL_DECK = [f"{r}{s}" for r in RANKS.keys() for s in SUITS.keys()]

def get_card_info(card_code):
    """Translates '10D' to '10 of Diamonds' and calculates standard score."""
    if not card_code or len(card_code) < 2:
        return "Unknown", 0
        
    rank_code = card_code[:-1].upper()
    suit_code = card_code[-1].upper()
    
    name = f"{RANKS.get(rank_code, rank_code)} of {SUITS.get(suit_code, suit_code)}"
    score = 0
    
    # Hardcoded Standard Scoring
    if rank_code == 'A': score = 1
    elif rank_code == 'J': score = 11
    elif rank_code == 'Q': score = 12
    elif rank_code == 'K': score = 13
    elif rank_code.isdigit(): score = int(rank_code)
        
    return name, score

def process_scan_history(history):
    """
    Temporal Persistence Algorithm: 
    Calculates the exact frequency of every card across all frames to filter out AI hallucinations.
    """
    if not history: 
        return []
        
    total_frames = len(history)
    if total_frames == 0: 
        return []

    # Flatten the history into one giant list of every card seen in every frame
    all_cards = [card for frame in history for card in frame]
    
    # Count the total occurrences of each card
    card_counts = Counter(all_cards)
    
    final_hand = []
    
    for card, total_count in card_counts.items():
        # Divide by total frames to get the average appearances per frame
        # e.g., if total_frames=20 and '10D' appeared 18 times -> 0.9 appearances per frame
        avg_appearance = total_count / total_frames
        
        # Round to the nearest whole number. 
        # 0.9 rounds to 1 card. 0.15 (a glitch) rounds to 0 cards. 
        # 1.8 (holding two of the same card) rounds to 2 cards.
        quantity = round(avg_appearance)
        
        # Add that exact quantity of the card to our final hand
        final_hand.extend([card] * quantity)
        
    return final_hand

# --- 3. STATE MACHINE ---
if 'stage' not in st.session_state: st.session_state.stage = 'setup'
if 'players' not in st.session_state: st.session_state.players = [] 
if 'scores' not in st.session_state: st.session_state.scores = {}
if 'turn_index' not in st.session_state: st.session_state.turn_index = 0
if 'scanned_cards' not in st.session_state: st.session_state.scanned_cards = []
if 'scan_key' not in st.session_state: st.session_state.scan_key = 0 
if 'round_number' not in st.session_state: st.session_state.round_number = 1

def reset_game():
    st.session_state.stage = 'setup'
    st.session_state.players = []
    st.session_state.scores = {}
    st.session_state.turn_index = 0
    st.session_state.scanned_cards = []
    st.session_state.round_number = 1

# --- SIDEBAR RESET ---
with st.sidebar:
    st.write("### Game Controls")
    if st.button("Restart Entire Game", type="secondary", use_container_width=True):
        reset_game()
        st.rerun()

# --- 4. THE API BRIDGE (V8) ---
BRIDGE_DIR = "scanner_bridge_v8"
os.makedirs(BRIDGE_DIR, exist_ok=True)

html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ margin: 0; font-family: sans-serif; background: #FAFAFA; display: flex; flex-direction: column; align-items: center; }}
        #container {{ position: relative; width: 100%; max-width: 500px; border-radius: 12px; overflow: hidden; background: #000; aspect-ratio: 4/3; }}
        video, canvas {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }}
        button {{ width: 100%; max-width: 500px; padding: 18px; margin-top: 15px; background: #111; color: #fff; border: none; border-radius: 10px; font-weight: bold; cursor: pointer; font-size: 16px; transition: 0.3s; }}
        #debug-log {{ width: 100%; max-width: 480px; height: 120px; margin-top: 10px; background: #1e1e1e; color: #00ff00; font-family: monospace; font-size: 11px; padding: 10px; border-radius: 8px; overflow-y: auto; text-align: left; display: none; }}
    </style>
</head>
<body>
    <div id="container">
        <video id="video" autoplay playsinline muted></video>
        <canvas id="canvas"></canvas>
    </div>
    <button id="scanBtn" onclick="toggleScan()">START SCAN</button>
    <div id="debug-log">System Booting...<br></div>

    <script>
        const video = document.getElementById("video");
        const canvas = document.getElementById("canvas");
        const ctx = canvas.getContext("2d");
        const btn = document.getElementById("scanBtn");
        const debugLog = document.getElementById("debug-log");
        
        let scanHistory = [];
        let isScanning = false;
        
        const hiddenCanvas = document.createElement("canvas");
        const hiddenCtx = hiddenCanvas.getContext("2d");
        hiddenCanvas.width = 640; hiddenCanvas.height = 640;

        function log(msg) {{
            const time = new Date().toLocaleTimeString();
            debugLog.innerHTML = `[${{time}}] ${{msg}}<br>` + debugLog.innerHTML;
        }}

        function sendToStreamlit(type, data) {{
            window.parent.postMessage({{ isStreamlitMessage: true, type: type, ...data }}, "*");
        }}

        window.onload = function() {{
            sendToStreamlit("streamlit:componentReady", {{ apiVersion: 1 }});
            sendToStreamlit("streamlit:setFrameHeight", {{ height: 600 }}); // slightly shorter without debug log showing
        }};

        navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: "environment" }} }})
            .then(s => {{ video.srcObject = s; log("Camera active. Ready."); }})
            .catch(e => log("Camera Error: " + e.message));

        setInterval(() => {{
            if (video.readyState === 4 && isScanning) {{
                hiddenCtx.drawImage(video, 0, 0, hiddenCanvas.width, hiddenCanvas.height);
                const dataURL = hiddenCanvas.toDataURL("image/jpeg", 0.7);
                const base64Data = dataURL.split(",")[1];

                fetch("https://detect.roboflow.com/playing-cards-ow27d/4?api_key={API_KEY}", {{
                    method: "POST", headers: {{ "Content-Type": "application/x-www-form-urlencoded" }}, body: base64Data
                }})
                .then(response => response.json())
                .then(data => {{
                    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    let currentFrameCards = [];
                    
                    if (data.predictions && data.predictions.length > 0) {{
                        log(`Frame captured: ${{data.predictions.length}} cards.`);
                        data.predictions.forEach(p => {{
                            const scaleX = canvas.width / 640; const scaleY = canvas.height / 640;
                            const x = p.x * scaleX; const y = p.y * scaleY;
                            const w = p.width * scaleX; const h = p.height * scaleY;
                            ctx.strokeStyle = "#10B981"; ctx.lineWidth = 4;
                            ctx.strokeRect(x - w/2, y - h/2, w, h);
                            currentFrameCards.push(p.class);
                        }});
                    }} else {{ log("Frame captured: 0 cards."); }}
                    scanHistory.push(currentFrameCards);
                }}).catch(err => log("API Error: " + err.message));
            }}
        }}, 400);

        function toggleScan() {{
            if (!isScanning) {{
                isScanning = true; scanHistory = [];
                btn.innerText = "STOP SCAN & REVIEW"; btn.style.backgroundColor = "#FF4B4B";
                log("--- RECORDING CARD HISTORY ---");
            }} else {{
                isScanning = false; ctx.clearRect(0, 0, canvas.width, canvas.height);
                btn.innerText = "START SCAN"; btn.style.backgroundColor = "#111";
                log("--- STREAM STOPPED ---");
                sendToStreamlit("streamlit:setComponentValue", {{ value: scanHistory }});
            }}
        }}
    </script>
</body>
</html>
"""

with open(os.path.join(BRIDGE_DIR, "index.html"), "w", encoding="utf-8") as f:
    f.write(html_code)

card_scanner = components.declare_component("card_scanner_v8", path=BRIDGE_DIR)

# --- 5. UI STYLE ---
st.markdown("""
    <style>
    .stApp { background-color: #FAFAFA; font-family: sans-serif; }
    h1, h2, h3 { font-weight: 300; }
    .card-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
    .total-row { display: flex; justify-content: space-between; padding: 12px 0; font-weight: bold; font-size: 20px; border-top: 2px solid #111; margin-top: 10px; }
    .leaderboard-row { display: flex; justify-content: space-between; padding: 15px; background-color: #fff; border: 1px solid #eaeaea; border-radius: 8px; margin-bottom: 10px; font-size: 18px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .leaderboard-name { font-weight: bold; }
    </style>
""", unsafe_allow_html=True)


# --- 6. PAGE 1: SETUP ---
if st.session_state.stage == 'setup':
    st.title("should we score")
    
    new_player = st.text_input("add player", placeholder="enter name...", key="name_input")
    if st.button("add") and new_player:
        if new_player not in st.session_state.players:
            st.session_state.players.append(new_player)
            st.session_state.scores[new_player] = 0
            st.rerun()

    if st.session_state.players:
        st.write("### roster")
        for p in st.session_state.players:
            st.write(f"- {p}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("START GAME", type="primary", use_container_width=True):
            st.session_state.stage = 'scan'
            st.rerun()


# --- 7. PAGE 2: SCANNING ---
elif st.session_state.stage == 'scan':
    current_player = st.session_state.players[st.session_state.turn_index]
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"{current_player}'s turn")
        st.caption(f"Round {st.session_state.round_number}")
    with col2:
        st.metric("Total", st.session_state.scores[current_player])
        
    st.write("point camera at the cards.")

    raw_history = card_scanner(key=f"scanner_instance_{st.session_state.scan_key}")

    if raw_history is not None and isinstance(raw_history, list):
        final_cards = process_scan_history(raw_history)
        st.session_state.scanned_cards = final_cards
        st.session_state.stage = 'edit'
        st.rerun()


# --- 8. PAGE 3: EDIT & CONFIRM ---
elif st.session_state.stage == 'edit':
    current_player = st.session_state.players[st.session_state.turn_index]
    st.title("review hand")
    
    st.write("add or remove cards if the ai made a mistake:")
    edited_cards = st.multiselect(
        "Inventory", 
        options=FULL_DECK, 
        default=st.session_state.scanned_cards,
        format_func=lambda x: get_card_info(x)[0],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    st.write("### score breakdown")
    total_score = 0
    
    for code in edited_cards:
        name, score = get_card_info(code)
        total_score += score
        st.markdown(f"<div class='card-row'><span>{name}</span><span>+{score}</span></div>", unsafe_allow_html=True)
        
    st.markdown(f"<div class='total-row'><span>Total</span><span>{total_score}</span></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("CONFIRM SCORE", type="primary", use_container_width=True):
        st.session_state.scores[current_player] += total_score
        
        st.session_state.turn_index += 1
        st.session_state.scanned_cards = []
        st.session_state.scan_key += 1
        
        # Check if the round is over
        if st.session_state.turn_index >= len(st.session_state.players):
            st.session_state.turn_index = 0 
            st.session_state.stage = 'overview' # Move to Leaderboard!
        else:
            st.session_state.stage = 'scan' # Move to next player
            
        st.rerun()
        
    if st.button("Cancel & Rescan", use_container_width=True):
        st.session_state.scanned_cards = []
        st.session_state.scan_key += 1
        st.session_state.stage = 'scan'
        st.rerun()


# --- 9. PAGE 4: ROUND OVERVIEW ---
elif st.session_state.stage == 'overview':
    st.title("round complete")
    st.write("### leaderboard")
    
    # Sort players by score (highest to lowest)
    sorted_scores = sorted(st.session_state.scores.items(), key=lambda item: item[1], reverse=True)
    
    for i, (player, score) in enumerate(sorted_scores):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else ""
        st.markdown(f"<div class='leaderboard-row'><span class='leaderboard-name'>{medal} {player}</span><span>{score} pts</span></div>", unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("START NEXT ROUND", type="primary", use_container_width=True):
        st.session_state.round_number += 1
        st.session_state.stage = 'scan'
        st.rerun()
        
    if st.button("End Game & Start Over", use_container_width=True):
        reset_game()
        st.rerun()
