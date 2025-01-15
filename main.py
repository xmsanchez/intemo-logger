import requests
import os
import re
from datetime import datetime
from lxml import html

# Selenium will be used only in the final step to validate entries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

USER = os.environ.get("intemo_user")
PASS = os.environ.get("intemo_pass")
ACTION = os.environ.get('INTEMO_ACTION')
INTEMO_HOST = os.environ.get('INTEMO_HOST')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    'content-type': 'application/x-www-form-urlencoded',
    'referer': f'{INTEMO_HOST}'
}

start_url = f'{INTEMO_HOST}/Security/LogIn/LogIn'

def check_response(response):
    response_code = response.status_code
    response_message = response.content

    if response_code == 200:
        print('OK')
    else:
        print('Response code: ' + str(response_code))
        raise Exception(f'Message: {response_message}')

def login_user(session, cookies):
    # Generate the payload for the login
    payload = { "__RequestVerificationToken": cookies['__RequestVerificationToken'],
                "Username": USER,
                "Password": PASS,
                "RememberMe": False}

    print('\nInitiate login')
    response = session.post(f'{INTEMO_HOST}/Security/LogIn/LogIn',
                            data=payload,
                            headers=headers,
                            cookies=cookies)

    check_response(response)
    return response.request._cookies.get_dict()

def is_working_day(tree):
    print('\nCheck if today is a working day')
    # Extract all <script> tags' content
    script_contents = tree.xpath("//script/text()")

    # Find the specific script containing the target keywords
    target_script = next(
        (script for script in script_contents if "workTimetableColors" in script and "workTimetableDescriptions" in script),
        None
    )

    work_timetable_working_days = []
    work_timetable_not_working_days = []

    if target_script:
        # Use regex to extract the keys and values for workTimetableColors and workTimetableDescriptions
        # Thanks for this, GPT ;-D
        colors_pattern = re.compile(r'workTimetableColors\["(\d+)"\]\s*=\s*"([^"]+)"')
        descriptions_pattern = re.compile(r'workTimetableDescriptions\["(\d+)"\]\s*=\s*"([^"]+)"')

        # work_timetable_colors is not really used but I'll leave it to switch to it just in
        # case intemo makes some changes to the descriptions that might affect this script
        work_timetable_colors = {match[0]: match[1] for match in colors_pattern.findall(target_script)}
        work_timetable_descriptions = {match[0]: match[1] for match in descriptions_pattern.findall(target_script)}

        for item in work_timetable_descriptions:
            if "Horario SaaS" in work_timetable_descriptions[item] or 'Horario   viernes' in work_timetable_descriptions[item]:
                work_timetable_working_days.append(item)
            else:
                work_timetable_not_working_days.append(item)

    # Get today's date formatted as YYYYMMDD
    today = datetime.today()
    today_date = today.strftime("%Y%m%d")
    today_date_formatted = today.strftime("%A, %dth of %B %Y")

    print("Today's date: " + today_date_formatted)
    if today_date in work_timetable_working_days:
        print('This IS a working day')
        return True
    elif today_date in work_timetable_not_working_days:
        print('This is NOT a working day')
        return False
    else:
        raise Exception('Today date not found in calendar')

def get_employee_calendar(session, cookies):
    # Fetch the calendar to ensure today is a workday and not weekend or holiday
    print('\nGet calendar')
    response = session.get(f'{INTEMO_HOST}/TimeAndAttendance/MyCalendar',
                            allow_redirects=False,
                            headers=headers,
                            cookies=cookies)

    check_response(response)
    return response

def get_entries(session, cookies):
    print('\nGet entries for today')
    response = session.get(f'{INTEMO_HOST}/TimeAndAttendance/EmployeeDashboard',
                            allow_redirects=False,
                            headers=headers,
                            cookies=cookies)

    check_response(response)

    # Parse the HTML
    tree = html.fromstring(response.content)

    # Extract entries and exits for today
    # Note that strip() gets rid of \r\n at the end of each time string
    entries = tree.xpath('//div[@class="real-record"]/div/img[contains(@src, "entry.png")]/following-sibling::text()')
    entries = [entry.strip() for entry in entries]

    exits = tree.xpath('//div[@class="real-record"]/div/img[contains(@src, "exit.png")]/following-sibling::text()')
    exits = [exit.strip() for exit in exits]

    return entries, exits

def selenium_init(cookies):
    print('Opening browser with selenium...')
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox") # Required to run in docker
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.3")
    driver = webdriver.Chrome(options=chrome_options)

    # Apparently it won't work without this first connection
    driver.get(f"{INTEMO_HOST}/")

    # Transfer cookies from requests to selenium
    for name, value in cookies.items():
        driver.add_cookie({'name': name, 'value': value})

    # Refresh the page to load the cookies
    driver.refresh()

    return driver

def new_record(cookies, entry_type):
    # For some reason direct api calls are not working properly for this step
    # Therefore we will use Selenium to validate start/end work

    # Initiate selenium and transfer cookies from requests to browser
    driver = selenium_init(cookies)

    # Request the iframe from where the start/end records are created
    driver.get(f'{INTEMO_HOST}/TimeAndAttendance/MyAccessRecords/CreateWork{entry_type}')

    # Wait until the button is found
    wait = WebDriverWait(driver, 10)
    btn_validate = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "button.btn.btn-primary")
        )
    )

    # Finally create the new record
    if btn_validate is not None:
        btn_validate.click()
    else:
        raise('Found an error.')

    print('OK')

# Start the main program
if __name__ == "__main__":
    if ACTION is None or ACTION == "":
        print('You must provide an action: start / exit')
        exit(1)

    print('\nInitiate requests session')
    session = requests.Session()
    session.get(f'{INTEMO_HOST}/Security/LogIn/LogIn', headers=headers)

    # Get the received cookies and log in the user
    cookies = session.cookies.get_dict()

    # Log in user and retrieve additional cookies required for further requests
    request_cookies = login_user(session, cookies)

    # We need to add an additional cookie required for certain requests
    # like checking the calendar or validating the start/end work
    try:
        cookies['.AspNet.Cookies'] = request_cookies['.AspNet.Cookies']
    except Exception as ex:
        raise Exception('Required ".AspNet.Cookies" cookie was not found in the login response.')

    # Retrieve calendar
    calendar = get_employee_calendar(session, cookies)

    # Check if today is weekday or weekend/holiday
    if is_working_day(html.fromstring(calendar.content)):

        # Get entries and exits
        entries, exits = get_entries(session, cookies)

        print(f'Action to perform: {ACTION}')
        if ACTION == "start":
            if len(entries) == 0:
                print('ENTRY record not found. Create a new one.')
                new_record(cookies, 'Start')
            else:
                print(f'There is already an ENTRY record: {entries}')

        if ACTION == "exit":
            if len(exits) == 0:
                print('EXIT record not found. Create a new one.')
                new_record(cookies, 'End')
            else:
                print(f'There is already an EXIT record: {exits}')
