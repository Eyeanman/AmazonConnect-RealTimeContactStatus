import boto3
import os
import logging

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

def get_contactrecord(contactid):
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
        log.error(f"Initial Contact Id does not exist!")
        return "Error"
    log.info(f"Got Record: {contactrecord}")
    return contactrecord

def append_log(contactrecord, log_message):
    if "contactflowlogs" not in contactrecord:
        contactrecord['contactflowlogs'] = []
    contactrecord['contactflowlogs'].append(log_message)
    contactrecord['latest_contactflow'] = {
        "contactflowname": log_message["ContactFlowName"],
        "contactflowmoduletype" : log_message["ContactFlowModuleType"],
        "timestamp": log_message["Timestamp"]
    }
    if 'latest_timestamp' in contactrecord:
        if log_message["Timestamp"]<contactrecord['latest_timestamp']:
            contactrecord['latest_timestamp'] = log_message["Timestamp"]
    else:
        contactrecord['latest_timestamp'] = log_message["Timestamp"]
    if 'earliest_timestamp' in contactrecord:
        if log_message["Timestamp"]<contactrecord['earliest_timestamp']:
            contactrecord['earliest_timestamp'] = log_message["Timestamp"]
    else:
        contactrecord['earliest_timestamp'] = log_message["Timestamp"]
    log.debug(f"Updating Contact Record to: {contactrecord}")
    ddb_table.put_item(
        Item=contactrecord
        )

def process_log_events(log_events):
    for log_event in log_events:
        log.debug(f'LogEvent: {log_event}')
        log_message = json.loads(log_event['message'])
        log.info(f'Log: {log_message}')
        contactid = log_message['ContactId']
        contactrecord = get_contactrecord(contactid)
        append_log(contactrecord, log_message)

def lambda_handler(event, context):
    log.debug(f"Raw Event Data: {event}")
    log_events = get_eventdata(event)
    log.debug(f"Log Events: {log_events}")
    process_log_events(log_events)



    return "Completed"