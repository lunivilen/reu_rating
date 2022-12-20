import json
import os
from func_timeout import func_timeout, FunctionTimedOut
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium import webdriver
from bs4 import BeautifulSoup as bs
import pandas as pd
import dataframe_image as dfi
from LKS.lks_bot import get_info_for_lks


def exit_(browser, login):
    browser.quit()
    os.remove(f"{login}.json")
    return None


def get_rating(login, password, event):
    # Timer time in seconds
    timer_time = 600

    # url
    url_main_page = "https://student.rea.ru/"

    # Option
    option = webdriver.ChromeOptions()
    option.add_argument('--no-sandbox')
    option.add_argument('--disable-dev-shm-usage')
    option.headless = True

    browser = webdriver.Chrome(options=option)
    browser.get(url=url_main_page)

    # Parsing
    browser.find_element("xpath", "/html/body/div[4]/div/div[1]/form/div[2]/input").send_keys(login)
    browser.find_element("xpath", "/html/body/div[4]/div/div[1]/form/div[3]/input").send_keys(password)
    browser.find_element("xpath", "/html/body/div[4]/div/div[1]/form/input[4]").click()

    # Close popup windows
    try:
        for er in range(2):
            browser.find_element(By.CLASS_NAME, "fancybox-close-small").click()
    except NoSuchElementException:
        pass

    soup = bs(markup=browser.page_source, features="lxml")
    try:
        print(soup.find(class_="errortext").text)
        return False
    except AttributeError:
        pass

    profile_amount = 0
    try:
        browser.find_element("xpath", "/html/body/nav/div/div/div[1]/a").click()
        soup = bs(markup=browser.page_source, features="lxml")
        profile_amount = len(list(map(lambda x: x.text, soup.find_all(class_="fakultet__selector_profile"))))

        with open(f"{login}.json", "w", encoding="utf-8") as f:
            json.dump(profile_amount, f)
    except NoSuchElementException:
        pass

    if profile_amount:
        while True:
            try:
                profile = int(
                    func_timeout(timer_time, get_info_for_lks, kwargs={"event": event, "profile": profile_amount}))
                if 0 < profile <= profile_amount:
                    break
            except FunctionTimedOut:
                return exit_(browser, login)
        browser.find_element("xpath",
                             f"/html/body/div[7]/div[2]/div[4]/div/div/div[3]/div[{profile}]/label").click()
        browser.find_element("xpath", "/html/body/div[7]/div[2]/div[4]/div/div/button[1]").click()

    soup = bs(markup=browser.page_source, features="lxml")
    prof_n = soup.find(class_="breadcrumb__fakultet__popup").text
    semester_amount = int(prof_n[29]) * 2

    with open(f"{login}.json", "w", encoding="utf-8") as f:
        json.dump(semester_amount, f)

    while True:
        try:
            semester = int(
                func_timeout(timer_time, get_info_for_lks, kwargs={"event": event, "semester": semester_amount}))
            if -1 < semester <= semester_amount:
                break
        except FunctionTimedOut:
            return exit_(browser, login)

    if semester:
        prof_n = prof_n[29:prof_n.index(',') + 1] + prof_n[62:-8] + f", {semester}-й семестр"
        url_rating = f"https://student.rea.ru/rating/index.php?semester={semester}-й+семестр"
    else:
        prof_n = prof_n[29:prof_n.index(',') + 1] + prof_n[62:-8]
        url_rating = "https://student.rea.ru/rating/index.php"

    browser.get(url=url_rating)
    src = browser.page_source

    # Save locally site's page
    with open(f"rating.html", "w", encoding="utf-8") as f:
        f.write(src)
    os.remove(f"{login}.json")
    browser.quit()

    # Getting table of scores
    with open(f"rating.html", "r", encoding="utf-8") as f:
        src = f.read()
    soup = bs(markup=src, features="lxml")

    try:
        head_list = list(map(lambda x: x.text, soup.find(class_="es-rating__line")))
        head_list = list(filter(lambda x: x != "\n", head_list))

        subjects = list(
            map(lambda x: x.text, soup.find_all(class_="es-rating__line-item es-rating__discipline")))
        subjects.pop(0)
        subjects_rows = []
        for i in subjects:
            b = list(filter(lambda x: x != "", i.split(" ")))
            b.pop(0)
            b = " ".join(b)
            subjects_rows.append([b])

        # Remove social and scientific subjects
        subjects_rows = subjects_rows[0:-2]

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
            for i in range(len(subjects_rows) - 1):
                if subjects_rows[i] == subjects_rows[i + 1] and subjects_rows[i][0] in course_work_subject:
                    course_work_subject.remove(subjects_rows[i][0])
                    subjects_rows[i + 1][0] += " (Курсовая работа или пересдача)"

        scores = list(map(lambda x: x.text, soup.find_all(class_="es-rating__tab-body-item")))
        scores = list(filter(lambda x: x != "", scores[0].split(" ")))
        scores = list(filter(lambda x: x[0].isdigit(), scores))
        scores_rows = [scores[i:i + 5] for i in range(0, len(scores), 5)]

        # Remove social and scientific scores
        for i in range(2):
            if len(scores_rows[-1]) != 5:
                scores_rows = scores_rows[:-1]

        df = pd.DataFrame(scores_rows, subjects_rows, head_list[1:])
        dfi.export(df, "image.png", fontsize=40)
        os.remove(f"rating.html")
    except (TypeError, IndexError):
        os.remove(f"rating.html")
        return None
    return True
