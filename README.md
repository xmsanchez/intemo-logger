# intemo auto-logger

**DISCLAIMER: THIS PROJECT USES SELENIUM.** For the most part the script uses direct API calls, but **I couldn't manage to make entry validation** to work properly so I'm using selenium for that last step. I'm open to feedback on that.

## Description

This project allows you to automate logging in intemo hour control system.

It will make sure if it is a **working day**, a **holiday** or **vacation** by checking the employee calendar. It is fetched from the "worktimetable" javascript variable located in the calendar page which contains "workTimetableColors" and "workTimetableDescriptions" fields.

The deployment is done in **Google Cloud** and the execution leverages the **Google Cloud Run** service, which has a few triggers where you'll define when to run the script (morning and afternoon).

If you'd rather prefer it to run as a daemon and wish to support that feature, feel free to open a Pull Request :-)

## How it works

The script will accept three parameters as environment variables which will control the behaviour.

- **intemo_user**: Your username (string)
- **intemo_pass**: Your password (string)
- **INTEMO_ACTION**: start / exit (string)
- **INTEMO_HOST**: Intemo host full DNS (string)

Based on the "INTEMO_ACTION" value, it will check if and "start" or an "end" record exists. If it exists, it will not try to do the action again (avoid duplicate entries if script runs multiple times).

If the enter or exit entry is not present, then it will create the new record in the platform.

## Google Cloud Run setup

> NOTE: Every step can be done through gcloud cli and therefore it could be scripted (easier to setup), but so far only the build with the cli is described in this README.

### Generate artifact

Export as GCLOUD_PROJECT your google cloud project and run:

```bash
gcloud builds submit --tag gcr.io/$GCLOUD_PROJECT/intemo-logger .
```

This will create the docker artifact.

### Setup jobs

**UPDATE: Added bash command to automatically create the jobs (trigger must be created manually)**

Remember to replace in the below commands the following fields:

- image (from the previous command)
- service-account (replace "myproject" with your project id)
- intemo_host
- intemo_pass
- intemo_user

**IMPORTANT: You need to create two jobs, one with action "start" and another one with action "exit"**

```bash
export ACTION=start
# export ACTION=exit <-- Use this to create the exit job, the other parameters are the same
gcloud run jobs create intemo-logger-${ACTION} \
  --image=gcr.io/myproject/intemo-logger@sha256:aaf00145c24943d3a55acc3f9fbe2fb6aaf00145c24943d3a55acc3f9fbe2fb6 \
  --tasks=1 \
  --memory=512Mi \
  --cpu=1000m \
  --task-timeout=10m \
  --max-retries=3 \
  --parallelism=0 \
  --region=europe-west2 \
  --service-account=myproject-compute@developer.gserviceaccount.com \
  --set-env-vars=INTEMO_ACTION=${ACTION},INTEMO_HOST=https://mydomain.com,intemo_pass=mypass,intemo_user=myuser
```

### Set trigger

Click in the new job and select "TRIGGERS".

Add a new scheduled trigger. There are a few parameters to set:

- Name: ``intemo-logger-start-scheduler-trigger`` or ``intemo-logger-exit-scheduler-trigger``
- Frequency: This is a standard cron format. For example:
- - Start: Run each day of the week at 7am: ``0 7 * * 1-5``
- - Exit: Run from monday to thursday at 16:30: ``30 16 * * 1-4``
- - Exit: Run on fridays at 1pm: ``0 13 * * 5``
- Time zone: Search for Spain and select Europe/Madrid.

Example of all the required triggers for my personal use case:

```bash
intemo-logger-exit-scheduler-trigger               europe-west2  30 16 * 1-6 1-4 (Europe/Madrid)    HTTP         ENABLED
intemo-logger-exit-scheduler-trigger-fridays       europe-west2  0 14 * * 5 (Europe/Madrid)         HTTP         ENABLED
intemo-logger-exit-scheduler-trigger-intensiva     europe-west2  30 13 * 7-9 1-5 (Europe/Madrid)    HTTP         ENABLED
intemo-logger-exit-scheduler-trigger-last-quarter  europe-west2  30 16 * 10-12 1-4 (Europe/Madrid)  HTTP         ENABLED
intemo-logger-start-scheduler-trigger              europe-west2  0 7 * * 1-5 (Europe/Madrid)        HTTP         ENABLED
```
