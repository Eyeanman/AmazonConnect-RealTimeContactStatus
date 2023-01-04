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
        log.debug(f"Initial Contact Id does not exist, creating {contactid}")
        contactrecord = {
            'InitialContactId': contactid,
            'Timestamps': {
                "eventbridge": "0"
                },
            'History': [],
            'ttl': int(ttl)
        }
        response = ddb_table.put_item(
        Item=contactrecord
        )
        log.debug(response)
    log.info(f"Got Record: {contactrecord}")
    return contactrecord


def process_log_detail(event_detail, ttl):
    contactid = event_detail['contactId']
    contactrecord = get_contactrecord(contactid,ttl)
    # Set Common Attributes
    contactrecord['initiationMethod'] = event_detail['initiationMethod']
    contactrecord['channel'] = event_detail['channel']
    
    # Set Uncommon Attributes
    if event_detail['eventType'] == "INITIATED":
        contactrecord['initiationTimestamp'] = event_detail['initiationTimestamp']
        if 'initialContactId' in event_detail:
            contactrecord['initalContactId1'] = event_detail['initalContactId']
        if 'previousContactId' in event_detail:
            contactrecord['previousContactId'] = event_detail['previousContactId']
    if event_detail['eventType'] == "QUEUED":
        contactrecord['flag_queued'] = True
        contactrecord['queueInfo'] = event_detail['queueInfo']
    if event_detail['eventType'] == "CONNECTED_TO_AGENT":
        contactrecord['flag_connected_to_agent'] = True
        contactrecord['agentInfo'] = event_detail['agentInfo']
    if event_detail['eventType'] == "DISCONNECTED":
        contactrecord['disconnectTimestamp'] = event_detail['disconnectTimestamp']

    contactrecord['History'].append(event_detail)
    unsorted_history = contactrecord['History']
    sorted_history = sorted(unsorted_history, key=lambda d: d['Timestamp'])
    contactrecord['History'] = sorted_history
    if contactrecord['Timestamps']['eventbridge'] < event_detail['Timestamp']:
        contactrecord['Status'] = event_detail['eventType']
        contactrecord['Timestamps']['eventbridge'] = event_detail['Timestamp']
    contactrecord['ttl'] = int(ttl)
    log.debug(f"Updating Contact Record to: {contactrecord}")
    ddb_table.put_item(
        Item=contactrecord
        )


def lambda_handler(event, context):
    log.debug(f"Raw Event Data: {event}")
    event_detail = event['detail']
    event_detail['Timestamp'] = event['time']
    event_detail['LogType'] = "ContactEvent"
    datetime_ttl = datetime.now() + timedelta(hours=6)
    ttl = datetime_ttl.strftime('%s')
    process_log_detail(event_detail, ttl)



    return "Completed"