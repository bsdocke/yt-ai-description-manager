import os
import time
import google.generativeai as genai
import config

def configure_ai_service():
    """Configures the Google AI service with the provided API key."""
    try:
        if not config.GOOGLE_AI_API_KEY:
            print("Error: Google AI API Key is missing.")
            return False
        genai.configure(api_key=config.GOOGLE_AI_API_KEY)
        print("Google AI service configured successfully.")
        return True
    except Exception as e:
        print(f"Error configuring Google AI service: {e}")
        print("Please ensure your GOOGLE_AI_API_KEY is valid.")
        return False


def get_video_files(directory):
    """
    Identifies video files in the specified directory based on common extensions.

    Args:
        directory (str): The path to the directory to scan.

    Returns:
        list: A list of full paths to video files found.
    """
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv"}
    found_files = []
    print(f"\nScanning for video files in '{os.path.abspath(directory)}'...")
    try:
        for filename in os.listdir(directory):
            if os.path.splitext(filename)[1].lower() in video_extensions:
                full_path = os.path.join(directory, filename)
                found_files.append(full_path)
        print(f"Found {len(found_files)} video file(s).")
        return found_files
    except FileNotFoundError:
        print(f"Error: The directory '{directory}' was not found.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while scanning the directory: {e}")
        return []

def generate_description(video_path):
    """
    Uploads a video, analyzes it with Gemini, and generates a description.

    Args:
        video_path (str): The full path to the video file.

    Returns:
        str: The generated description for the video.
    """
    print(f"\nProcessing '{os.path.basename(video_path)}'...")

    # 1. Upload the video file to the AI service
    print("Uploading file to AI service...")
    video_file = genai.upload_file(path=video_path)

    # Wait for the upload and initial processing to complete
    while video_file.state.name == "PROCESSING":
        time.sleep(10)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise ValueError("Video file processing failed on the server.")

    print("File uploaded successfully.")

    # 2. Define the prompt for the model
    filename = os.path.basename(video_path)
    prompt = f"""
    Based on the content of this video and its filename, "{filename}", please perform the following tasks:

    1.  Write a compelling, concise, and SEO-friendly description for a YouTube video. The description should be a single, engaging paragraph that accurately summarizes the video's content. Please avoid using the word iconic or classic.
    2.  If there is any relevant trivia about the company, product, or people who appear in the video, you can include a second brief paragraph that presents this info in an interesting way. If not, do not add a second paragraph.

    The tone should be suitable for a general YouTube audience. Format the output clearly with line breaks, but do not use markdown or bullets or any kind, including numerical listing.
    """


    # 3. Generate content using the Gemini 1.5 Flash model
    print("Generating description with Gemini...")
    model = genai.GenerativeModel(model_name="models/gemini-flash-latest")
    response = model.generate_content([prompt, video_file], request_options={"timeout": 600})


    # 4. Clean up the uploaded file from the server
    genai.delete_file(video_file.name)
    print("Cleaned up uploaded file from server.")

    return response.text


def process_videos(directory, on_complete):
    """
    Orchestrates the video processing workflow.
    """
    if not configure_ai_service():
        on_complete()
        return

    video_files = get_video_files(directory)

    if not video_files:
        print("No video files to process.")
        on_complete()
        return

    consecutive_error_count = 0

    for video_path in video_files:
        try:
            description_text = generate_description(video_path)

            # Save the description to a text file
            description_filename = os.path.splitext(video_path)[0] + ".txt"
            with open(description_filename, "w", encoding="utf-8") as f:
                f.write(description_text)

            print(f"Successfully created description: '{os.path.basename(description_filename)}'")
            # Reset error count on success
            consecutive_error_count = 0

        except Exception as e:
            print(f"--- ERROR: Failed to process file '{os.path.basename(video_path)}' ---")
            print(f"Issue: {e}")
            print("-------------------------------------------------------------------")
            consecutive_error_count += 1
            if consecutive_error_count > config.MAX_CONSECUTIVE_ERRORS:
                print(f"\nCRITICAL: Reached {consecutive_error_count} consecutive errors.")
                print("Stopping process to prevent further issues.")
                break

        # A small delay to respect API rate limits
        time.sleep(2)

    print("\nProcessing finished.")
    on_complete()
