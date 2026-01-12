import os
import sys
import time
import random
import re
import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow
import config

def get_authenticated_service(args):
    flow = flow_from_clientsecrets(config.CLIENT_SECRETS_FILE,
                                   scope=config.YOUTUBE_UPLOAD_SCOPE,
                                   message=config.MISSING_CLIENT_SECRETS_MESSAGE)

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)

    return build(config.YOUTUBE_API_SERVICE_NAME, config.YOUTUBE_API_VERSION,
                 http=credentials.authorize(httplib2.Http()))

def initialize_upload(youtube, options):
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    body=dict(
        snippet=dict(
            title=options.title,
            description=options.description,
            tags=tags,
            categoryId=24
        ),
        status=dict(
            privacyStatus="private",
            selfDeclaredMadeForKids=False
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    print("Video id '%s' was successfully uploaded." % response['id'])
                    return True
                else:
                    print("The upload failed with an unexpected response: %s" % response)
                    return False
        except HttpError as e:
            if e.resp.status in config.RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                     e.content)
            else:
                raise
        except config.RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

        if error is not None:
            print(error)
            retry += 1
            if retry > config.MAX_RETRIES:
                print("No longer attempting to retry.")
                return False

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print("Sleeping %f seconds and then retrying..." % sleep_seconds)
            time.sleep(sleep_seconds)
    return False

def start_yt_upload(directory, on_complete):
    argparser.add_argument("--category", default="22",
                           help="Numeric video category. " +
                                "See https://developers.google.com/youtube/v3/docs/videoCategories/list")
    argparser.add_argument("--keywords", help="Video keywords, comma separated",
                           default="")
    argparser.add_argument("--privacyStatus", choices=config.VALID_PRIVACY_STATUSES,
                           default=config.VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
    args = argparser.parse_args()

    youtube = get_authenticated_service(args)

    uploaded_dir = os.path.join(directory, "Uploaded")
    os.makedirs(uploaded_dir, exist_ok=True)

    for filename in os.listdir(directory):
        if filename.endswith(".mp4"):
            video_path = os.path.join(directory, filename)

            # Format the title by replacing periods with spaces and wrapping a trailing year in parentheses
            title = os.path.splitext(filename)[0]
            title = title.replace('.', ' ')
            title = re.sub(r' (\d{4})$', r' (\1)', title)

            description_filename = filename.replace(".mp4", ".txt")
            description_path = os.path.join(directory, description_filename)

            description = ""
            if os.path.exists(description_path):
                with open(description_path, "r", encoding="utf-8") as f:
                    description = f.read()

            # Add file-specific details to the args object
            args.file = video_path
            args.title = title
            args.description = description

            upload_successful = False
            try:
                upload_successful = initialize_upload(youtube, args)
            except HttpError as e:
                print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
                if "quota" in e.content.decode('utf-8'):
                    print("Quota exceeded. Quitting uploads.")
                    return


            if upload_successful:
                print("Upload successful. Moving files...")
                try:
                    dest_video_path = os.path.join(uploaded_dir, filename)
                    os.rename(video_path, dest_video_path)

                    if os.path.exists(description_path):
                        dest_description_path = os.path.join(uploaded_dir, description_filename)
                        os.rename(description_path, dest_description_path)
                except IOError as e:
                    print("An IO error occurred. Upload succeeded but file movement failed. Continuing: %s" % e)
    on_complete()
