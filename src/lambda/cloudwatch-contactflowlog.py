import boto3
import os
import logging
from datetime import datetime, timedelta

# logging
ROOT_LOG_LEVEL = os.environ["ROOT_LOG_LEVEL"]
LOG_LEVEL = os.environ["LOG_LEVEL"]
root_logger = logging.getLogger()
root_logger.setLevel(ROOT_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(LOG_LEVEL)

TABLE_NAME = os.environ["DDB_TABLENAME"]
resource_ddb = boto3.resource('dynamodb')
ddb_table = resource_ddb.Table(TABLE_NAME)

import gzip
import json
import base64


def get_eventdata(event):
    cw_data = event['awslogs']['data']
    compressed_payload = base64.b64decode(cw_data)
    uncompressed_payload = gzip.decompress(compressed_payload)
    payload = json.loads(uncompressed_payload)
    log_events = payload['logEvents']
    return log_events

def get_contactrecord(contactid, ttl):
    response = ddb_table.get_item(
        Key={
            'InitialContactId': contactid
            }
        )
    log.debug(response)
    if 'Item' in response:
        log.debug(f"Initial Contact Id found: {contactid}")
        contactrecord = response['Item']
    else:
        contactrecord = {
            'InitialContactId': contactid,
            'Timestamps': {
                "contactflowlogs": "0"
                },
            'History': [],
            'ttl': int(ttl)
        }
    log.info(f"Got Record: {contactrecord}")
    return contactrecord

def append_log(contactrecord, log_message):
    contactrecord['History'].append(log_message)
    unsorted_history = contactrecord['History']
    sorted_history = sorted(unsorted_history, key=lambda d: d['Timestamp'])
    contactrecord['History'] = sorted_history
    if "contactflowlogs" in contactrecord['Timestamps']:
        if contactrecord['Timestamps']['contactflowlogs'] < log_message['Timestamp']:
            contactrecord['latest_contactflow'] = log_message
            contactrecord['Timestamps']['contactflowlogs'] = log_message['Timestamp']
    else:
        contactrecord['latest_contactflow'] = log_message
        contactrecord['Timestamps']['contactflowlogs'] = log_message['Timestamp']

    log.debug(f"Updating Contact Record to: {contactrecord}")
    ddb_table.put_item(
        Item=contactrecord
        )

def process_log_events(log_events, ttl):
    for log_event in log_events:
        log.debug(f'LogEvent: {log_event}')
        log_message = json.loads(log_event['message'])
        log.info(f'Log: {log_message}')
        contactid = log_message['ContactId']
        contactrecord = get_contactrecord(contactid, ttl)
        log_message['LogType'] = "ContactFlowLog"
        append_log(contactrecord, log_message)

def lambda_handler(event, context):
    log.debug(f"Raw Event Data: {event}")
    log_events = get_eventdata(event)
    log.debug(f"Log Events: {log_events}")
    datetime_ttl = datetime.now() + timedelta(hours=6)
    ttl = datetime_ttl.strftime('%s')
    process_log_events(log_events, ttl)



    return "Completed"