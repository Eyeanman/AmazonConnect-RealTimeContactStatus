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
        contactrecord = {
            'Connect_ContactId': contactid,
            'History': [],
            'DDB_ExpiryEpoch': int(ttl)
        }
    log.info(f"Got Record: {contactrecord}")
    return contactrecord

def append_parameters(contactid, parameters, ttl):
    contactrecord = get_contactrecord(contactid, ttl)
    for parameter in parameters:
        contactrecord[parameter] = parameters['parameter']
    contactrecord['DDB_ExpiryEpoch'] = int(ttl)
    log.debug(f"Updating Contact Record to: {contactrecord}")
    ddb_table.put_item(
        Item=contactrecord
        )

def lambda_handler(event, context):
    log.debug(f"Event: {event}")
    datetime_ttl = datetime.now() + timedelta(hours=int(CONTACT_RETENTION))
    ttl = datetime_ttl.strftime('%s')
    contactid = event['Details']['ContactData']['ContactId']
    parameters = event['Details']['Parameters']
    parameters['LogType'] = "ContactFlowLambda"
    append_parameters(contactid, parameters, ttl)



    return "Completed"