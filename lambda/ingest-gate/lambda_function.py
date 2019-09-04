import json, base64
import urllib.parse
import boto3
import sys, traceback
import uuid
import os
from fssi_common import *

def lambda_handler(event, context):
    try:
        print('EVENT ', str(event))

        tags = {}
        if 'user_meta' in event["queryStringParameters"]:
            try:
                userMeta = event["queryStringParameters"]['user_meta']
                tags = json.loads(base64.b64decode(urllib.parse.unquote(userMeta)))
            except:
                type, err, tb = sys.exc_info()
                print('caught exception:', err)
                traceback.print_exc(file=sys.stdout)

        print('user meta tags', tags)

        requestFileName = event["queryStringParameters"]['name']
        fileName, fileExtension = os.path.splitext(requestFileName)
        uploadKey = 'upload/' + str(uuid.uuid4()) + fileExtension
        s3 = boto3.client('s3')
        presignedUrl = s3.generate_presigned_url('put_object', {'Bucket':FssiResources.S3Bucket.Ingest ,'Key':uploadKey,  'ContentType':'binary/octet-stream'})

        print('GENERATED PRESIGNED URL for ', requestFileName, presignedUrl)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body' : json.dumps({
                'uploadUrl': presignedUrl,
                'uploadKey': uploadKey
            })
        }

    except:
        type, err, tb = sys.exc_info()
        print('caught exception:', err)
        traceback.print_exc(file=sys.stdout)

    return {
        'statusCode': 404,
        'body': json.dumps('x⸑x')
    }