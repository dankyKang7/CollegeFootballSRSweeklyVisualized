# Save as app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import warnings
st.set_page_config(page_title="College Football SRS Dashboard", layout="wide")


warnings.filterwarnings("ignore")

# -------------------------------
# 1. Load SRS Data
# -------------------------------
srsData_conf = pd.read_csv('srs_24_07.csv')

# Correct types
srsData_conf['week'] = srsData_conf['week'].astype(int)
srsData_conf['season'] = srsData_conf['season'].astype(int)

# Initial padded season_week
srsData_conf['season_week'] = srsData_conf.apply(
    lambda x: f"{x.season}-{x.week:02d}", axis=1
)

# -------------------------------
# 2. Pull Team Colors + Logos
# -------------------------------
team_metadata = pd.read_csv('team_metadata.csv')
team_colors = dict(zip(team_metadata['school'], team_metadata['color']))
team_logos = dict(zip(team_metadata['school'], team_metadata['logo']))



team_metadata = get_team_metadata()

# -------------------------------
# 3. Streamlit App Layout
# -------------------------------
st.sidebar.title("Filters")

# Sidebar Filters
conferences = sorted(srsData_conf['team_conference'].dropna().unique())
selected_confs = st.sidebar.multiselect(
    "Select Conference(s)", options=conferences, default=conferences
)

filtered_teams = sorted(srsData_conf[srsData_conf['team_conference'].isin(selected_confs)]['team'].unique())
selected_teams = st.sidebar.multiselect(
    "Select Team(s)", options=filtered_teams, default=filtered_teams
)

seasons = sorted(srsData_conf['season'].unique())
selected_seasons = st.sidebar.multiselect(
    "Select Season(s)", options=seasons, default=seasons
)

# Optional smoothing
smoothing = st.sidebar.slider("SRS Moving Average Window (weeks)", min_value=1, max_value=5, value=1)

# Optional animation toggle
animate_plot = st.sidebar.checkbox("Animate by Week?", value=False)

# -------------------------------
# 4. Filter and Prepare Data
# -------------------------------
filtered_data = srsData_conf[
    (srsData_conf['team_conference'].isin(selected_confs)) &
    (srsData_conf['team'].isin(selected_teams)) &
    (srsData_conf['season'].isin(selected_seasons))
]

filtered_data = filtered_data.drop_duplicates(subset=["team", "season", "week"])

# 🔥 Rebuild season_week cleanly only if not empty
if not filtered_data.empty:
    filtered_data['season_week'] = filtered_data.apply(
        lambda x: f"{x.season}-{x.week:02d}", axis=1
    )
    filtered_data['season_week'] = filtered_data['season_week'].astype(str)

# Optional smoothing
if smoothing > 1 and not filtered_data.empty:
    filtered_data['ratings'] = (
        filtered_data
        .sort_values(['team', 'season', 'week'])
        .groupby(['team'])['ratings']
        .transform(lambda x: x.rolling(window=smoothing, min_periods=1).mean())
    )

# -------------------------------
# 5. Main Title
# -------------------------------
st.title("College Football SRS Dashboard")

# -------------------------------
# 6. Plot
# -------------------------------
if filtered_data.empty:
    st.warning("⚠️ No data available for the selected filters. Please adjust your selections.")
else:
    sorted_weeks = sorted(filtered_data['season_week'].unique())

    if animate_plot:
        fig = px.line(
            filtered_data,
            x="season_week",
            y="ratings",
            color="team",
            line_group="season",
            markers=True,
            hover_data=["team", "season", "week", "ratings"],
            labels={"season_week": "Season + Week", "ratings": "SRS Rating"},
            animation_frame="season_week",
        )
    else:
        fig = px.line(
            filtered_data,
            x="season_week",
            y="ratings",
            color="team",
            line_group="season",
            markers=True,
            hover_data=["team", "season", "week", "ratings"],
        )

    # Apply team colors and custom hover templates
    for trace in fig.data:
        team_name = trace.name.replace("🏈 ", "")  # 🔥 Remove emoji for metadata lookup
        if team_name in team_metadata:
            # Color
            trace.line.color = team_metadata[team_name]['color']
    
            # Name with emoji for legend
            trace.name = f"🏈 {team_name}"
    
            # Logos
            logo = team_metadata[team_name]['logo']
    
            if logo:
                trace.hovertemplate = (
                    f"<b>{team_name}</b><br>"
                    f"<img src='{logo}' style='width:30px;height:30px;'><br>"
                    "Week: %{x}<br>"
                    "SRS: %{y:.2f}<extra></extra>"
                )
            else:
                trace.hovertemplate = (
                    f"<b>{team_name}</b><br>"
                    "Week: %{x}<br>"
                    "SRS: %{y:.2f}<extra></extra>"
                )



    # Update Layout
    fig.update_layout(
        xaxis=dict(
            tickfont=dict(size=14),
            ticklen=8,
            tickwidth=2,
            tickcolor='black',
        ),
        yaxis=dict(
            tickfont=dict(size=14),
            ticklen=8,
            tickwidth=2,
            tickcolor='black',
        ),
        xaxis_type='category',
        xaxis_categoryorder='array',
        xaxis_categoryarray=sorted_weeks,
        xaxis_tickangle=-45,
        xaxis_title="Season + Week",
        yaxis_title="SRS Rating",
        legend_title="Team",
        hovermode="closest",
    )
    # # 🔥 Critical setting:
    # fig.update_traces(hovertemplate=None, hoverinfo="skip")
    # fig.update_layout(hovermode="closest")

    # Thicker lines
    for trace in fig.data:
        trace.line.width = 3

    # Vertical lines at Week 1
    week1_lines = sorted(filtered_data[filtered_data['week'] == 1]['season_week'].unique())
    for w1 in week1_lines:
        fig.add_vline(
            x=w1,
            line_dash="dash",
            line_color="gray",
            opacity=0.4
        )

    # Season Year Labels
    for i in range(len(week1_lines)):
        current_week = week1_lines[i]
        if i + 1 < len(week1_lines):
            season_year = current_week.split('-')[0]
            fig.add_annotation(
                x=current_week,
                y=1.05,
                text=season_year,
                showarrow=False,
                yref='paper',
                xanchor='left',
                font=dict(size=12, color="gray")
            )

    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------
    # 7. Show Raw Data
    # -------------------------------
    if st.checkbox("Show Raw Data Table"):
        st.dataframe(filtered_data.sort_values(['team', 'season_week']))

    # -------------------------------
    # 8. Download CSV
    # -------------------------------
    csv = filtered_data.to_csv(index=False).encode('utf-8')
    _ = st.download_button(
        label="📥 Download Filtered SRS Data",
        data=csv,
        file_name='filtered_srs_data.csv',
        mime='text/csv',
    )
