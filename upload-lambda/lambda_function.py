import json
import base64
import os
import boto3

s3 = boto3.client("s3")

BUCKET_NAME = "kids-horror-stories-ru-images"
HTML_FILE_PATH = "index.html"
PASSWORD = "lady-gaga"


def lambda_handler(event, context):
    print(json.dumps(event))

    if event["routeKey"] == "GET /":
        return serve_html()
    elif event["routeKey"] == "POST /":
        return upload_files(event)
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


def upload_files(event):
    try:
        headers = event["headers"]
        password = headers.get("password")

        if password != PASSWORD:
            return {
                "statusCode": 403,
                "body": json.dumps({"message": "Forbidden: Incorrect password"}),
            }

        body = json.loads(event["body"])
        files = body["files"]

        for file in files:
            file_name = file["file_name"]
            key = f"input/{file_name}"
            content_type = file["content_type"]
            file_content = base64.b64decode(file["file_content"])

            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=key,
                Body=file_content,
                ContentType=content_type,
            )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Files uploaded successfully"}),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
