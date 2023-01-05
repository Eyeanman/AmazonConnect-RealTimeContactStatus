# AmazonConnect-RealTimeContactStatus
Tracks the current status of each Contact taking data from various sources

## Features
* A item will be created in DynamoDb when ever an event is triggered from:
    * Event Bridge Contact Events (https://docs.aws.amazon.com/connect/latest/adminguide/contact-events.html#contact-events-data-model)
    * Amazon Connect Contact Flow Logs from Cloud Watch (https://docs.aws.amazon.com/connect/latest/adminguide/about-contact-flow-logs.html)
* Various Flags and "Latest" Attributes are created for ease of referencing/viewing e.g:
    * Has Contact Queued
    * Has Contact Connected to Agent
    * What was the last Contact Flow/Block experienced
* History of all Logs received, sorted by timestamp
* Items are deleted after X minutes of the last log being received

## Deployment
Deploy the CloudFormation Template found in [/src/cloudformation](/src/cloudformation/), completing the following Parameters:
* Environment (Dev/Sit/PreProd/Prod)
* Logging Level for Lambda's
* Logging Level for Lambda Dependancies
* Contact Status Retention in Minutes (Default is 1 Day / 1440 minutes)
* Amazon Connect Instance Name (required to view Contact Flow Logs)
* Amazon Connect Instance Arn (required to create Event Bridge Rule)

Once deployed, data will start to be populated in DynamoDb Table (Stack output  "oDynamoDbTableAmazonConnectContactStatusTableName" ) when ever a contact is created in Amazon Connect

Lambda's are currently hardcoded into the CloudFormation Template for ease of deployment, the masters are in [/src/lambda/](/src/lambda/) and should be copied over to the CloudFormation Template when changes are made.

## Schema
|Attribute |Description |
|-----------|-------------|
|Connect_ContactId |Primary Key as the basis for majority of events |
|DDB_ExpiryEpoch|The TTL of the record as set by the CloudFormation Template, once this expires, DDB will delete the record automatically|
|Customer_Identifier|Global Secondary Index to allow looking up of historic contacts from the same customer|
|Flag_*|Flags to show different statuses e.g. Queued, Connected to Agent etc|
|Connect_*|Connect Related data such as InitiationMethod, Queue Info, Agent Info, Latest Contact Flow etc|
|History|History of Logs received for this Contact|
|Timestamps| List of Timestamps to ensure only the latest logs are being placed into Latest attributes|
|Status| Latest Status of Contact, e.g. INITIATED, QUEUED, CONNECTED_TO_AGENT, DISCONNECTED|

## TODO
* Lambda to insert data from within Contact Flows
* Lambda to lookup historic contacts to allow different decisions to be made, e.g.:
    * If callback currently active, advise customer and either cancel callback or disconnect call
    * If Voice/Chat currently active, ask which they prefer to continue with and disconnect the other
    * If recently Contacted, ask if its regarding the same thing and go directly to that queue
* Insert data from Agent Events Streams (if viable...)
* Readable View of Customer Experience split into Friendly and Techy:
    * Friendly: Prompts Heard, Options Selected
    * Techy: Attributes Stored, Lambda's Invoked and their durations
* Move Items to more sustainable storage for long term access (e.g. S3?)

## Gotcha's
* A Call/Chat can have multiple Contacts, so if doing something on Disconnect, ensure all related ContactId's are also disconnected