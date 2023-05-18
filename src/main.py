# this function
# gets the simple html page
# updates the login page and logout page address
# returns the content

import json
import boto3
import logging
import os
import time
import hashlib

from botocore.exceptions import ClientError
images_bucket = os.environ['UPLOADER_IMAGES_BUCKET']
default_signedurl_expiry_seconds = os.environ['DEFAULT_SIGNEDURL_EXPIRY_SECONDS']

def handler(event, context):

    uniquehash = hashlib.sha1("{}".format(time.time_ns()).encode('utf-8')).hexdigest()
    result = create_presigned_post(images_bucket, "new/{}|".format(uniquehash[:5]) + "${filename}")

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html'
        },
        'body': file_get_contents("index.html").replace('###preSignedUrl###', json.dumps(result))
    }

def file_get_contents(filename):
    with open(filename) as f:
        return f.read()

# this function
# creates a pre-sighned URL for uploading image to S3 and returns it

def create_presigned_post(bucket_name, object_name, fields=None, conditions=None, expiration=default_signedurl_expiry_seconds):
    s3_client = boto3.client('s3')

    try:
        response = s3_client.generate_presigned_post(bucket_name,
            object_name,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=int(expiration)
        )
    except ClientError as e:
        logging.error(e)
        return None

    return response