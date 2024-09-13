import streamlit as st
import pandas as pd
import altair as alt
from st_aggrid import GridOptionsBuilder, AgGrid, GridUpdateMode, ColumnsAutoSizeMode

def chart_data(data, name):
    #transform dataframe 
    source=pd.melt(data, id_vars=[name], value_name="Points")

    chart = alt.Chart(source).mark_bar().encode(
        column=alt.Column(name, title=""),
        x=alt.X('variable', title="", scale=alt.Scale(paddingOuter=1)),
        y=alt.Y('Points'),
        color=alt.Color('variable', scale=alt.Scale(range=['#134B70', '#808080']))
        ).configure_view(
            strokeWidth=0.0,
        )
    
    return chart

def position_data(position:str, sel_row: pd.DataFrame, past_week:bool, last_week_df=None):
    column_names = {
        "WR": ["Receiving Yards", "Receptions", "Touchdowns"],
        "RB": ["Rushing Yards", "Receiving Yards", "Receptions", "Touchdowns"],
        "QB": ["Passing Yards", "Passing TD", "Interceptions", "Rushing Yards", "Rushing TD"]
        }
    
    proj_columns = {
        "WR": ["Rec Yds DFS", "Rec DFS", "TDs DFS"],
        "RB": ["Rush Yds DFS", "Rec Yds DFS", "Rec DFS", "TDs DFS"],
        "QB": ["Pass Yds DFS", "Pass TDs DFS", "Int DFS", "Rush Yds DFS", "TDs DFS"]
        }
    act_or_last_columns = {
        "WR": ["rec_Yds", 'rec_Rec', 'rec_TD'],
        "RB": ["rush_Yds", "rec_Yds", 'rec_Rec', 'rec_TD'],
        "QB": ["pass_Yds", "pass_TD", "pass_INT", "rush_Yds", "rush_TD"]
        }

    if past_week:
        first_column = column_names[position]
        second_column = [sel_row[k].iloc[0] for k in proj_columns[position]]
        third_column = [sel_row[k].iloc[0] for k in act_or_last_columns[position]]
        data = pd.DataFrame({
        position: first_column,
        "Projected": second_column,
        "Actual": third_column
        })
    
    else:
        last_week_row = last_week_df[last_week_df["Name"] == sel_row.iloc[0,3]]
        try:
            first_column = column_names[position]
            second_column = [sel_row[k].iloc[0] for k in proj_columns[position]]
            if position != "RB":
                third_column = [last_week_row[k].iloc[0] for k in act_or_last_columns[position]]
            else:
                third_column = [last_week_row["rush_Yds"].iloc[0], last_week_row["rec_Yds"].iloc[0], last_week_row["rec_Rec"].iloc[0], (last_week_row["rec_TD"].iloc[0] + last_week_row["rush_TD"].iloc[0])]
            print(first_column)
            print(second_column)
            print(third_column)
            data = pd.DataFrame({
            position: first_column,
            "Projected": second_column,
            "Last Week": third_column
            })
        except:
            try:
                data = pd.DataFrame({
                    position: first_column,
                    "Projected": second_column,
                    })
                try:
                    data = pd.DataFrame({
                    position: first_column,
                    "Last Week": third_column
                    })
                except:
                    st.write(f"Last week data for {sel_row.iloc[0,3]} not available")
            except:
                st.write(f"Projected data for {sel_row.iloc[0,3]} not available yet")
    return data
    

st.set_page_config(page_title="Plum Dashboard", page_icon=":football:", layout="wide")

st.title(":football: Plum Dashboard")
st.markdown('<style>div.block-container{padding-top:4rem;}</style>', unsafe_allow_html=True)
md = "Welcome to the Plum Dashboard, your home for all your DraftKings Daily Fantasy Sports (DFS) needs. Use this dashboard to help build your lineups based on DFS projections by yours-truly PureSlurp. The dashboard uses data from props as well as historical data of draftkings scoring to help users create the perfect lineups! \n Quick Start Guide:\n - Select the week on the left you want to deep dive\n - Select a player to see their projections and history"
st.markdown(md)

# Create for Week
st.sidebar.header("Week to Analyze")
week_str = st.sidebar.selectbox("Pick your Week", [f"WEEK{x}" for x in range(1,3)], index=0)
week = int(week_str[4:])

# df_proj = pd.read_csv(f"2024/{week}/NFL_Proj_DFS.csv")
df_debug = pd.read_csv(f"2024/{week_str}/dashboard.csv")
df_debug["Value"] = (df_debug["Proj DFS Total"] / df_debug["Salary"]) * 1000
# df_debug = pd.merge(df_debug, df_proj, how="left", on="Name")

# figure out if the week is in the past or future
try:
    df_box_score = pd.read_csv(f"2024/{week_str}/box_score_debug.csv")
    df = pd.merge(df_debug, df_box_score, how="left", on="Name")
    df["Net"] = df["Proj DFS Total"] - df["Act DFS Total"]
    df = df.round({"Net": 2, "Proj DFS Total": 2})
    display_df = df[["Position", "Name", "Salary", "TeamAbbrev", "Proj DFS Total", "Act DFS Total", "Net"]]
    past_week = True
    last_week_df = None
except:
    df = df_debug
    df = df.round({"Proj DFS Total": 2})
    display_df = df[["Position", "Name", "Salary","Game Info", "TeamAbbrev", "Proj DFS Total", "Value"]]
    past_week = False
    last_week_df = pd.read_csv(f"2024/WEEK{week-1}/box_score_debug.csv")
    print("box score not available yet")



st.subheader(f"Week {week} Player Pool Summary")

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
    if isinstance(data["selected_rows"], list):
        row_dict = data["selected_rows"][0]
        del row_dict["_selectedRowNodeInfo"]
        sel_row = pd.DataFrame(row_dict, index=[0])
    else:
        sel_row = data["selected_rows"]

    position = sel_row.iloc[0,1]
    selected_data = position_data(position, sel_row, past_week, last_week_df)
    
    chart = chart_data(selected_data, position)
    st.altair_chart(chart) #, use_container_width=True)
    selected_data.loc['total']= selected_data.sum()
    selected_data.loc[selected_data.index[-1], 'WR'] = ''
    selected_data = selected_data.round(2)
    st.write(selected_data)
    