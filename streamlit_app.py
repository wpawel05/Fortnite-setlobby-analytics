import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import re
import os

st.set_page_config(page_title="Fortnite Live Tournament Tracker", layout="wide")

# --- STYLE ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎮 Fortnite Live Tournament Tracker - Pro Edition")
st.subheader("System śledzenia progresji i precyzyjnej rekonstrukcji meczów")

# --- INITIALIZATION ---
if 'game_data' not in st.session_state:
    st.session_state.game_data = {}
if 'num_boxes' not in st.session_state:
    st.session_state.num_boxes = 1

# --- ARCHIVE LOADER LOGIC ---
def get_archived_tournaments():
    tournaments = []
    if os.path.exists("."):
        for item in os.listdir("."):
            if os.path.isdir(item) and not item.startswith(".") and not item.startswith("__"):
                files = os.listdir(item)
                if any(f.startswith("match") and f.endswith(".txt") for f in files):
                    tournaments.append(item)
    return sorted(tournaments)

archived_tours = get_archived_tournaments()

# --- PARSING FUNCTION ---
def parse_block(text):
    if not text or len(text.strip()) < 10: return pd.DataFrame()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    data = []
    i = 0
    while i < len(lines):
        if not lines[i].isdigit(): 
            i += 1
            continue
        try:
            rank = int(lines[i])
            country_raw = lines[i+1]
            idx = i + 2
            stats_idx = -1
            for j in range(idx, min(idx + 6, len(lines))):
                if re.match(r'^\d+\s+\d+\s+\d+\s+\d+', lines[j]):
                    stats_idx = j
                    break
            if stats_idx == -1:
                i += 1
                continue
            
            player_info = lines[idx:stats_idx]
            p1 = player_info[0]
            p2 = player_info[2] if len(player_info) >= 3 else player_info[1]
            
            s = lines[stats_idx].split()
            pts, matches, wins, elims, place = int(s[0]), int(s[1]), int(s[2]), int(s[3]), float(s[4])
            
            # Czas przeżycia
            t_str = " ".join(s[5:])
            minutes = int(re.search(r'(\d+)m', t_str).group(1)) if 'm' in t_str else 0
            seconds = int(re.search(r'(\d+)s', t_str).group(1)) if 's' in t_str else 0
            total_sec = minutes * 60 + seconds

            data.append({
                "Duo": f"{p1} & {p2}",
                "Country_Raw": country_raw,
                "Total_Points": pts,
                "Total_Elims": elims,
                "Total_Wins": wins,
                "Avg_Placement": place,
                "Avg_Time_Sec": total_sec
            })
            i = stats_idx + 1
            while i < len(lines) and (lines[i].startswith('$') or 'k' in lines[i].lower()): i += 1
        except: i += 1
    return pd.DataFrame(data)

# --- SIDEBAR: INPUT & ARCHIVE ---
st.sidebar.header("📂 Zarządzanie danymi")

# Sekcja Archiwum
if archived_tours:
    st.sidebar.subheader("🗄️ Wczytaj zarchiwizowany turniej")
    selected_tour = st.sidebar.selectbox("Wybierz turniej z repozytorium:", ["-- Wybierz turniej --"] + archived_tours)
    
    if selected_tour != "-- Wybierz turniej --" and st.sidebar.button("Zaimportuj dane"):
        st.session_state.game_data = {}
        files = sorted([f for f in os.listdir(selected_tour) if f.startswith("match") and f.endswith(".txt")])
        
        for idx, filename in enumerate(files, start=1):
            with open(os.path.join(selected_tour, filename), "r", encoding="utf-8") as f:
                st.session_state.game_data[idx] = f.read()
        st.session_state.num_boxes = len(files)
        st.sidebar.success(f"Pomyślnie zaimportowano {len(files)} meczów!")

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Ręczne wprowadzanie LIVE")

# Renderowanie pól tekstowych na podstawie zmiennej num_boxes
for g in range(1, st.session_state.num_boxes + 1):
    with st.sidebar.expander(f"Mecz {g}", expanded=(g == st.session_state.num_boxes)):
        input_key = f"raw_g{g}"
        default_val = st.session_state.game_data.get(g, "")
        val = st.text_area(f"Dane z Tracker-a (Mecz {g}):", value=default_val, key=input_key, height=150)
        if val:
            st.session_state.game_data[g] = val

# Przycisk do ręcznego dodawania kolejnego slotu na mecz
if st.sidebar.button("➕ Dodaj kolejny mecz"):
    st.session_state.num_boxes += 1
    st.rerun()

# --- PROCESSING ---
all_games_dfs = {}
for g, txt in st.session_state.game_data.items():
    parsed = parse_block(txt)
    if not parsed.empty:
        all_games_dfs[g] = parsed

if all_games_dfs:
    all_duos = pd.concat(all_games_dfs.values())["Duo"].unique()
    
    # Wyciąganie i rozdzielanie unikalnych państw
    unique_countries = set()
    for df_g in all_games_dfs.values():
        for c in df_g["Country_Raw"].unique():
            if c.lower() == 'poland':
                unique_countries.add('PL')
            else:
                if len(c) % 2 == 0 and c.isupper():
                    for k in range(0, len(c), 2):
                        unique_countries.add(c[k:k+2])
                else:
                    unique_countries.add(c.upper())
                    
    # --- FILTRY ---
    st.markdown("### 🛠️ Filtry Analizy")
    f_col1, f_col2, f_col3 = st.columns([2, 2, 3])
    
    max_available_games = max(all_games_dfs.keys())
    with f_col1:
        if max_available_games > 1:
            game_range = st.slider("Wybierz zakres gier do analizy:", 1, max_available_games, (1, max_available_games))
            selected_games = list(range(game_range[0], game_range[1] + 1))
        else:
            st.info("Dostępna tylko 1 gra.")
            selected_games = [1]
            
    with f_col2:
        selected_countries = st.multiselect("Kraje:", options=sorted(list(unique_countries)), default=sorted(list(unique_countries)))
    with f_col3:
        selected_duos = st.multiselect("Wybierz konkretne duety do porównania:", options=sorted(all_duos))

    # --- REKONSTRUKCJA MATEMATYCZNA LOGIKI LIVE ---
    processed_stats = []
    
    for duo in all_duos:
        prev_pts, prev_elims, prev_wins = 0, 0, 0
        prev_sum_placement, prev_sum_time = 0, 0
        
        for g in sorted(all_games_dfs.keys()):
            df_g = all_games_dfs[g]
            row = df_g[df_g["Duo"] == duo]
            
            if not row.empty:
                r = row.iloc[0]
                
                # Delty dla tabeli głównej
                current_pts = r["Total_Points"] - prev_pts
                current_elims = r["Total_Elims"] - prev_elims
                current_wins = r["Total_Wins"] - prev_wins
                
                # Średnie rekonstruowane ze skumulowanych (per mecz)
                current_total_placement = r["Avg_Placement"] * g
                current_total_time = r["Avg_Time_Sec"] * g
                
                game_placement = current_total_placement - prev_sum_placement
                game_time_sec = current_total_time - prev_sum_time
                
                game_placement = max(1.0, round(game_placement, 1))
                game_time_sec = max(0.0, round(game_time_sec, 0))
                
                c_raw = r["Country_Raw"]
                duo_countries = ['PL'] if c_raw.lower() == 'poland' else ([c_raw[k:k+2] for k in range(0, len(c_raw), 2)] if (len(c_raw) % 2 == 0 and c_raw.isupper()) else [c_raw.upper()])
                
                processed_stats.append({
                    "Gra": g,
                    "Duo": duo,
                    "Duo_Countries": duo_countries,
                    "Punkty_w_Grze": current_pts,
                    "Elimy_w_Grze": current_elims,
                    "Wygrane_w_Grze": current_wins,
                    "Miejsce_w_Grze": game_placement,
                    "Czas_Sek_w_Grze": game_time_sec,
                    "Suma_Punktów": r["Total_Points"],
                    "Suma_Eliminacji": r["Total_Elims"]
                })
                
                prev_pts = r["Total_Points"]
                prev_elims = r["Total_Elims"]
                prev_wins = r["Total_Wins"]
                prev_sum_placement = current_total_placement
                prev_sum_time = current_total_time

    full_df = pd.DataFrame(processed_stats)
    
    # --- ZAAWANSOWANE FILTROWANIE ---
    mask_game = full_df["Gra"].isin(selected_games)
    def country_match(row_countries):
        return any(c in selected_countries for c in row_countries)
    mask_country = full_df["Duo_Countries"].apply(country_match)
    
    final_mask = mask_game & mask_country
    if selected_duos:
        final_mask = final_mask & (full_df["Duo"].isin(selected_duos))
        
    view_df = full_df[final_mask]

    # --- TABELA LIDERÓW ---
    st.markdown("### 🏆 Tabela Wyników dla wybranych gier")
    if not view_df.empty:
        leaderboard = view_df.groupby("Duo").agg({
            "Punkty_w_Grze": "sum",
            "Elimy_w_Grze": "sum",
            "Wygrane_w_Grze": "sum",
            "Miejsce_w_Grze": "mean",
            "Czas_Sek_w_Grze": "mean",
        }).sort_values("Punkty_w_Grze", ascending=False)
        
        leaderboard["Śr. Czas życia"] = leaderboard["Czas_Sek_w_Grze"].apply(lambda x: f"{int(x//60)}m {int(x%60):02d}s")
        leaderboard.columns = ["Suma Punktów", "Suma Eliminacji", "Wygrane Mecze", "Śr. Miejsce", "Czas_Sek_Raw", "Śr. Czas życia"]
        
        st.dataframe(leaderboard[["Suma Punktów", "Suma Eliminacji", "Wygrane Mecze", "Śr. Miejsce", "Śr. Czas życia"]], use_container_width=True)
    else:
        st.warning("Brak danych spełniających kryteria filtrów.")

    # --- WYKRESY ---
    if not view_df.empty:
        st.markdown("### 📈 Dokładna Analiza Per Mecz (Wartości Rzeczywiste)")
        
        t1, t2 = st.tabs(["Punkty i Eliminacje (Suma)", "Pozycje i Survival (Mecz)"])

        with t1:
            col1, col2 = st.columns(2)
            with col1:
                fig_pts = px.line(view_df, x="Gra", y="Suma_Punktów", color="Duo", markers=True,
                                 title="Wykres liniowy: Całkowity stan punktów po poszczególnych grach", template="plotly_dark")
                fig_pts.update_xaxes(dtick=1)
                st.plotly_chart(fig_pts, use_container_width=True)
            with col2:
                fig_el = px.line(view_df, x="Gra", y="Suma_Eliminacji", color="Duo", markers=True,
                               title="Wykres liniowy: Całkowity stan eliminacji po poszczególnych grach", template="plotly_dark")
                fig_el.update_xaxes(dtick=1)
                st.plotly_chart(fig_el, use_container_width=True)

        with t2:
            col3, col4 = st.columns(2)
            with col3:
                fig_pl = px.line(view_df, x="Gra", y="Miejsce_w_Grze", color="Duo", markers=True,
                                title="Dokładne miejsce zajęte w konkretnym meczu (1 = TOP 1)", template="plotly_dark")
                fig_pl.update_yaxes(autorange="reversed")
                fig_pl.update_xaxes(dtick=1)
                st.plotly_chart(fig_pl, use_container_width=True)
            with col4:
                view_df["Czas_Min_w_Grze"] = view_df["Czas_Sek_w_Grze"] / 60
                fig_tm = px.line(view_df, x="Gra", y="Czas_Min_w_Grze", color="Duo", markers=True,
                                title="Faktyczny czas przeżycia w tym meczu (w minutach)", template="plotly_dark")
                fig_tm.update_xaxes(dtick=1)
                st.plotly_chart(fig_tm, use_container_width=True)
else:
    st.warning("👈 Wybierz zarchiwizowany turniej lub zacznij wpisywać mecze ręcznie.")
