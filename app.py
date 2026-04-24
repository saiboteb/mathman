import os
import streamlit as st
import streamlit.components.v1 as components
from collections import Counter

st.set_page_config(page_title="should we score", layout="centered", initial_sidebar_state="collapsed")

if "ROBOFLOW_API_KEY" in st.secrets:
    api_key = st.secrets["ROBOFLOW_API_KEY"]
else:
    st.error("missing api key")
    st.stop()

# suits, ranks, deck (all lower case) + for 500
suits = {'s': 'spades', 'h': 'hearts', 'd': 'diamonds', 'c': 'clubs'}
ranks = {'2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', '10': '10', 'j': 'jack', 'q': 'queen', 'k': 'king', 'a': 'ace'}
full_deck = [f"{r}{s}" for r in ranks.keys() for s in suits.keys()]
all_cards_with_jokers = full_deck + ["joker", "joker2"]

# For 500 mode options
suit_options = ['spades', 'hearts', 'diamonds', 'clubs', 'no trumps']
bid_options = [str(i) for i in range(6, 11)] + ["misère"]

# 500 bid scoring table as (suit, bid) => score
fivehundred_score_table = {
    # spades
    ("spades", "6"): 40, ("spades", "7"): 140, ("spades", "8"): 240, ("spades", "9"): 340, ("spades", "10"): 440,
    # clubs
    ("clubs", "6"): 60, ("clubs", "7"): 160, ("clubs", "8"): 260, ("clubs", "9"): 360, ("clubs", "10"): 460,
    # diamonds
    ("diamonds", "6"): 80, ("diamonds", "7"): 180, ("diamonds", "8"): 280, ("diamonds", "9"): 380, ("diamonds", "10"): 480,
    # hearts
    ("hearts", "6"): 100, ("hearts", "7"): 200, ("hearts", "8"): 300, ("hearts", "9"): 400, ("hearts", "10"): 500,
    # no trumps
    ("no trumps", "6"): 120, ("no trumps", "7"): 220, ("no trumps", "8"): 320, ("no trumps", "9"): 420, ("no trumps", "10"): 520,
    # misère
    ("", "misère"): 250,
}

def get_500_possible_scores(suit_options, bid_options):
    result = []
    for suit in suit_options:
        for bid in bid_options:
            if bid == "misère":
                result.append((suit, bid, fivehundred_score_table.get(("", bid), None)))
            else:
                score = fivehundred_score_table.get((suit, bid), None)
                if score is not None:
                    result.append((suit, bid, score))
    return result

def get_500_score(suit, bid):
    if bid == "misère":
        return fivehundred_score_table.get(("", "misère"), 250)
    return fivehundred_score_table.get((suit, bid), 0)

def get_card_info(card_code, game_mode):
    if not card_code or len(card_code) < 2:
        if card_code and "joker" in card_code.lower():
            return "joker", 0
        return "unknown", 0

    card = card_code.lower()
    if "joker" in card:
        name = "joker"
        score = 0
        if game_mode == "gin":
            score = 30
        if game_mode == "dutch":
            score = 0
        return name, score

    if len(card) >= 3 and card[:-1] == '10':
        rank_code, suit_code = '10', card[-1]
    else:
        rank_code, suit_code = card[:-1], card[-1]
    name = f"{ranks.get(rank_code, rank_code)} of {suits.get(suit_code, suit_code)}"
    score = 0

    if game_mode == "face value":
        if rank_code in ['j','q','k']:
            score = 10
        elif rank_code == 'a':
            score = 1
        elif rank_code.isdigit():
            score = int(rank_code)
    elif game_mode == "gin":
        if rank_code in ['a']:
            score = 1
        elif rank_code in ['j', 'q', 'k']:
            score = 10
        elif rank_code.isdigit():
            score = int(rank_code)
    elif game_mode == "yaniv":
        if rank_code in ['j', 'q', 'k']:
            score = 10
        elif rank_code == 'a':
            score = 1
        elif rank_code.isdigit():
            score = int(rank_code)
    elif game_mode == "dutch":
        if "joker" in card:
            score = 0
        elif rank_code == 'k' and suit_code in ['s','c']:   # black king
            score = -1
        elif rank_code == 'a':
            score = 1
        elif rank_code.isdigit():
            score = int(rank_code)
        else:
            score = 10
    else:
        score = 0

    return name, score

def process_scan_history(history):
    if not history: return []
    total_frames = len(history)
    all_cards = [card for frame in history for card in frame]
    card_counts = Counter([c.lower() for c in all_cards])
    final_hand = []
    for card, total_count in card_counts.items():
        quantity = round(total_count / total_frames)
        final_hand.extend([card] * quantity)
    return final_hand

# --- state ---
if 'stage' not in st.session_state: st.session_state.stage = 'setup'
if 'teams' not in st.session_state: st.session_state.teams = []
if 'team_scores' not in st.session_state: st.session_state.team_scores = {}
if 'players' not in st.session_state: st.session_state.players = []
if 'scores' not in st.session_state: st.session_state.scores = {}
if 'scanned_cards' not in st.session_state: st.session_state.scanned_cards = []
if 'scan_key' not in st.session_state: st.session_state.scan_key = 0
if 'game_mode' not in st.session_state: st.session_state.game_mode = "face value"
if 'scoring_mode' not in st.session_state: st.session_state.scoring_mode = 'automatic' # 'manual' or 'automatic'
if 'fivehundred_suit' not in st.session_state: st.session_state.fivehundred_suit = suit_options[0]
if 'fivehundred_bid' not in st.session_state: st.session_state.fivehundred_bid = bid_options[0]
if 'fivehundred_bidder' not in st.session_state: st.session_state.fivehundred_bidder = st.session_state.players[0] if st.session_state.players else ""
if 'fivehundred_num_won' not in st.session_state: st.session_state.fivehundred_num_won = int(bid_options[0])
if 'confirm_home_warning' not in st.session_state: st.session_state.confirm_home_warning = False
if 'winner' not in st.session_state: st.session_state.winner = None
if 'loser' not in st.session_state: st.session_state.loser = None

MAX_TEAMS = 2

# --- cam bridge (still required) ---
bridge_dir = "scanner_bridge_v10"
os.makedirs(bridge_dir, exist_ok=True)

html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ margin: 0; display: flex; flex-direction: column; align-items: center; background: #fff; color: #111; }}
        #container {{ position: relative; width: 100%; max-width: 500px; border-radius: 0; overflow: hidden; background: #000; aspect-ratio: 4/3; }}
        video, canvas {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; }}
        button {{ width: 100%; max-width: 500px; padding: 18px; margin-top: 15px; background: #ccc; color: #111; border: none; border-radius: 0; font-size: 16px; }}
    </style>
</head>
<body>
    <div id="container"><video id="video" autoplay playsinline muted></video><canvas id="canvas"></canvas></div>
    <button id="scanBtn" onclick="toggleScan()">scan</button>
    <script>
        const video = document.getElementById("video"); const canvas = document.getElementById("canvas"); const ctx = canvas.getContext("2d"); const btn = document.getElementById("scanBtn");
        let scanHistory = []; let isScanning = false;
        const hiddenCanvas = document.createElement("canvas"); const hiddenCtx = hiddenCanvas.getContext("2d"); hiddenCanvas.width = 640; hiddenCanvas.height = 640;

        window.onload = () => {{ window.parent.postMessage({{isStreamlitMessage: true, type: "streamlit:componentReady", apiVersion: 1}}, "*"); window.parent.postMessage({{isStreamlitMessage: true, type: "streamlit:setFrameHeight", height: 640}}, "*"); }};

        navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: "environment" }} }})
            .then(s => video.srcObject = s).catch(e => console.log(e));

        setInterval(() => {{
            if (video.readyState === 4 && isScanning) {{
                hiddenCtx.drawImage(video, 0, 0, 640, 640);
                const b64 = hiddenCanvas.toDataURL("image/jpeg", 0.7).split(",")[1];
                fetch("https://detect.roboflow.com/playing-cards-ow27d/4?api_key={api_key}&confidence=60&overlap=30", {{ method: "POST", headers: {{"Content-Type": "application/x-www-form-urlencoded"}}, body: b64 }})
                .then(r => r.json()).then(data => {{
                    canvas.width = video.videoWidth; canvas.height = video.videoHeight; ctx.clearRect(0, 0, canvas.width, canvas.height);
                    let currentFrameCards = [];
                    if (data.predictions && data.predictions.length > 0) {{
                        data.predictions.forEach(p => {{
                            ctx.strokeStyle = "#ccc"; ctx.lineWidth = 2;
                            ctx.strokeRect(p.x * (canvas.width/640) - (p.width * (canvas.width/640))/2, p.y * (canvas.height/640) - (p.height * (canvas.height/640))/2, p.width * (canvas.width/640), p.height * (canvas.height/640));
                            currentFrameCards.push(p.class);
                        }});
                    }}
                    scanHistory.push(currentFrameCards);
                }});
            }}
        }}, 400);

        function toggleScan() {{
            if (!isScanning) {{
                isScanning = true; scanHistory = [];
                btn.innerText = "stop and send"; btn.style.backgroundColor = "#eee"; btn.style.color = "#000";
            }} else {{
                isScanning = false; ctx.clearRect(0, 0, canvas.width, canvas.height);
                btn.innerText = "scan"; btn.style.backgroundColor = "#ccc"; btn.style.color = "#111";
                window.parent.postMessage({{isStreamlitMessage: true, type: "streamlit:setComponentValue", value: scanHistory}}, "*");
            }}
        }}
    </script>
</body>
</html>
"""
with open(os.path.join(bridge_dir, "index.html"), "w", encoding="utf-8") as f: f.write(html_code)
card_scanner = components.declare_component("card_scanner_v10", path=bridge_dir)

# --- Return Home Button ---
def handle_return_home():
    st.session_state.stage = 'setup'
    st.session_state.teams = []
    st.session_state.team_scores = {}
    st.session_state.players = []
    st.session_state.scores = {}
    st.session_state.scanned_cards = []
    st.session_state.scan_key = 0
    st.session_state.game_mode = "face value"
    st.session_state.fivehundred_suit = suit_options[0]
    st.session_state.fivehundred_bid = bid_options[0]
    st.session_state.fivehundred_bidder = st.session_state.players[0] if st.session_state.players else ""
    st.session_state.fivehundred_num_won = int(bid_options[0])
    st.session_state.confirm_home_warning = False
    st.session_state.winner = None
    st.session_state.loser = None

# --- page: setup ---
if st.session_state.stage == 'setup':
    st.title("should we score")

    st.session_state.game_mode = st.selectbox(
        "game rules",
        [
            "face value (all cards face value, highest score wins)",
            "gin (all cards face value, jokers 30, lowest score wins)",
            "yaniv (j,q,k are 10 pts, others face value, lowest score wins, at 50 you go to 25, at 100 you go to 50)",
            "dutch (black kings are -1, jokers 0, everything else face value, lowest score wins)",
            "500 (trick scoring, highest score wins, end game at 500 or -500)"
        ],
        format_func=lambda mode: mode.split(" (")[0]
    )
    game_mode_map = {
        "face value": "face value",
        "gin": "gin",
        "yaniv": "yaniv",
        "dutch": "dutch",
        "500": "500"
    }
    mode_prefix = st.session_state.game_mode.split(" ")[0]
    st.session_state.game_mode = game_mode_map.get(mode_prefix, "default_mode")

    if st.session_state.game_mode == "500":
        # Setup two teams, pick a name for each (enforced max)
        with st.form(key="team_form", clear_on_submit=True):
            new_team = st.text_input("add team", placeholder="enter team name...")
            submit_btn = st.form_submit_button("add")
            if submit_btn and new_team and new_team not in st.session_state.teams and len(st.session_state.teams) < MAX_TEAMS:
                st.session_state.teams.append(new_team)
                st.session_state.team_scores[new_team] = 0
                st.rerun()
        if st.session_state.teams:
            st.write("teams")
            for t in st.session_state.teams:
                st.write(f"- {t}")
            if len(st.session_state.teams) == MAX_TEAMS:
                if st.button("start game"):
                    st.session_state.stage = 'edit'  # jump to edit directly for 500 mode
                    st.session_state.winner = None
                    st.session_state.loser = None
                    st.rerun()
        if len(st.session_state.teams) >= MAX_TEAMS:
            st.warning(f"Maximum of {MAX_TEAMS} teams reached.")
    else:
        st.session_state.scoring_mode = st.radio("scoring mode", ["automatic", "manual"], horizontal=True)
        st.markdown("---")
        with st.form(key="player_form", clear_on_submit=True):
            new_player = st.text_input("add player", placeholder="enter name...")
            submit_btn = st.form_submit_button("add")
            if submit_btn and new_player and new_player not in st.session_state.players:
                st.session_state.players.append(new_player)
                st.session_state.scores[new_player] = 0
                st.rerun()
        if st.session_state.players:
            st.write("players")
            for p in st.session_state.players:
                st.write(f"- {p}")
            if st.button("start game"):
                st.session_state.stage = 'scan'
                st.session_state.winner = None
                st.session_state.loser = None
                st.rerun()

# --- page: scan or manual entry ---
elif st.session_state.stage == 'scan':
    is_500 = st.session_state.game_mode == "500"
    if is_500:
        # remove this scan page for 500 entirely -- always go directly to edit
        st.session_state.stage = 'edit'
        st.rerun()
    else:
        # Pick the current player (turn-based for other modes)
        current_player = st.session_state.players[st.session_state.scan_key % len(st.session_state.players)]
        st.subheader(f"{current_player}'s turn")
        st.write(f"score: {st.session_state.scores[current_player]}")

        # --- Home button ---
        col = st.columns([6, 1])
        with col[-1]:
            home_clicked = st.button("🏠", help="Return home and reset all progress")
        if home_clicked:
            st.session_state.confirm_home_warning = True
        if st.session_state.confirm_home_warning:
            st.warning("Are you sure you want to return home? All progress will be lost.")
            colyes, colno = st.columns([2, 1])
            with colyes:
                if st.button("Reset and return home"):
                    handle_return_home()
                    st.rerun()
            with colno:
                if st.button("Cancel"):
                    st.session_state.confirm_home_warning = False
            st.stop()

        st.session_state.scoring_mode = st.radio("scoring mode", ["automatic", "manual"], 
                                                 index=0 if st.session_state.scoring_mode == "automatic" else 1, horizontal=True, key="score_mode_in_scan")
        if st.session_state.scoring_mode == 'automatic':
            st.write("hold phone above cards and tap stop when ready")
            raw_history = card_scanner(key=f"scanner_instance_{st.session_state.scan_key}")
            if st.button("switch to manual entry"):
                st.session_state.scanned_cards = []
                st.session_state.scoring_mode = 'manual'
                st.session_state.stage = 'edit'
                st.rerun()
            if raw_history is not None and isinstance(raw_history, list):
                final_cards = process_scan_history(raw_history)
                st.session_state.scanned_cards = final_cards
                st.session_state.stage = 'edit'
                st.rerun()
        else:
            st.write("manual card entry")
            if st.button("switch to camera"):
                st.session_state.scoring_mode = 'automatic'
                st.session_state.stage = 'scan'
                st.rerun()
            st.session_state.scanned_cards = []
            st.session_state.stage = 'edit'
            st.rerun()

# --- page: edit & confirm hand (shows name up top and 500 logic) ---
elif st.session_state.stage == 'edit':
    is_500 = st.session_state.game_mode == "500"
    if is_500:
        st.subheader("500: score entry")
        st.markdown("#### Enter 500 contract & result for this hand.")

        if not st.session_state.teams or len(st.session_state.teams) < MAX_TEAMS:
            st.warning("Add two teams first.")
            st.stop()
        # Inputs, show all again (allow edits/changes)
        st.session_state.fivehundred_bidder = st.selectbox(
            "Which team is bidding?",
            st.session_state.teams,
            index=(st.session_state.teams.index(st.session_state.fivehundred_bidder)
                   if st.session_state.fivehundred_bidder in st.session_state.teams else 0),
            key="500_bidder_edit"
        )
        st.session_state.fivehundred_suit = st.selectbox(
            "trump suit", 
            suit_options,
            index=suit_options.index(st.session_state.fivehundred_suit)
                if st.session_state.fivehundred_suit in suit_options else 0, 
            key="500_suit_edit"
        )
        st.session_state.fivehundred_bid = st.selectbox(
            "bid", 
            bid_options,
            index=bid_options.index(st.session_state.fivehundred_bid)
                if st.session_state.fivehundred_bid in bid_options else 0,
            key="500_bid_edit"
        )
        # for number won: allow up to 10
        number_won_min = 0
        number_won_max = 10
        won_default = int(st.session_state.fivehundred_bid) if st.session_state.fivehundred_bid.isdigit() else 6
        if isinstance(st.session_state.fivehundred_num_won, int):
            curr_val = st.session_state.fivehundred_num_won
        else:
            try:
                curr_val = int(st.session_state.fivehundred_num_won)
            except Exception:
                curr_val = won_default
        if st.session_state.fivehundred_bid.isdigit():
            curr_val = max(int(st.session_state.fivehundred_bid), number_won_min)
        else:
            curr_val = number_won_min
        st.session_state.fivehundred_num_won = st.number_input("Number of tricks WON (bidding team)", min_value=number_won_min,
                                                              max_value=number_won_max, value=curr_val, step=1, key="500_numwon_edit")
        bidder_team = st.session_state.fivehundred_bidder
        suit = st.session_state.fivehundred_suit
        bid = st.session_state.fivehundred_bid
        num_won = st.session_state.fivehundred_num_won

        other_team = [t for t in st.session_state.teams if t != bidder_team]
        other_team = other_team[0] if other_team else None

        # Only calculate for valid bid and suit
        if bid == "misère":
            bid_score = get_500_score(suit, bid)
            st.write(f"Score for misère: {bid_score}")
            st.info("Scoring misère (only works for solo, assign to bidding team)")
        else:
            bid_score = get_500_score(suit, bid)
            st.write(f"Score for {bid} {suit}: {bid_score}")
            st.write(f"Bidding Team: {bidder_team}, Needed: {bid} | Tricks won: {num_won}")

        if st.button("confirm score"):
            # Calculate result
            team_scores_delta = {t: 0 for t in st.session_state.teams}
            if bid == "misère":
                team_scores_delta[bidder_team] += bid_score
                if other_team:
                    team_scores_delta[other_team] += 0  # explicit for clarity
            elif bid.isdigit():
                bid_int = int(bid)
                total_tricks = 10
                nonbidder_tricks = total_tricks - num_won if num_won <= total_tricks else 0
                if num_won >= bid_int:
                    # Bidding team makes contract: gets the bid points only.
                    team_scores_delta[bidder_team] += bid_score
                    if other_team:
                        # The non-bidder gets 10 points per trick they won (if any)
                        team_scores_delta[other_team] += nonbidder_tricks * 10
                else:
                    # Bidding team fails contract: loses the bid points (negative), non-bidder gets 10 points per trick they won.
                    team_scores_delta[bidder_team] -= bid_score
                    if other_team:
                        team_scores_delta[other_team] += nonbidder_tricks * 10

            # Apply deltas
            for t in team_scores_delta:
                st.session_state.team_scores[t] += team_scores_delta[t]

            st.session_state.scanned_cards = []

            # Check for winner/loser (only team that gets to 500 or -500 triggers end)
            winner = None
            loser = None
            for tname, tscore in st.session_state.team_scores.items():
                if tscore >= 500:
                    winner = tname
                elif tscore <= -500:
                    loser = tname
            if winner is not None:
                st.session_state.winner = winner
                st.session_state.stage = 'game_over'
            elif loser is not None:
                st.session_state.loser = loser
                st.session_state.stage = 'game_over'
            else:
                st.session_state.stage = 'between_rounds'
            st.session_state.scan_key += 1
            st.rerun()

        if st.button("cancel & rescan"):
            st.session_state.scanned_cards = []
            st.session_state.scan_key += 1
            st.session_state.stage = 'edit'
            st.rerun()

    else:
        # Pick current player (still turn-based for other games)
        current_player = st.session_state.players[st.session_state.scan_key % len(st.session_state.players)]
        st.subheader(f"{current_player}'s hand")

        st.write(f"scoring: {st.session_state.game_mode}")

        # Home button
        col = st.columns([6, 1])
        with col[-1]:
            home_clicked = st.button("🏠", help="Return home and reset all progress", key="home_edit")
        if home_clicked:
            st.session_state.confirm_home_warning = True
        if st.session_state.confirm_home_warning:
            st.warning("Are you sure you want to return home? All progress will be lost.")
            colyes, colno = st.columns([2, 1])
            with colyes:
                if st.button("Reset and return home", key="home_edit_confirm"):
                    handle_return_home()
                    st.rerun()
            with colno:
                if st.button("Cancel", key="home_edit_cancel"):
                    st.session_state.confirm_home_warning = False
            st.stop()

        # Make sure drop down is always empty after each turn for other games
        edited_cards = st.multiselect(
            "add/remove cards",
            options=all_cards_with_jokers,
            default=st.session_state.scanned_cards,
            format_func=lambda x: get_card_info(x, st.session_state.game_mode)[0],
            key=f'multiselect_edit_{st.session_state.scan_key}'
        )
        total_score = 0
        lines = []
        for code in edited_cards:
            name, score = get_card_info(code, st.session_state.game_mode)
            total_score += score
            lines.append(f"{name} : {score}")
        for l in lines:
            st.write(l)
        st.write(f"total: {total_score}")
        if st.button("confirm score"):
            # Special yaniv/dutch rules for score adjustment
            if st.session_state.game_mode == "yaniv":
                new_score = st.session_state.scores[current_player] + total_score
                # If at 50, go to 25. If at 100, go to 50.
                if new_score >= 100:
                    new_score = 50
                elif new_score >= 50:
                    new_score = 25
                st.session_state.scores[current_player] = new_score
            else:
                st.session_state.scores[current_player] += total_score

            # Clear scanned cards so next player does not see them
            st.session_state.scanned_cards = []

            # Move to next player's turn
            st.session_state.scan_key += 1
            if st.session_state.scan_key % len(st.session_state.players) == 0:
                st.session_state.stage = 'between_rounds'
            else:
                st.session_state.stage = 'scan'
            st.rerun()
        if st.button("cancel & rescan"):
            st.session_state.scanned_cards = []
            st.session_state.scan_key += 1
            st.session_state.stage = 'scan'
            st.rerun()

# --- page: rankings/between rounds ---
elif st.session_state.stage == 'between_rounds':
    st.write("-- round over, current rankings --")
    # Home button
    col = st.columns([6, 1])
    with col[-1]:
        home_clicked = st.button("🏠", help="Return home and reset all progress", key="home_between")
    if home_clicked:
        st.session_state.confirm_home_warning = True
    if st.session_state.confirm_home_warning:
        st.warning("Are you sure you want to return home? All progress will be lost.")
        colyes, colno = st.columns([2, 1])
        with colyes:
            if st.button("Reset and return home", key="home_between_confirm"):
                handle_return_home()
                st.rerun()
        with colno:
            if st.button("Cancel", key="home_between_cancel"):
                st.session_state.confirm_home_warning = False
        st.stop()

    # sort ranks
    if st.session_state.game_mode == "500":
        ranking = sorted(st.session_state.teams, key=lambda t: st.session_state.team_scores[t], reverse=True)
        for rank_i, tname in enumerate(ranking, 1):
            st.write(f"{rank_i}. {tname} ({st.session_state.team_scores[tname]})")
        winner = None
        loser = None
        for tname, tscore in st.session_state.team_scores.items():
            if tscore >= 500:
                winner = tname
            elif tscore <= -500:
                loser = tname
        if winner is not None:
            st.session_state.winner = winner
            st.session_state.stage = 'game_over'
            st.rerun()
        elif loser is not None:
            st.session_state.loser = loser
            st.session_state.stage = 'game_over'
            st.rerun()
    else:
        game_highest_wins = st.session_state.game_mode == "face value"
        ranking = sorted(st.session_state.players, key=lambda p: st.session_state.scores[p], reverse=game_highest_wins)
        for rank_i, pname in enumerate(ranking, 1):
            st.write(f"{rank_i}. {pname} ({st.session_state.scores[pname]})")
    if st.button("next round"):
        # Reset scanned cards for drop down for next round / player
        st.session_state.scanned_cards = []
        st.session_state.stage = 'scan'
        st.rerun()

# --- GAME OVER PAGE for 500 ---
elif st.session_state.stage == "game_over":
    st.title("GAME OVER")
    if st.session_state.game_mode == "500":
        if st.session_state.winner:
            st.success(f"{st.session_state.winner} wins! Final score: {st.session_state.team_scores[st.session_state.winner]}")
        elif st.session_state.loser:
            st.error(f"{st.session_state.loser} lost the game! Final score: {st.session_state.team_scores[st.session_state.loser]}")
        else:
            st.info("Game finished.")
        st.write("Final scores:")
        ranking = sorted(st.session_state.teams, key=lambda t: st.session_state.team_scores[t], reverse=True)
        for rank_i, tname in enumerate(ranking, 1):
            st.write(f"{rank_i}. {tname} ({st.session_state.team_scores[tname]})")
        if st.button("Return home and reset"):
            handle_return_home()
            st.rerun()
    else:
        if st.session_state.winner:
            st.success(f"{st.session_state.winner} wins! Final score: {st.session_state.scores[st.session_state.winner]}")
        elif st.session_state.loser:
            st.error(f"{st.session_state.loser} lost the game! Final score: {st.session_state.scores[st.session_state.loser]}")
        else:
            st.info("Game finished.")
        st.write("Final scores:")
        ranking = sorted(st.session_state.players, key=lambda p: st.session_state.scores[p], reverse=True)
        for rank_i, pname in enumerate(ranking, 1):
            st.write(f"{rank_i}. {pname} ({st.session_state.scores[pname]})")
        if st.button("Return home and reset"):
            handle_return_home()
            st.rerun()
