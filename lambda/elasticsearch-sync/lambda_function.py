import json
import boto3
import sys
from fssi_common import *
import requests
from requests_aws4auth import AWS4Auth

region = 'us-west-1'
service = 'es'
esIndex = 'media-index'
esType = ''
headers = { "Content-Type": "application/json" }

esDomainName = FssiResources.ElasticSearch.StageDomain

def getEsEndpoint(esDomainName):
    res = esClient.describe_elasticsearch_domain(DomainName=esDomainName)
    if res and 'DomainStatus' in res:
        endpointUrl = res['DomainStatus']['Endpoint']
        return endpointUrl

def processDbEvent(event, table, itemId, itemData):
    global esDomainName, region, services, esIndex, esType

    host = 'https://' + getEsEndpoint(esDomainName)
    awsAuth = AWS4Auth(ACCESS_KEY, SECRET_KEY, region, service, session_token=SESSION_TOKEN)
    url = host + '/' + esIndex + '/' + esType + '/'
    itemUrl = url + itemId
    if event == 'REMOVE':
        print('delete from index: {}'.format(itemId))
        r = requests.delete(itemUrl, auth = awsAuth)
    else:
        document = itemData
        print('insert document into ES index {}'.format(document))
        print('insert URL {}'.format(url))
        r =requests.put(itemUrl, auth = awsAuth, json = document, headers = headers)

    if r.status_code != 200:
        raise ValueError('error {} while executing request {}: {}'.format(r.status_code, itemUrl, r.content))

def lambda_handler(event, context):
    try:
        print('SNS EVENT ', str(event))

        for record in event['Records']:
            snsRecord = record['Sns']
            messageDict = json.loads(snsRecord['Message'])

            table = messageDict['table']
            event = messageDict['event']
            itemId = messageDict['itemId']
            itemData = messageDict['itemData']

            print('DynamoDB event {} for table {}, item {}: {}'.format(event, table, itemId, itemData))
            processDbEvent(event, table, itemId, itemData)
    except:
        err = reportError()
        print('caught exception:', sys.exc_info()[0])
        return lambdaReply(420, str(err))

    return processedReply()

if __name__ == '__main__':
    sampleEvent = {
                    'Records': [
                        {
                            'EventSource': 'aws:sns',
                            'EventVersion': '1.0',
                            'EventSubscriptionArn': 'arn:aws:sns:us-west-1:756428767688:fssi2019-sns-dynamodb-updates:fe494d9c-3880-4bd5-a6ca-db0f80692a6b',
                            'Sns': {
                                'Type': 'Notification',
                                'MessageId': '85a117f8-787e-5816-aa88-42133f5b9bc5',
                                'TopicArn': 'arn:aws:sns:us-west-1:756428767688:fssi2019-sns-dynamodb-updates',
                                'Subject': None,
                                'Message': '{"table": "fssi2019-dynamodb-media-user-meta", "event": "INSERT", "itemId": "upload/9c8ff173-ef17-45ea-9144-ec42cf8d9268.jpg", "itemData": {"bucket": {"S": "fssi2019-s3-ingest"}, "created": {"S": "2019-09-05 10:24:53.492380"}, "meta": {"M": {"a/c": {"M": {"intensity": {"S": "0.81"}, "sentiment": {"S": "-0.22"}}}, "notworking": {"M": {"intensity": {"S": "1"}, "sentiment": {"S": "0.86"}}}}}, "id": {"S": "upload/9c8ff173-ef17-45ea-9144-ec42cf8d9268.jpg"}}}',
                                'Timestamp': '2019-09-05T17:24:53.999Z',
                                'SignatureVersion': '1',
                                'Signature': 'gPts8OaxptkTM2Vg90hcFtCF0JAEJU9tYqkjzBfNflPLP5z7hN9A2kYJX1ZbyF/V1V3vxvURrdrbWEiq3fWHU5Oxy4yQru8Gp2wXSwqUb+tQqQ51zzVClotWhOXpy9b01VLvmQDO9YyllhfSEvk8Vd965d44V4zFN/lprSNYgoko1s4O8xM7MKeHxQcEk4zyNC9+lDkE2eJggkM2SaFlxn2QrYrxxwFyamds50Vq34eyDdcjJo6WoxP7boglhTOgzYryd0e28IODCZyTUqtUpWf7Ca+6nS9+qBlUywfhz4NoCqK6eR860n7U6chFPjtnFaBXUmW5+hUaDz9+9YjvBQ==',
                                'SigningCertUrl': 'https://sns.us-west-1.amazonaws.com/SimpleNotificationService-6aad65c2f9911b05cd53efda11f913f9.pem',
                                'UnsubscribeUrl': 'https://sns.us-west-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-west-1:756428767688:fssi2019-sns-dynamodb-updates:fe494d9c-3880-4bd5-a6ca-db0f80692a6b',
                                'MessageAttributes': {}
                            }
                        }
                    ]}
    lambda_handler(sampleEvent, None)
