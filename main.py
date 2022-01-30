#!/usr/bin/env python3
# Telegran_alerts
# Script by @dssalazaru

import os, re, ssl, time
from urllib.request import urlopen
import urllib.parse

testing = False # Set True for testing

# ----------------------------------------------------------
# Telegram Bot & Chat data
chat_id = "-000000000000"
chat_id_testing = "-000000000000"
token = '0000000000:AAAAAAAAAAAAA_00AAAAA0AAA0AAAA0A'
# Check MK config
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
# General data
date = time.ctime()
file = "/tmp/cmk_status"

tmpl_host_text = """*Check_MK: $HOSTNAME$ - $EVENT_TXT$*
`Host:     $HOSTNAME$`
`Address:  $HOSTADDRESS$`
`Event:    $EVENT_TXT$`
`Output:   $HOSTOUTPUT$`

$LONGHOSTOUTPUT$
"""

tmpl_service_text = """*Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$*
Host:     $HOSTNAME$
Address:  $HOSTADDRESS$
Service:  $SERVICEDESC$
Event:    $EVENT_TXT$
Output:   $SERVICEOUTPUT$

$LONGSERVICEOUTPUT$
"""

tmpl_active_host = """
===============================
*Host:          $HOST$*
Status:        DOWN
Date:          $DATE$
===============================
"""
# ----------------------------------------------------------

def main():
    global msg
    try:
        if testing:
            host = "HOST | 10.10.10.10"; status = "UP" # Change status to UP or DOWN to test
            msg = host + "\n" + status
        context = fetch_notification_context()
        if len(context) == 0: send_active_alert()
        else:
            msg = construct_message_text(context)
            host = context["HOSTNAME"] + " | " + context["HOSTADDRESS"]; status = context["HOSTSTATE"]
            status_check(host, status)
    except Exception as err:
        send_error("main", err)

# ----------------------------------------------------------
# Get context and format normal alert msg 

def fetch_notification_context(): # fetch all data from host down
    context = {}
    try:
        for (var, value) in os.environ.items():
            if var.startswith("NOTIFY_"):
                context[var[7:]] = value
    except Exception as err:
        send_error("data_symon", err)
    return context

# Generate the normal message from a template

def construct_message_text(context):
    notification_type = context["NOTIFICATIONTYPE"]
    if notification_type in [ "PROBLEM", "RECOVERY" ]:
        txt_info = "$PREVIOUS@HARDSHORTSTATE$ -> $@SHORTSTATE$"
    elif notification_type.startswith("FLAP"):
        if "START" in notification_type:
            txt_info = "Started Flapping"
        else:
            txt_info = "Stopped Flapping ($@SHORTSTATE$)"
    elif notification_type.startswith("DOWNTIME"):
        what = notification_type[8:].title()
        txt_info = "Downtime " + what + " ($@SHORTSTATE$)"
    elif notification_type == "ACKNOWLEDGEMENT":
        txt_info = "Acknowledged ($@SHORTSTATE$)"
    elif notification_type == "CUSTOM":
        txt_info = "Custom Notification ($@SHORTSTATE$)"
    else:
        txt_info = notification_type # Should neven happen

    txt_info = substitute_context(txt_info.replace("@", context["WHAT"]), context)

    context["EVENT_TXT"] = txt_info

    if context['WHAT'] == 'HOST':
        tmpl_text = tmpl_host_text
    else:
        tmpl_text = tmpl_service_text

    return substitute_context(tmpl_text, context)

# Replace all values in template

def substitute_context(template, context):
    # First replace all known variables
    for varname, value in context.items():
        template = template.replace('$'+varname+'$', value)

    # Remove the rest of the variables and make them empty
    template = re.sub("\$[A-Z_][A-Z_0-9]*\$", "", template)
    return template

# If the host is UP send a new notification

def status_check(host, status):
    if status == "DOWN":
        add_line(host)
    elif status == "UP":
        remove_line(host)
        send_telegram_message(msg)
    else:
        send_error("status_check", "Status desconocido")

# When the host is DOWN add a new line in the file cmk_status

def add_line(line):
    try:
        with open(file, "a") as f:
            f.write(line + "\n")
            f.close()
        send_telegram_message(msg)
    except Exception as err:
        send_error("add_line", err)

# When the host is UP remove the host line in the file cmk_status

def remove_line(line):
    try:
        data = open(file).readlines()
        hosts = [h.replace("\n", "") for h in list(set(data))]
        for h in hosts:
            if line == h:
                hosts.remove(line)
        sort_file(hosts)
    except Exception as err:
        send_error("remove_line", err)

# Read file and send notification

def send_active_alert():
    hosts = read_file()
    for host in hosts:
        if len(host) <= 0:
            sort_file(hosts)
        else:
            text = tmpl_active_host.replace("$HOST$", host)
            text = text.replace("$DATE$", date)
            send_telegram_message(text)

# Open cmk_status file and get all hosts

def read_file():
    try:
        data = open(file).readlines()
        hosts = [h.replace("\n", "") for h in list(set(data))]
        if "\\n" in hosts:
            remove_line("\\n")
            hosts = read_file()
        return hosts
    except Exception as err:
        send_error("read_file", err)

# Read cmk_status file for remove empty lines

def sort_file(hosts):
    try:
        f = open(file, "w")
        for h in hosts:
            if len(h) > 0:
                f.write(h + "\n")
    except Exception as err:
        send_error("sort_file", err)

# Send Telegram notification with the error to chat

def send_error(funcion, err):
    error = f"""**Error en [ {funcion} ]**
    {date}
    {str(err)}
    """
    send_telegram_message(error)
    exit() # Errores o data erronea

# Send Telegran notification

def send_telegram_message(msg):
        chat = chat_id_testing if testing else chat_id
        url = 'https://api.telegram.org/bot%s/sendMessage' % (token)
        data = urllib.parse.urlencode({'chat_id':chat, 'text':msg, 'parse_mode':'Markdown'}).encode("utf-8")
        urlopen(url, data=data, context=ctx).read()

# ------------------------------------------------------------
# Run program

if __name__ == "__main__":
    main()