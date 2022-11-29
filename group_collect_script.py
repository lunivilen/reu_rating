import sqlite3 as sq
from selenium import webdriver
from bs4 import BeautifulSoup as bs
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

with sq.connect("states.db") as con:
    # Browser options
    option = webdriver.ChromeOptions()
    option.headless = True
    option.add_argument('--no-sandbox')
    option.add_argument('--disable-dev-shm-usage')

    # Variables
    url_main_page = "https://student.rea.ru/"
    cur_login = con.cursor()
    cur_password = con.cursor()
    cur_main = con.cursor()
    list_login = []
    list_password = []

    # Try to create study_group column in database
    try:
        cur_main.executescript("ALTER TABLE lks ADD study_group varchar(255)")
    except sq.OperationalError:
        pass

    for login, password in \
            zip(
                cur_login.execute("SELECT login FROM lks WHERE study_group IS NULL"),
                cur_password.execute("SELECT password FROM lks WHERE study_group IS NULL")
            ):
        list_login.append(login[0])
        list_password.append(password[0])

    for login, password in zip(list_login, list_password):
        browser = webdriver.Chrome(options=option)
        browser.get(url=url_main_page)

        # Authorization
        try:
            browser.find_element("xpath", "/html/body/div[4]/div/div[1]/form/div[2]/input").send_keys(login)
            browser.find_element("xpath", "/html/body/div[4]/div/div[1]/form/div[3]/input").send_keys(password)
            browser.find_element("xpath", "/html/body/div[4]/div/div[1]/form/input[4]").click()
        except TypeError:
            browser.quit()
            cur_main.executescript(f"UPDATE lks SET study_group = 'authorization_error' WHERE login = '{login}'")
            continue

        # Close popup windows
        try:
            for er in range(2):
                browser.find_element(By.CLASS_NAME, "fancybox-close-small").click()
        except NoSuchElementException:
            pass

        # Wrong password or login
        soup = bs(markup=browser.page_source, features="lxml")
        try:
            a = soup.find(class_="errortext").text
            cur_main.executescript(f"UPDATE lks SET study_group = 'authorization_error' WHERE login = '{login}'")
            continue
        except AttributeError:
            pass

        # Get group
        for temp in browser.find_elements(By.CLASS_NAME, "es-training__group"):
            if temp != "":
                group = temp.text

        # Update database
        cur_main.executescript(f"UPDATE lks SET study_group = '{group}' WHERE login = '{login}'")
        browser.quit()
