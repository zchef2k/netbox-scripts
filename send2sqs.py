import requests
import json
import os
from extras.scripts import Script
from requests_aws4auth import AWS4Auth

# vars
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")

class SendEventToSQS_Requests(Script):
    """
    A NetBox script that uses 'requests' to send an event to SQS.
    Relies on 'requests-aws4auth' for SigV4 signing.
    """
    class Meta:
        name = "SQS Event Forwarder (Requests)"
        description = "Forwards a NetBox event to AWS SQS using the 'requests' library."
        hidden = True

    def run(self, data, commit):
        """
        This 'run' method is called by the Event Rule.
        The 'data' parameter IS the event payload from NetBox.
        """

        # pre-validation of completeness
        if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, SQS_QUEUE_URL]):
            self.log_failure(
                "Missing AWS environment variables (KEY_ID, SECRET_KEY, REGION, SQS_QUEUE_URL). Cannot send message."
            )
            return

        self.log_info(f"Received event: {data.get('event')} for model {data.get('model')}")

        try:
            # build auth package
            auth = AWS4Auth(
                AWS_ACCESS_KEY_ID,
                AWS_SECRET_ACCESS_KEY,
                AWS_REGION,
                'sqs'  # The AWS service name
            )

            # prepare event payload
            message_body_string = json.dumps(data)

            # SQS API expects 'application/x-www-form-urlencoded' data,
            # not raw json
            post_data = {
                'Action': 'SendMessage',
                'MessageBody': message_body_string
                # Add 'MessageGroupId' here if using a FIFO queue
                # 'MessageGroupId': data.get('model', 'netbox-event')
            }

            # make the request
            self.log_info(f"Sending event to {SQS_QUEUE_URL}...")
            
            response = requests.post(
                SQS_QUEUE_URL,
                data=post_data,
                auth=auth
            )

            # log result
            response.raise_for_status() 

            self.log_success(f"Successfully forwarded event to SQS. Response: {response.text}")
            return f"Sent to SQS. Response: {response.text}"

        except requests.exceptions.HTTPError as e:
            # catch error return codes
            self.log_failure(f"HTTP Error sending to SQS: {e.response.status_code} - {e.response.text}")
            return str(e)
        except Exception as e:
            self.log_failure(f"A general error occurred: {e}")
            return str(e)