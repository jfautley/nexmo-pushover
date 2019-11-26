# Nexmo + PushOver == :dancer:
A simple AWS Lambda (using Chalice) function to forward SMS messages from the Nexmo API to PushOver for notifications.

## Deployment
```
$ git clone https://github.com/jfautley/nexmo-pushover && cd nexmo-pushover
<do some venv stuff, probably>
$ pip install -r requirements.txt
<setup AWS credentials>
$ chalice deploy
Creating deployment package.
Creating IAM role: nexmo-pushover-dev
Creating lambda function: nexmo-pushover-dev
Updating rest API
Resources deployed:
  - Lambda ARN: arn:aws:lambda:<region>:123456789012:function:nexmo-pushover-dev
  - Rest API URL: https://<hex>.execute-api.<region>.amazonaws.com/api/
```

## Nexmo Configuration
Set your number/global "SMS Inbound Webhook URL" to the "Rest API URL" output by `chalice deploy` (or found by running `chalice url` after deployment), after appending `/sms`, i.e.:

```https://<hex>.execute-api.<region>.amazonaws.com/api/sms```

You might also need to ensure that your "HTTP Method" is set to **POST-JSON** under your global dashboard settings.
