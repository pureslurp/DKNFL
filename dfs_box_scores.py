import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
import sys
import numpy as np
import argparse

def dk_scoring(col, key):
    match key:
        case "pass_Yds":
            '''
            25 pass yds = 1 (0.04/yd)
            300+ yd game = 3 
            '''
            total = int(col) * 0.04
            if int(col) >= 300:
                total += 3
            return total
        case "pass_TD":
            # pass TD = 4
            return int(col) * 4
        case "pass_INT":
            # INT = -1
            return int(col) * -1
        case "rush_Yds":
            '''
            10 rush yds = 1
            100+ rush game = 3
            '''
            total = int(col) * 0.1
            if int(col) >= 100:
                total += 3
            return total
        case "rush_TD":
            # Rush TD = 6
            return int(col) * 6
        case "rec_Rec":
            # Rec = 1
            return int(col)
        case "rec_Yds":
            '''
            10 rec yds = 1
            100+ rec game = 3
            '''
            total = int(col) * 0.1
            if int(col) >= 100:
                total += 3
            return total
        case "rec_TD":
            # rec TD = 6
            return int(col) * 6

def fix_player(player):
    split_player = player.split(".")
    if len(split_player) > 2:
        if split_player[0] == "Amon-Ra":
            player = "Amon-Ra St. Brown"
        elif split_player[0] == "Equanimeous":
            player = "Equanimeous St. Brown"
        split_player = split_player[:-1]
        split_player = [s.strip() for s in split_player]
        initials = split_player[:-1]
        player = f'{".".join(initials)}. {split_player[-1][:-1]}'.strip()
    else:
        player = split_player[0][:-1]
    return player


def main(argv):
    argParser = argparse.ArgumentParser()
    argParser.add_argument("week", type=int, help="NFL Week")
    args = argParser.parse_args()
    WEEK = args.week
    pass_columns = ["player", "pass_Yds", "pass_TD", "pass_INT"]
    rush_columns = ["player", "rush_Yds", "rush_TD"]
    rec_columns = ["player", "rec_Rec", "rec_Yds", "rec_TD"]
    pass_df = pd.DataFrame(columns=pass_columns)
    rush_df = pd.DataFrame(columns=rush_columns)
    rec_df = pd.DataFrame(columns=rec_columns)

    url = 'https://www.footballdb.com/games/index.html'
    driver = webdriver.Firefox()
    driver.get(url)
    driver.implicitly_wait(120)
    result = driver.page_source
    soup = BeautifulSoup(result, "html.parser")

    data = soup.find_all()
    data = soup.find_all('table', class_='statistics')
    games = data[WEEK-1].find_all('tr')
    links = []
    for game in games:
        try:
            link = game.find("a").get('href')
            links.append(link)
        except:
            continue

    for link in links:
        #html = pd.read_html(f"https://www.footballdb.com{link}")
        driver.get(f"https://www.footballdb.com{link}")
        #driver.implicitly_wait(120)
        result = driver.page_source
        soup = BeautifulSoup(result, "html.parser")
        data = soup.find('div', {"id": "divBox_stats"})
        headers = soup.find_all('div', class_="divider")
        tables = data.find_all("table")
        data_dict = {}
        for j in range(0, 6):
        #for table in tables:
            head = tables[j].find("thead")
            body = tables[j].find("tbody")
            hs = head.find_all("th")
            try:
                bs_r = body.find_all("tr")
            except:
                bs_r = body.find("tr")
            #print(bs)
            for x in range(0, len(bs_r)):
                #print(bs_r)
                bs = bs_r[x].find_all("td")
                for i in range(0, len(hs)):
                    data_dict[hs[i].text]= bs[i].text
                if j < 2:                
                    row = [fix_player(list(data_dict.values())[0]), data_dict["Yds"], data_dict["TD"], data_dict["Int"]]
                    pass_df.loc[len(pass_df)] = row
                elif j < 4:
                    row = [fix_player(list(data_dict.values())[0]), data_dict["Yds"], data_dict["TD"]]
                    rush_df.loc[len(rush_df)] = row
                else:
                    row = [fix_player(list(data_dict.values())[0]), data_dict["Rec"], data_dict["Yds"], data_dict["TD"]]
                    rec_df.loc[len(rec_df)] = row

                data_dict.clear()

    master = pd.merge(pass_df, rush_df, how='outer', on='player')
    master = pd.merge(master, rec_df, how='outer', on='player')
    master = master.fillna(0)
    col_of_interets = ["pass_Yds", "pass_TD", "pass_INT", "rush_Yds", "rush_TD", "rec_Rec", "rec_Yds", "rec_TD"]

    for key in col_of_interets:
        master[key] = master[key].apply(lambda x: dk_scoring(x, key))

    #master["DFS Total"] = master[col_of_interets].sum()
    master["DFS Total"] = master.iloc[:, 1:].sum(axis=1)
    master.rename(columns={"player" : "Name"}, inplace=True)
    master.to_csv(f"2023/WEEK{WEEK}/box_score_debug_week_{WEEK}.csv")
    print(f"Successfully wrote box scores to WEEK{WEEK} folder")
    driver.close()
    driver.quit()  

if __name__ == "__main__":
    main(sys.argv[1:])