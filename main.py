import sys

import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ignored_exceptions = (selenium.common.exceptions.StaleElementReferenceException,
                      selenium.common.exceptions.NoSuchElementException)

class Session:
    def __init__(self, email, password):
        chrome_options = ChromeOptions()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get('https://aspen.cpsd.us/aspen/logonSSO.do?deploymentId=ma-cambridge&districtId=*dst&idpName=Cambridge%20Google%20SAML')
            email_field = driver.find_element(By.XPATH, "//input[@type='email']")
            email_field.click()
            email_field.send_keys(email, Keys.ENTER)
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='password']"))
            )
            pass_field = driver.find_element(By.XPATH, "//input[@type='password']")
            pass_field.send_keys(password, Keys.ENTER)
            WebDriverWait(driver, 5).until(EC.url_contains("https://aspen.cpsd.us/aspen/home.do"))

        except selenium.common.exceptions.StaleElementReferenceException:
            print("[ERROR] Failed to initialize session, probably a client-side issue.")

        self.driver = driver
        self.session_id = driver.current_url.split('&jsessionid=')[1]
        self.email = email
        # For security reasons don't store password all willy-nilly
        print(self.session_id)

    @staticmethod
    def _bake_details(detail_keys, detail_values):
        final_dict = {}
        key_convert = lambda x: x.replace(":", "")\
                                 .replace(" > Description", "")\
                                 .replace(" ", "_")\
                                 .lower()

        for k, v in zip(detail_keys, detail_values):
            if k.text != "Score":
                final_dict[key_convert(k.text)] = v.text
            else:
                # Do score processing
                score = v.text.split('\n')
                if len(score) == 1:
                    # Free text OR marked as PEND, MISS, Ungraded, or EXC
                    score = score[0]
                    text_marks = ["MISS", "PEND", "EXC", "Ungraded"]
                    for mark in text_marks:
                        if mark in score:
                            score = mark

                if len(score) == 2:
                    # Actual score given
                    score = score[1].split('(')[0].rstrip()

                final_dict["score"] = score

        final_dict.pop("teacher")
        final_dict.pop("course")
        return final_dict

    # Given a class_id (like L122-004, T608-004, etc.) build a json block for that class, in a given quarter
    def _build_json_academics_quarter(self, class_id, quarter):
        assignment_list = []
        self.driver.get("https://aspen.cpsd.us/aspen/portalClassList.do?navkey=academics.classes.list")

        # Go to class page
        class_href = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.LINK_TEXT, class_id))
        )
        class_href.click()

        # Go to assignment listing
        assignments_href = WebDriverWait(self.driver, 5, ignored_exceptions=ignored_exceptions).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Assignments"))
        )
        assignments_href.click()

        # Find first row in assignment table
        portal = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "listCell"))
        )

        # Find the link to that first assignment detail page, and finally click.
        portal = portal.find_element(By.TAG_NAME, "a")
        portal.click()
        print("[LOG] Successfully entered academic detail page, scraping now...")

        # Get location of next assignment button
        next_button = WebDriverWait(self.driver, 5, ignored_exceptions=ignored_exceptions).until(
            EC.element_to_be_clickable((By.ID, "nextButton"))
        )
        while next_button:
            next_button = WebDriverWait(self.driver, 5, ignored_exceptions=ignored_exceptions).until(
                EC.presence_of_element_located((By.ID, "nextButton"))
            )
            table = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "mainTable"))
            )

            # Retrieve and sanitize info
            detail_keys = table.find_elements(By.CLASS_NAME, "detailProperty")
            detail_values = table.find_elements(By.CLASS_NAME, "detailValue")
            assignment_list.append(Session._bake_details(detail_keys, detail_values))

            if not next_button.get_property("disabled"):
                next_button.click()
            else:
                break

        return assignment_list

    def close(self):
        self.driver.quit()

    def exit(self):
        self.driver.quit()
        sys.exit()

    def home(self):
        self.driver.get(f"https://aspen.cpsd.us/aspen/home.do?deploymentId=ma-cambridge&jsessionid={self.session_id}")


user = Session("28lspong@cpsd.us", "facestatued123")
print(user._build_json_academics_quarter("L122-004", "Q4"))
user.exit()

