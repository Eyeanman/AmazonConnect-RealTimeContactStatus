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
CONTACT_RETENTION = os.environ["CONTACT_RETENTION"]
resource_ddb = boto3.resource('dynamodb')
ddb_table = resource_ddb.Table(TABLE_NAME)

import gzip
import json
import base64


def get_contactrecord(contactid, ttl):
    response = ddb_table.get_item(
        Key={
            'Connect_ContactId': contactid
            }
        )
    log.debug(response)
    if 'Item' in response:
        log.debug(f"Initial Contact Id found: {contactid}")
        contactrecord = response['Item']
    else:
        log.debug(f"Initial Contact Id does not exist, creating {contactid}")
        contactrecord = {
            'Connect_ContactId': contactid,
            'Timestamps': {
                "eventbridge": "0"
                },
            'History': [],
            'DDB_ExpiryEpoch': int(ttl)
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
    contactrecord['Connect_InitiationMethod'] = event_detail['initiationMethod']
    contactrecord['Connect_Channel'] = event_detail['channel']
    
    # Set Uncommon Attributes
    contactrecord['initiationTimestamp'] = event_detail['initiationTimestamp']
    if 'initialContactId' in event_detail:
        contactrecord['Connect_initalContactId'] = event_detail['initalContactId']
    if 'previousContactId' in event_detail:
        contactrecord['Connect_previousContactId'] = event_detail['previousContactId']
    if event_detail['eventType'] == "QUEUED":
        contactrecord['Flag_Queued'] = True
        contactrecord['Connect_queueInfo'] = event_detail['queueInfo']
    if event_detail['eventType'] == "CONNECTED_TO_AGENT":
        contactrecord['Flag_Connected_To_Agent'] = True
        contactrecord['Connect_agentInfo'] = event_detail['agentInfo']
    if event_detail['eventType'] == "DISCONNECTED":
        contactrecord['Connect_disconnectTimestamp'] = event_detail['disconnectTimestamp']

    contactrecord['History'].append(event_detail)
    unsorted_history = contactrecord['History']
    sorted_history = sorted(unsorted_history, key=lambda d: d['Timestamp'])
    contactrecord['History'] = sorted_history
    if contactrecord['Timestamps']['eventbridge'] < event_detail['Timestamp']:
        contactrecord['Status'] = event_detail['eventType']
        contactrecord['Timestamps']['eventbridge'] = event_detail['Timestamp']
    contactrecord['DDB_ExpiryEpoch'] = int(ttl)
    log.debug(f"Updating Contact Record to: {contactrecord}")
    ddb_table.put_item(
        Item=contactrecord
        )


def lambda_handler(event, context):
    log.debug(f"Raw Event Data: {event}")
    event_detail = event['detail']
    event_detail['Timestamp'] = event['time']
    event_detail['LogType'] = "ContactEvent"
    datetime_ttl = datetime.now() + timedelta(hours=int(CONTACT_RETENTION))
    ttl = datetime_ttl.strftime('%s')
    process_log_detail(event_detail, ttl)



    return "Completed"