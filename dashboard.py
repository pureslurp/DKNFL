import streamlit as st
import pandas as pd
import altair as alt
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode

st.set_page_config(page_title="Plum Dashboard", page_icon=":football:", layout="wide")

st.title(":football: Plum Dashboard")
st.markdown('<style>div.block-container{padding-top:4rem;}</style>', unsafe_allow_html=True)

# Create for Week
st.sidebar.header("Week to Analyze")
week = st.sidebar.selectbox("Pick your Week", [f"WEEK{x}" for x in range(1,18)], index=0)

# df_proj = pd.read_csv(f"2024/{week}/NFL_Proj_DFS.csv")
df_debug = pd.read_csv(f"2024/{week}/dashboard.csv")
# df_debug = pd.merge(df_debug, df_proj, how="left", on="Name")

# figure out if the week is in the past or future
try:
    df_box_score = pd.read_csv(f"2024/{week}/box_score_debug.csv")
    df = pd.merge(df_debug, df_box_score, how="left", on="Name")
    df["Net"] = df["Proj DFS Total"] - df["Act DFS Total"]
    df = df.round({"Net": 2, "Proj DFS Total": 2})
    display_df = df[["Position", "Name", "Salary", "TeamAbbrev", "Proj DFS Total", "Act DFS Total", "Net"]]
    past_week = True
except:
    df = df_debug
    df = df.round({"Proj DFS Total": 2})
    display_df = df[["Position", "Name", "Salary","Game Info", "TeamAbbrev", "Proj DFS Total"]]
    past_week = False
    print("box score not available yet")



st.subheader(f"{week} Player Pool Summary")

with st.container(height=500):
    # select the columns you want the users to see
    gb = GridOptionsBuilder.from_dataframe(display_df)
    # configure selection
    gb.configure_selection(selection_mode="single", use_checkbox=True)

    gb.configure_default_column(
        flex=1,
        minWidth=100,
        maxWidth=500,
        resizable=True,
        filter=True
    )
    gridOptions = gb.build()

    data = AgGrid(df,
                gridOptions=gridOptions,
                update_mode=GridUpdateMode.SELECTION_CHANGED)


st.subheader("DFS Points Evaluation")
if data["selected_rows"] is not None:
    sel_row = data["selected_rows"].copy()
    if isinstance(sel_row, list):
        sel_row = sel_row[0]
        st.write(sel_row)
        del sel_row["_selectedRowNodeInfo"]
        st.write(sel_row)
        sel_row = pd.DataFrame.from_dict(sel_row)
    if sel_row.iloc[0,1] == "WR":
        if past_week:
            wr_data = pd.DataFrame([["Receiving Yards", sel_row["Rec Yds DFS"].iloc[0], sel_row["rec_Yds"].iloc[0]],["Receptions", sel_row["Rec DFS"].iloc[0] , sel_row["rec_Rec"].iloc[0]], ["Touchdowns", sel_row["TDs DFS"].iloc[0], sel_row["rec_TD"].iloc[0]]], columns=['Receiving','Projected','Actual'])
        else:
            wr_data = pd.DataFrame([["Receiving Yards", sel_row["Rec Yds DFS"].iloc[0]],["Receptions", sel_row["Rec DFS"].iloc[0]], ["Touchdowns", sel_row["TDs DFS"].iloc[0]]], columns=['Receiving','Projected'])
        #transform dataframe 
        source=pd.melt(wr_data, id_vars=['Receiving'])

        chart=alt.Chart(source).mark_bar(strokeWidth=90).encode(
            x=alt.X('variable:N', title="", scale=alt.Scale(paddingOuter=0.5)),#paddingOuter - you can play with a space between 2 models 
            y='value:Q',
            color='variable:N',
            column=alt.Column('Receiving:N', title="", spacing =0), #spacing =0 removes space between columns, column for can and st 
        ).properties( width = 250, height = 300, ).configure_header(labelOrient='bottom').configure_view(
            strokeOpacity=0)

        st.altair_chart(chart) #, use_container_width=True)

    st.write(sel_row)