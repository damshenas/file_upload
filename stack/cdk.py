import yaml
import typing

from aws_cdk import (
    aws_s3 as _s3,
    aws_cloudformation,
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

class S3ImageUploaderStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        with open("stack/config.yml", 'r') as stream:
            configs = yaml.safe_load(stream)

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
        api_gateway_get_signedurl_resource = api_gateway_resource.add_resource('signedUrl')
        api_gateway_image_search_resource = api_gateway_resource.add_resource('search')

        ### landing page function
        get_landing_page_function = Function(self, "UPLOADER_GET_LANDING_PAGE",
            function_name="UPLOADER_GET_LANDING_PAGE",
            runtime=Runtime.PYTHON_3_7,
            handler="main.handler",
            code=Code.from_asset("./src/landingPage"))

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

        ### get signed URL function
        get_signedurl_function = Function(self, "UPLOADER_GET_SIGNED_URL",
            function_name="UPLOADER_GET_SIGNED_URL",
            environment={
                "UPLOADER_IMAGES_BUCKET": images_S3_bucket.bucket_name,
                "DEFAULT_SIGNEDURL_EXPIRY_SECONDS": configs["Functions"]["DefaultSignedUrlExpirySeconds"]
            },
            runtime=Runtime.PYTHON_3_7,
            handler="main.handler",
            code=Code.from_asset("./src/getSignedUrl"))

        get_signedurl_integration = LambdaIntegration(
            get_signedurl_function,
            proxy=True,
            integration_responses=[IntegrationResponse(
                status_code='200',
                response_parameters={
                   'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            )])

        get_signedurl_method = api_gateway_get_signedurl_resource.add_method('GET', get_signedurl_integration,
            method_responses=[MethodResponse(
                status_code='200',
                response_parameters={
                    'method.response.header.Access-Control-Allow-Origin': True,
                }
            )])
        
        signedurl_custom_resource = typing.cast("aws_cloudformation.CfnCustomResource", get_signedurl_method.node.find_child('Resource'))
        signedurl_custom_resource.add_property_override('AuthorizerId', api_gateway_get_signedurl_authorizer.ref)

        images_S3_bucket.grant_put(get_signedurl_function, objects_key_pattern="new/*")

        ### API gateway finalizing
        self.add_cors_options(api_gateway_get_signedurl_resource)
        self.add_cors_options(api_gateway_landing_page_resource)
        self.add_cors_options(api_gateway_image_search_resource)

        ### outputs
        CfnOutput(self, 'LandingPage',
            value=api_gateway.url_for_path('/web'),
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
