# YouTube AI Description Manager
This project is a simple GUI application that allows you to generate YouTube descriptions for your local video files in bulk. It also provides a utility to bulk upload those same files and their descriptions to YouTube.

## Usage
The simplest way to get started (for Windows users) is to download one of the executable builds.

In the directory where you keep the .exe, create a client_secrets.json file and a settings.json file.

Once you start the program with your appropriate OAuth credentials, you will likely be prompted to use your browser to allow it permissions to upload on behalf of your account and YouTube channel. Choose values as appropriate.

## client_secrets.json
This is where you'll need to store your credentials that allow you to upload videos to YouTube.

Should be in the following format
```
{"installed":
  {"client_id":"yourclientid.apps.googleusercontent.com",
  "project_id":"yourprojectid","auth_uri":"https://accounts.google.com/o/oauth2/auth",
  "token_uri":"https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs",
  "client_secret":"yourclientsecret",
  "redirect_uris":["http://localhost"]
}}

```

You can acquire an OAuth 2.0 client ID and client secret from the Google API Console at https://console.cloud.google.com/.
 
Please ensure that you have enabled the YouTube Data API for your project.

For more information about using OAuth2 to access the YouTube Data API, see: https://developers.google.com/youtube/v3/guides/authentication

For more information about the client_secrets.json file format, see: https://developers.google.com/api-client-library/python/guide/aaa_client_secrets

## settings.json
These are more like preferences, but do include your Gemini API key that you'll need for Description generation.

The only required value is google_ai_api_key, the rest can be populated from Settings in the application.
```
{
    "max_consecutive_errors": 3,
    "max_upload_retries": 10,
    "google_ai_api_key": "YourGeminiAPIKeyHere"
}
```

You can find this key at https://aistudio.google.com/app/api-keys once you've logged in. If you don't have one, you will need to create one

## Running from source
Make sure you have Python3 installed on your machine and available on the PATH

After cloning the repo, navigate to the root in a terminal

Run
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create and populate your settings.json and client_secrets.json in the same directory as described above.

Then run

```
python3 main.py
```
