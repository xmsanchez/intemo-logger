# intemo auto-logger

**DISCLAIMER: THIS PROJECT USES SELENIUM.** Therefore, any changes in their website could affect the functionality of this script.

I wanted to make it work with direct javascript calls to their API but I **couldn't manage to make the authentication** to work properly. I'm open to feedback on that.

## Description

This project allows you to automate logging in intemo hour control system.

The deployment is done in **Google Cloud** and the execution leverages the **Google Cloud Run** service, which has a few triggers at the time where you need to run the script (morning and afternoon).

It will make sure if it is a **working day**, a **holiday** or **vacation** (but see below warning)

> **WARNING**: This feature **is not** dynamic for now. I need to work on extracting it automatically. For now, you need to manually extract the json file with the CSS used in the calendar and place it in [dates.py](dates.py).

## How it works

The script will accept three parameters as environment variables which will control the behaviour.

- **intemo_user**: Your username (string)
- **intemo_pass**: Your password (string)
- **INTEMO_ACTION**: start / exit (string)
- **INTEMO_HOST**: Intemo host full DNS (string)

Based on the "INTEMO_ACTION" value, it will check if and enter or an exit register exists. If it exists, it will not try to do the action again (avoid duplicate entries if script runs multiple times).

If the enter or exit entry is not present, then it will create the new registry in the platform.

## Add a random for entry / exit

You can search and uncomment these lines:

```python
# Wait for some seconds before starting (give it a random entry/exit time)
wait_for_execution(300)
```

The function ``wait_for_execution(300)`` accepts and integer which will be used in the random function as ``time.sleep(int)``, so the script runs after the generated time runs out.

## Google Cloud Run setup

> NOTE: Every step can be done through gcloud cli and therefore it could be scripted (easier to setup), but so far only the build with the cli is described in this README.

### Generate artifact

Export as GCLOUD_PROJECT your google cloud project and run:

```bash
gcloud builds submit --tag gcr.io/$GCLOUD_PROJECT/intemo-logger .
```

This will create the docker artifact.

### Setup jobs

Now go to the jobs console: https://console.cloud.google.com/run/jobs

Click on "Create job":

- Click on "Container Registry" --> select the container that we just built in the previous step.
- Set the name: "intemo-logger-start" / "intemo-logger-exit"
- Pick a region. I use "europe-west2"
- Expand "Container, variables and secrets, connections, security" and click on "Variables & secrets"
- Add variable "INTEMO_ACTION" with the desired value ("start" or "exit")
- Add variable "INTEMO_HOST" with the desired value ("https://xxxxxx")
- Click on create

### Set trigger

Click in the new job and select "TRIGGERS".

Add a new scheduled trigger. There are a few parameters to set:

- Name: ``intemo-logger-start-scheduler-trigger`` or ``intemo-logger-exit-scheduler-trigger``
- Frequency: This is a standard cron format. For example:
- - Start: Run each day of the week at 7am: ``0 7 * * 1-5``
- - Exit: Run from monday to thursday at 16:30: ``30 16 * * 1-4``
- - Exit: Run on fridays at 1pm: ``0 13 * * 5``
- Time zone: Search for Spain and select Europe/Madrid.

> NOTE: If you did set the ``wait_for_execution()`` function, remember to adapt your triggers.