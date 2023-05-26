from aws_cdk import (
    aws_s3 as _s3,
    aws_sns as _sns,
    aws_s3_notifications as _s3n,
    Stack,
    CfnOutput
)

from aws_cdk.aws_apigateway import (
    RestApi,
    LambdaIntegration,
    MockIntegration,
    PassthroughBehavior,
    IntegrationResponse,
    MethodResponse
)

from aws_cdk.aws_lambda import (
    Code,
    Function,
    Runtime
)

from constructs import Construct

configs = {
    "ProjectName" : "S3FILEUPLOAD",
    "Functions": {
        "DefaultSignedUrlExpirySeconds": "86400"
        }
}

class S3ImageUploaderStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ### S3 core
        images_S3_bucket = _s3.Bucket(self, "S3_IMAGES")

        images_S3_bucket.add_cors_rule(
            allowed_methods=[_s3.HttpMethods.POST],
            allowed_origins=["*"] # add API gateway web resource URL
        )

        ### api gateway core
        api_gateway = RestApi(self, 'UPLOADER_API_GATEWAY', rest_api_name='S3ImageUploaderApiGateway')
        api_gateway_resource = api_gateway.root.add_resource(configs["ProjectName"])
        api_gateway_landing_page_resource = api_gateway_resource.add_resource('web')

        ### landing page function
        get_landing_page_function = Function(self, "UPLOADER_GET_LANDING_PAGE",
            function_name="UPLOADER_GET_LANDING_PAGE",
            environment={
                "UPLOADER_IMAGES_BUCKET": images_S3_bucket.bucket_name,
                "DEFAULT_SIGNEDURL_EXPIRY_SECONDS": configs["Functions"]["DefaultSignedUrlExpirySeconds"]
            },
            runtime=Runtime.PYTHON_3_7,
            handler="main.handler",
            code=Code.from_asset("./src"))

        get_landing_page_integration = LambdaIntegration(
            get_landing_page_function,
            proxy=True,
            integration_responses=[IntegrationResponse(
                status_code='200',
                response_parameters={
                    'method.response.header.Access-Control-Allow-Origin': "'*'"
                }
            )])

        api_gateway_landing_page_resource.add_method('GET', get_landing_page_integration,
            method_responses=[MethodResponse(
                status_code='200',
                response_parameters={
                    'method.response.header.Access-Control-Allow-Origin': True
                }
            )])
        
        images_S3_bucket.grant_put(get_landing_page_function, objects_key_pattern="new/*")

        ### API gateway finalizing
        self.add_cors_options(api_gateway_landing_page_resource)

        ### File fupload notification
        new_upload_topic = _sns.Topic(self, "NewFileUploadedTopic")
        images_S3_bucket.add_event_notification(_s3.EventType.OBJECT_CREATED, _s3n.SnsDestination(new_upload_topic))

        ### outputs
        CfnOutput(self, 'LandingPage',
            value="{}{}/web".format(api_gateway.url_for_path('/'), configs['ProjectName']),
            description='The landing page'
        )

    def add_cors_options(self, apigw_resource):
        apigw_resource.add_method('OPTIONS', MockIntegration(
            integration_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,OPTIONS'"
                }
            }
            ],
            passthrough_behavior=PassthroughBehavior.WHEN_NO_MATCH,
            request_templates={"application/json":"{\"statusCode\":200}"}
        ),
        method_responses=[{
            'statusCode': '200',
            'responseParameters': {
                'method.response.header.Access-Control-Allow-Headers': True,
                'method.response.header.Access-Control-Allow-Methods': True,
                'method.response.header.Access-Control-Allow-Origin': True,
                }
            }
        ],
    )
