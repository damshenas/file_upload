#!/usr/bin/env python3

from aws_cdk import App

from stack.cdk import S3ImageUploaderStack

app = App()
S3ImageUploaderStack(app, "S3ImageUploader", env={'region': 'eu-central-1'})

app.synth()
