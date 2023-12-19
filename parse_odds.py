from doctest import master
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
import time
import pandas as pd
from collections import defaultdict
import sys
import argparse

stat_list = ["Passing Yards", "Rushing Yards", "Receiving Yards", "Receptions", "Touchdowns", "Passing TDS", "Interceptions"]

def odds_list_row(html):
    name = html.find("div", class_="props-name").text.strip()
    line = html.find("span", class_="data-moneyline").text.strip()
    try:
        line_odds = float(html.find("small", class_="data-odds best").text.strip())
    except:
        line_odds = 100
    name = name.split(' ')
    name = name[0] + " " + name[1]
    if line[0] == "o" or line[0] == "u":
        line = float(line[1:])
    elif line == 'even':
        line = 100
    else:
        line = float(line)
    if line_odds < 0:
        final_line = (line_odds/-110) * line
    else:
        final_line = (100/line_odds) * line
    return name, final_line


def main(argv):
    argParser = argparse.ArgumentParser()
    argParser.add_argument("week", type=int, help="NFL Week")
    args = argParser.parse_args()
    WEEK = args.week
    driver = webdriver.Firefox()
    driver.get('https://www.scoresandodds.com/nfl/props')
    driver.implicitly_wait(120)
    data_dict = defaultdict(dict)
    name_list = []
    line_list = []
    for i in range(0, len(stat_list) - 1):
        result = driver.page_source
        soup = BeautifulSoup(result, "html.parser")
        odds_table = soup.find_all('ul', class_="table-list")
        odds_list = odds_table[i].find_all("li")
        for entry in odds_list:
            name, line = odds_list_row(entry)
            data_dict[f"{stat_list[i]}"][name] = line
        element = driver.find_element(By.XPATH, f"// span[contains(text(), '{stat_list[i]}')]")
        element.click()
        driver.implicitly_wait(200)
        element = driver.find_element(By.XPATH, f"// span[contains(text(), '{stat_list[i+1]}')]")
        element.click()
        time.sleep(1)
        driver.implicitly_wait(200)
        name_list.clear()
        line_list.clear()
        if i == len(stat_list) - 2:
            result = driver.page_source
            soup = BeautifulSoup(result, "html.parser")
            odds_table = soup.find_all('ul', class_="table-list")
            odds_list = odds_table[i+1].find_all("li")
            for entry in odds_list:
                name, line = odds_list_row(entry)
                data_dict[f"{stat_list[i+1]}"][name] = line

    driver.close()
    driver.quit()  

    all_names = []
    for entry_stat in stat_list:
        entry_name_list = list(data_dict[entry_stat].keys())
        for entry_name in entry_name_list:
            if entry_name not in all_names:
                all_names.append(entry_name)

    master_df = pd.DataFrame(columns=["Name"])
    master_df["Name"] = all_names

    for entry_stat in stat_list:
        entry_dict = pd.DataFrame(data_dict[entry_stat].items(), columns=["Name", f"{entry_stat}"])
        master_df = pd.merge(master_df, entry_dict, how='left', on='Name')

    
    master_df.to_csv(f"2023/WEEK{WEEK}/NFL_Proj_{WEEK}.csv", index=False)
    print(f"Successfully wrote file, /NFL_Proj_{WEEK}.csv")


if __name__ == "__main__":
    main(sys.argv[1:])