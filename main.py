from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from random import randint
import time, os
 

USER = os.environ.get("intemo_user")
PASS = os.environ.get("intemo_pass")
ACTION = os.environ.get('INTEMO_ACTION')
INTEMO_HOST = os.environ.get('INTEMO_HOST')
driver = None
 
def wait_for_execution(wait_for):
    """
    Wait for the script execution
    This should provide a more human-like entry/exit register
    """
    rand = randint(0, wait_for)
    print(f'\nWait for {rand} seconds before executing the operation so this looks more like human interaction :-) ...')
    time.sleep(rand)
 
def init_selenium():
    """
    Initialize driver
    """
    global driver
    # Start URL is the host + login path
    start_url = f'{INTEMO_HOST}/Security/LogIn/LogIn'
    print('Start with url: ' + start_url)
    print(f'\nInitializing selenium chrome driver...')
    chrome_options = Options()
    chrome_options.add_argument("--headless") # for Chrome >= 109
    chrome_options.add_argument("--no-sandbox") # ensure compatibility with docker
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.3")
    driver = webdriver.Chrome(options=chrome_options)
    print(f'Opening start url {start_url}...')
    driver.get(start_url)
    print('Done')
 
def find_element(query_type, queries):
    """
    Find an element based on query type and query value
 
    Args:
        query_type(str): Can be ID, CLASS_NAME, XPATH
        queries(list): Array of queries to send to selenium
    """
    global driver
    response = None
    for query in queries:
        try:
            if query_type == 'ID':
                response = driver.find_element(By.ID, query)
            elif query_type == 'CLASS_NAME':
                response = driver.find_element(By.CLASS_NAME, query)
            elif query_type == 'LINK_TEXT':
                response = driver.find_element(By.LINK_TEXT, query)
            if query_type == 'XPATH':
                response = driver.find_element(By.XPATH, value=query)
        except Exception:
            pass
    #print(f'Response: {response}')
    return response
 
def record_do_not_exist(entry_type, entry):
    """
    Check if a record exists
    """
    if entry is not None:
        print(f'{entry_type} time: {entry.text}')
        return False
    else:
        print(f'{entry_type} not found!')
        return True
 
def validate(entry_type):
    """
    Validates entry/exit
    """
    print(f'Entry type is: {entry_type}')
    entry_type_text = {
        'start': ['Entrada trabajo'],
        'exit': ['Fin trabajo']
    }
    print(f'\nNeed to register: "{entry_type_text[entry_type][0]}"')
    btn = find_element('XPATH', [f"//*[contains(@title, '{entry_type_text[entry_type][0]}')]"])
    if btn is not None:
        btn.click()
    else:
        raise('Found an error. btn is none')
 
    print(f'\nSwitching to iframe to add an "{entry_type}" record...')
    time.sleep(2)
    iframe = find_element('XPATH', ["//iframe"])
    driver.switch_to.frame(iframe)
 
    btn_validate = find_element('XPATH', ["//button[text()='Validate']", "//button[text()='Validar']"])
 
    try:
        btn_validate.click()
    except Exception as ex:
        print(f'Got an error!: {ex}')
 
    driver.switch_to.parent_frame()
 
def check_calendar():
    calendar_url = f'{INTEMO_HOST}/TimeAndAttendance/MyCalendar'
    print('\nCheck calendar: ' + calendar_url)
    print(f'Opening calendar url {calendar_url}...')

    driver.get(calendar_url)
    lines = driver.page_source.splitlines()

    work_time_table = []
    # Now you can process each line

    for line in lines:
        # Your logic here (e.g., print the line)
        if "workTimetableColors" in line and not "dateIndex" in line:
            work_time_table.append(line.replace(" ", "").replace(";", ""))

    dates_object = {}
    for item in work_time_table:
        if not "varworkTimetableColors" in item:
            str_split = item.split('"')
            dates_object[str_split[1]] = str_split[3]

    # Switch back to previous page
    driver.get(f'{INTEMO_HOST}/TimeAndAttendance/EmployeeDashboard')
    return dates_object

def parse_working_days(working_days):
    date_format = "%Y%m%d"
    today = datetime.strftime(datetime.today(), date_format)
    print(f'Check if today is a workday ({today})')
    is_workday = working_days[today]

    if is_workday == "#CCCCCC":
        print(f'Date: {today} is {is_workday}. TODAY IS WORKDAY. Proceed.')
    else:
        print(f'Date: {today} is {is_workday}. Today IS NOT workday. Nothing to do.')
        exit(0)

# START MAIN FUNCTION
if __name__ == "__main__":
    print(ACTION)
    if ACTION is None or ACTION == "":
        print('You must provide an action: start / exit')
        exit(1)
    
    # Init driver
    init_selenium()
 
    # # Wait for some seconds before starting (give it a random entry/exit time)
    # wait_for_execution(300)
 
    # Search for form user/pass input boxes
    print("\nLet's log the user in...")
    username = find_element('ID', ["Username"])
    password = find_element('ID', ["Password"])
 
    username.send_keys(USER)
    password.send_keys(PASS)
 
    # LOGIN BUTTON
    # In headless mode the language might change so we need to test both
    login_queries = ["//button[text()='Iniciar sesión']", "//button[text()='Log in']"]
    login_btn = find_element('XPATH', login_queries)
    login_btn.click()
 
    # Give it time for rendering the window
    # (should use the webdriverwait but... this is easier)
    time.sleep(1)
    print('Done')

    # Dynamically hceck calendar for workdays / holidays
    working_days = check_calendar()

    # Check if it's a working day (not holidays, not weekend)
    # If it's not a owrking day, the script will exit
    parse_working_days(working_days)
 
    if ACTION == "start":
        # CHECK IF START EXISTS
        print('\nSearch for Start/Inicio')
        entry_start_queries = ["//*[contains(@title, 'Inicio')]//ancestor::div[contains(@class, 'real-record')]", "//*[contains(@title, 'Start')]//ancestor::div[contains(@class, 'real-record')]"]
        entry_start = find_element('XPATH', entry_start_queries)
        if record_do_not_exist('start', entry_start):
            validate('start')
 
    elif ACTION == "exit":
        # CHECK IF EXIT EXISTS
        print('\nSearch for End/Fin')
        entry_exit_queries = ["//*[contains(@title, 'Fin')]//ancestor::div[contains(@class, 'real-record')]", "//*[contains(@title, 'End')]//ancestor::div[contains(@class, 'real-record')]"]
        entry_exit = find_element('XPATH', entry_exit_queries)
        if record_do_not_exist('exit', entry_exit):
            validate('exit')
 
    driver.quit()
    