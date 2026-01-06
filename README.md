# YouTube AI Description Manager
This project is a simple GUI application that allows you to generate YouTube descriptions for your local video files in bulk. It also provides a utility to bulk upload those same files and their descriptions to YouTube.

## Usage
The simplest way to get started (for Windows users) is to download one of the executable builds.
In the directory where you keep the .exe, create a client_secrets.json file and a settings.json file.

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

TODO - add instructions for how to create or get these values from Google Console

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
TODO - add where to get this key

## Running from source
TODO explain getting started with venv, what version of Python you'll need, etc... Not very different from what you'd need for running the executable
