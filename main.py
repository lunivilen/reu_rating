from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from bs4 import BeautifulSoup as bs
import os
import json


def get_rating(login, password, semester=0):
    # urls
    url_main_page = "https://student.rea.ru/"
    if semester:
        url_rating = f"https://student.rea.ru/rating/index.php?semester={semester}-й+семестр"
    else:
        url_rating = "https://student.rea.ru/rating/index.php"

    # Option
    option = webdriver.FirefoxOptions()
    option.set_preference("dom.webdriver.enable", False)
    option.set_preference("dom.webnotifications.enabled", False)
    option.set_preference("media.volume_scale", "0.0")
    option.headless = True

    browser = webdriver.Firefox(options=option)
    browser.get(url_main_page)

    # Parsing
    browser.find_element("xpath", "/html/body/div[4]/div/div[1]/form/div[2]/input").send_keys(login)
    browser.find_element("xpath", "/html/body/div[4]/div/div[1]/form/div[3]/input").send_keys(password)
    browser.find_element("xpath", "/html/body/div[4]/div/div[1]/form/input[4]").click()
    profile = 0

    # Parsing all profiles
    while True:
        profile += 1
        try:
            # Trying to choose next profile
            browser.find_element("xpath", "/html/body/nav/div/div/div[1]/a").click()
            browser.find_element("xpath",
                                 f"/html/body/div[7]/div[2]/div[4]/div/div/div[3]/div[{profile}]/label").click()
            browser.find_element("xpath", "/html/body/div[7]/div[2]/div[4]/div/div/button[1]").click()
            if profile == 1:
                browser.get(url_rating)
            src = browser.page_source

            # Save locally site's page
            with open(f"rating_{profile}.html", "w", encoding="utf-8") as f:
                f.write(src)

        except NoSuchElementException:
            if profile == 1:
                profile += 1
                browser.get(url_rating)
                src = browser.page_source

                # Save locally site's page
                with open("rating_1.html", "w", encoding="utf-8") as f:
                    f.write(src)
            break
    browser.quit()

    # Getting table of scores
    for k in range(1, profile):
        with open(f"rating_{k}.html", "r", encoding="utf-8") as f:
            src = f.read()
        soup = bs(src, "lxml")

        try:
            head_list = list(map(lambda x: x.text, soup.find(class_="es-rating__line")))
            head_list = list(filter(lambda x: x != "\n", head_list))

            subjects = list(map(lambda x: x.text, soup.find_all(class_="es-rating__line-item es-rating__discipline")))
            subjects.pop(0)
            subjects_rows = []
            for i in subjects:
                b = list(filter(lambda x: x != "", i.split(" ")))
                b.pop(0)
                b = " ".join(b)
                subjects_rows.append([b])

            # Checking for course work
            is_course_work = soup.find_all(class_="es-rating__line es-rating__line-child close")
            if is_course_work != "":
                course_work = []
                for i in is_course_work:
                    course_work.append(i.find(class_="es-rating__line-item es-rating__discipline").text)

                course_work_subject = []
                for i in course_work:
                    b = list(filter(lambda x: x != "", i.split(" ")))
                    b.pop(0)
                    b = " ".join(b)
                    course_work_subject.append(b)
                for i in range(-1, -(len(subjects_rows) - 1), -1):
                    if subjects_rows[i] == subjects_rows[i - 1] and subjects_rows[i][0] in course_work_subject:
                        subjects_rows[i][0] += "(Курсовая работа)"

            scores = list(map(lambda x: x.text, soup.find_all(class_="es-rating__tab-body-item")))
            scores = list(filter(lambda x: x != "", scores[0].split(" ")))
            scores = list(filter(lambda x: x[0].isdigit(), scores))
            scores_rows = [scores[i:i + 5] for i in range(0, len(scores), 5)]

            # Generate dict for json file
            temp_dict = []
            final_rows_json = []
            for i in range(len(scores_rows)):
                temp_dict.append(dict(zip(head_list[1:], scores_rows[i])))

            for i in range(len(temp_dict)):
                final_rows_json.append(dict(zip(subjects_rows[i], temp_dict)))

            # Write json file
            with open(f"rating_table_{k}.json", "w", encoding="utf-8") as f:
                json.dump(final_rows_json, f, indent=2, ensure_ascii=False)
                os.remove(f"rating_{k}.html")
        except TypeError:
            with open(f"rating_table_{k}.json", "w", encoding="utf-8") as f:
                json.dump(0, f)
                os.remove(f"rating_{k}.html")
