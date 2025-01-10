import requests
import os
import re
import pickle
import json
from datetime import datetime
from lxml import html


USER = os.environ.get("intemo_user")
PASS = os.environ.get("intemo_pass")
ACTION = os.environ.get('INTEMO_ACTION')
INTEMO_HOST = os.environ.get('INTEMO_HOST')

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    'content-type': 'application/x-www-form-urlencoded',
    'referer': f'{INTEMO_HOST}/Security/LogIn/LogIn'
}

start_url = f'{INTEMO_HOST}/Security/LogIn/LogIn'

def check_response(response):
    response_code = response.status_code
    response_message = response.content

    if response_code == 200:
        print('OK')
    elif response_code == 302:
        print('Response code: ' + str(response_code))
        raise Exception(f'Message: {response_message}')
    else:
        print('Response code: ' + str(response_code))
        raise Exception(f'Message: {response_message}')

def login_user(session, cookies):
    # Generate the payload for the login
    payload = { "__RequestVerificationToken": cookies['__RequestVerificationToken'],
                "Username": USER,
                "Password": PASS,
                "RememberMe": False}

    # Send the login request
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
        colors_pattern = re.compile(r'workTimetableColors\["(\d+)"\]\s*=\s*"([^"]+)"')
        descriptions_pattern = re.compile(r'workTimetableDescriptions\["(\d+)"\]\s*=\s*"([^"]+)"')

        work_timetable_colors = {match[0]: match[1] for match in colors_pattern.findall(target_script)}
        work_timetable_descriptions = {match[0]: match[1] for match in descriptions_pattern.findall(target_script)}

        for item in work_timetable_descriptions:
            if "Horario SaaS" in work_timetable_descriptions[item] or 'Horario   viernes' in work_timetable_descriptions[item]:
                work_timetable_working_days.append(item)
            else:
                work_timetable_not_working_days.append(item)

    # print(f'Working days: {work_timetable_working_days}')
    # print(f'NON Working days: {work_timetable_not_working_days}')

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



def check_calendar(session, cookies):
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

def new_record(session, cookies, event_type):
    # Get current date and time
    now = datetime.now()

    # Define the parameters
    date_local = now.replace(hour=0, minute=0, second=0, microsecond=0)  # Set time to 12:00:00 AM
    time_local = now  # Use the current time

    # Format the values as requested
    date_local_str = date_local.strftime("%-m/%-d/%Y %-I:%M:%S %p")
    time_local_str = time_local.strftime("%-m/%-d/%Y %-I:%M:%S %p")

    # Form data (payload)
    payload = {
        'EventTypeValue': event_type,
        'DateLocal': date_local_str,
        'TimeLocal': time_local_str
    }

    print('Set a new entry. Payload: ' + str(payload))

    # Send POST request with the data
    response = session.post(f'{INTEMO_HOST}/TimeAndAttendance/MyAccessRecords/Edit',
                            data=payload,
                            headers=headers,
                            cookies=cookies)

    check_response(response)
    print(response.content)
    print(response.status_code)
    return response

# Start the main program
if __name__ == "__main__":
    session = requests.Session()
    session.get(f'{INTEMO_HOST}/Security/LogIn/LogIn', headers=headers)

    # Get the received cookies
    cookies = session.cookies.get_dict()

    # Log in user and retrieve additional cookies required for furhter requests
    request_cookies = login_user(session, cookies)

    # # We need to add an additional cookie required for certain requests
    # cookies['.AspNet.Cookies'] = request_cookies['.AspNet.Cookies']

    # Retrieve calendar
    response = check_calendar(session, cookies)

    # Check if today is weekday or weekend/holiday
    if is_working_day(html.fromstring(response.content)):

        # Get entries and exits
        entries, exits = get_entries(session, cookies)

        event_type_start = 10
        event_type_exit = 11

        if len(entries) == 0:
            print('ENTRY record not found.')
            # Create new entry record
            new_record(session, cookies, event_type_start)
        else:
            print(f'There is already an ENTRY record: {entries}')

        if len(exits) == 0:
            print('EXIT record not found.')
            # Create new exit record
            new_record(session, cookies, event_type_exit)
        else:
            print(f'There is already an EXIT record: {exits}')
