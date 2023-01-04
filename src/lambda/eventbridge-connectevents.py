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
        log.debug(f"Initial Contact Id does not exist, creating {contactid}")
        contactrecord = {
            'InitialContactId': contactid,
            'Timestamps': {
                "eventbridge": "0"
                },
            'History': {
                "contact_status":[]
            }
            }
        response = ddb_table.put_item(
        Item=contactrecord
        )
        log.debug(response)
    log.info(f"Got Record: {contactrecord}")
    return contactrecord


def process_log_detail(event_detail):
    if 'initialContactId' in event_detail:
        contactid = event_detail['initialContactId']
    else:
        contactid = event_detail['contactId']
    contactrecord = get_contactrecord(contactid)
    contactrecord['History']['contact_status'].append(event_detail)
        
    if event_detail["timestamp"] > contactrecord['Timestamps']['eventbridge']:
        contactrecord['contact_status'] = event_detail['eventType']
        contactrecord['Timestamps']['eventbridge'] = event_detail['timestamp']

    log.debug(f"Updating Contact Record to: {contactrecord}")
    ddb_table.put_item(
        Item=contactrecord
        )

def lambda_handler(event, context):
    log.debug(f"Raw Event Data: {event}")
    event_detail = event['detail']
    event_detail['timestamp'] = event['time']
    process_log_detail(event_detail)



    return "Completed"