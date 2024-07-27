import json
import boto3
from botocore.exceptions import NoCredentialsError

s3 = boto3.client("s3")

BUCKET_NAME = "kids-horror-stories-ru-images"
HTML_FILE_PATH = "index.html"
PASSWORD = "lady-gaga"


def lambda_handler(event, context):
    print(json.dumps(event))

    if event["routeKey"] == "GET /":
        return serve_html()
    elif event["routeKey"] == "POST /":
        return generate_presigned_url(event)
    else:
        return {
            "statusCode": 405,
            "body": json.dumps({"message": "Method Not Allowed"}),
        }


def serve_html():
    try:
        with open(HTML_FILE_PATH, "r") as file:
            html_content = file.read()
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": html_content,
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def generate_presigned_url(event):
    try:
        headers = event["headers"]
        password = headers.get("password")

        if password != PASSWORD:
            return {
                "statusCode": 403,
                "body": json.dumps({"message": "Forbidden: Incorrect password"}),
            }

        body = json.loads(event["body"])
        file_name = "input/" + body["file_name"]
        content_type = body["content_type"]

        presigned_url = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": file_name,
                "ContentType": content_type,
            },
            ExpiresIn=3600,
        )

        return {"statusCode": 200, "body": json.dumps({"url": presigned_url})}
    except NoCredentialsError:
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Credentials not available"}),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
