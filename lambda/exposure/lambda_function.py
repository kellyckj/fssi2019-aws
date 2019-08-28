import json
import boto3
import sys, traceback
import uuid
import os
from fssi_common import *

class ExposureInput():
    ExperienceIdKey = 'experience_id'
    ExperienceStateKey = 'state'

def lambdaReply(code, message):
    print('lambda reply {}: {}'.format(code, message))
    return {
        'statusCode': code,
        'body': json.dumps(message)
    }

def malformedMessageReply():
    return lambdaReply(420, 'Malformed message received')

def processedReply():
    return lambdaReply(200, 'Message processed')

def getOccupancy(experienceId):
    # get latest occupancy for the experience
    # the occupancy is an array of visitor IDs (QR codes)
    occupancyTable = dynamoDbResource.Table(FssiResources.DynamoDB.Occupancy)
    result = occupancyTable.get_item(Key={'id' : experienceId})
    return result['Item']['occupancy']

def getVisitorExposure(visitorId):
    response = timeseriesGetLatestForKey(FssiResources.DynamoDB.VisitorExposureTs,
      keyName='visitor_id', keyValue=visitorId)

    if response['Count'] > 0:
        return ExposureVector(json.loads(response['Items'][0]['exposure']['S']))
    return ExposureVector({})

def updateExposure(exposureV, emissionV):
    '''Updates visitor exposure vector with emission vector (experience state)

    :param exposureV: Visitor exposure vector
    :param emissionV: Experience emission vector (state)
    :return: Updated visitor exposure vector
    '''

    return ExposureVector.simpleAverage([exposureV, emissionV])

def writeVisitorExposure(visitorId, exposureV):
    # print('VISITOR EXPOSURE UPDATE', visitorId, exposureV)
    timeseriesAdd(FssiResources.DynamoDB.VisitorExposureTs,
      { 'visitor_id' : visitorId,
        'exposure' : json.dumps(exposureV.encode())})

def writeExperienceExposure(experienceId, exposureV):
    # print('EXPERIENCE EXPOSURE UPDATE', experienceId, exposureV)
    timeseriesAdd(FssiResources.DynamoDB.ExperienceExposureTs,
      { 'experience_id' : experienceId,
        'exposure' : json.dumps(exposureV.encode())})

def lambda_handler(event, context):
    try:
        snsRecord = event['Records'][0]['Sns']
        messageDict = json.loads(snsRecord['Message'])
        experienceState = ExperienceState(messageDict)
        experienceOccupancy = getOccupancy(experienceState.experienceId_)

        experienceAggregateExposure = ExposureVector(experienceState.emissionVector_)

        # for each user in the experience -- update their exposure vector
        experienceAggregate = [experienceState.emissionVector_]
        for visitorId in experienceOccupancy:
            # first -- retrieve current exposure vector
            visitorExposure = getVisitorExposure(visitorId)
            # now update exposure vector with current experience state
            # print('VISITOR', visitorId)
            # print('VISITOR EXPOSURE', visitorExposure)
            # print('EXPERIENCE STATE', experienceState)
            updatedExposure = updateExposure(visitorExposure, experienceState.emissionVector_)
            # print('UPDATED VISITOR EXPOSURE', updatedExposure)
            # save visitor exposure back to db
            writeVisitorExposure(visitorId, updatedExposure)
            experienceAggregate.append(visitorExposure)
        # write aggregate experience exposure
        writeExperienceExposure(experienceState.experienceId_, ExposureVector.simpleAverage(experienceAggregate))
    except:
        type, err, tb = sys.exc_info()
        print('caught exception:', err)
        traceback.print_exc(file=sys.stdout)
        return lambdaReply(420, str(err))

    return processedReply()

# for local testing
if __name__ == '__main__':
    sampleEvent = {
                    'Records':[{
                                'Sns':{
                                    'Message' : '{"experience_id":"tactile", "state": {"apple": {"intensity": 0.32896388205408866, "sentiment": 0.7291166671340621}, "longbeach": {"intensity": 0.6507964003090817, "sentiment": -0.15451901775011567}, "pho": {"intensity": 0.9577991223053027, "sentiment": 0.5302774498703153}, "chineesedumplings": {"intensity": 0.09065038989810137, "sentiment": -0.7309778440918324}, "lambgyro": {"intensity": 0.9674758956209828, "sentiment": 0.629708591025866}}}'
                                    }
                                }]
                  }
    lambda_handler(sampleEvent, None)
