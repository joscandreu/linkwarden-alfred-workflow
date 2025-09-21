#!/usr/bin/env python3
"""
Save link to Linkwarden - Action Script (Step 2: Process the save)
Handles the actual saving with tags and collection assignment
"""

import sys
import os
import json
import re
from urllib.parse import urlparse
from linkwarden_api import LinkwardenAPI


def extract_save_data_from_arg(arg: str) -> dict:
    """Extract save data from the argument passed from the script filter"""
    import json

    if arg.startswith('save_enhanced:'):
        try:
            json_str = arg.replace('save_enhanced:', '')
            return json.loads(json_str)
        except:
            return {'url': arg, 'tags': [], 'collections': []}
    elif arg.startswith('save_url:'):
        # Legacy format support
        url = arg.replace('save_url:', '')
        return {'url': url, 'tags': [], 'collections': []}
    else:
        # Just a URL
        return {'url': arg, 'tags': [], 'collections': []}


def get_page_title(url: str) -> str:
    """Attempt to get page title (basic implementation)"""
    try:
        import urllib.request

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8', errors='ignore')

            # Simple title extraction
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # Clean up title
                title = re.sub(r'\s+', ' ', title)
                return title[:200]  # Limit title length

    except Exception:
        pass

    # Fallback to domain name
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return "Saved Link"


def show_notification(title: str, message: str, sound: bool = True):
    """Show enhanced macOS notification with sound"""
    try:
        import subprocess

        # Escape quotes and special characters
        safe_message = message.replace('"', '\\"').replace('\\', '\\\\')
        safe_title = title.replace('"', '\\"').replace('\\', '\\\\')

        # Build AppleScript with sound and subtitle
        applescript = f'''
        display notification "{safe_message}" with title "{safe_title}" subtitle "Linkwarden Alfred Workflow"
        '''

        if sound:
            applescript += ' sound name "Glass"'

        subprocess.run([
            'osascript', '-e', applescript
        ], check=True, capture_output=True, text=True)

        print(f"Notification sent: {title} - {message}")

        # Also try to use the more modern user notification center if available
        try:
            import subprocess
            subprocess.run([
                'osascript', '-e',
                f'''
                set theTitle to "{safe_title}"
                set theMessage to "{safe_message}"
                display notification theMessage with title theTitle subtitle "Alfred Workflow" sound name "Glass"
                '''
            ], check=False, capture_output=True, text=True, timeout=2)
        except:
            pass

    except Exception as e:
        print(f"Failed to show notification: {e}")
        print(f"   Title: {title}")
        print(f"   Message: {message}")

        # Fallback: try simpler notification
        try:
            import subprocess
            subprocess.run([
                'osascript', '-e',
                f'display notification "{safe_message}"'
            ], check=False, timeout=1)
        except:
            pass


def get_user_input_for_tags_and_collection(api: LinkwardenAPI, url: str) -> dict:
    """Get user input for tags and collection using Alfred dialogs"""
    try:
        import subprocess

        # Get available collections for suggestions
        collections = api.get_collections()
        collection_names = [col.get('name', '') for col in collections if col.get('name')]

        # Get available tags for suggestions
        tags = api.get_tags()
        tag_names = [tag.get('name', '') for tag in tags if tag.get('name')]

        # Simple approach: use AppleScript dialogs
        # In a real implementation, you might want to create a more sophisticated interface

        # Get tags
        tag_prompt = "Enter tags (comma-separated):"
        if tag_names:
            tag_prompt += f"\n\nSuggested tags: {', '.join(tag_names[:10])}"

        tag_script = f'''
        tell application "System Events"
            set response to display dialog "{tag_prompt}" default answer "" with title "Add Tags"
            return text returned of response
        end tell
        '''

        try:
            tag_result = subprocess.run([
                'osascript', '-e', tag_script
            ], capture_output=True, text=True, timeout=60)

            entered_tags = tag_result.stdout.strip()
            tag_list = [tag.strip() for tag in entered_tags.split(',') if tag.strip()] if entered_tags else []
        except:
            tag_list = []

        # Get collection
        collection_prompt = "Enter collection name (optional):"
        if collection_names:
            collection_prompt += f"\n\nAvailable collections: {', '.join(collection_names[:10])}"

        collection_script = f'''
        tell application "System Events"
            set response to display dialog "{collection_prompt}" default answer "" with title "Select Collection"
            return text returned of response
        end tell
        '''

        try:
            collection_result = subprocess.run([
                'osascript', '-e', collection_script
            ], capture_output=True, text=True, timeout=60)

            collection_name = collection_result.stdout.strip()
        except:
            collection_name = ""

        return {
            'tags': tag_list,
            'collection': collection_name
        }

    except Exception as e:
        print(f"Error getting user input: {e}")
        return {'tags': [], 'collection': ''}


def main():
    print("Starting Linkwarden save action...", file=sys.stderr)

    try:
        # Get the save data from the argument
        arg = sys.argv[1] if len(sys.argv) > 1 else ""
        print(f"Received argument: {arg}", file=sys.stderr)

        save_data = extract_save_data_from_arg(arg)
        url = save_data['url']
        tags = save_data['tags']
        collections = save_data['collections']

        print(f"Extracted save data:", file=sys.stderr)
        print(f"  URL: {url}", file=sys.stderr)
        print(f"  Tags: {tags}", file=sys.stderr)
        print(f"  Collections: {collections}", file=sys.stderr)

        if not url:
            print("No URL provided", file=sys.stderr)
            print("Error: No URL to save")
            return

        print("Initializing Linkwarden API...", file=sys.stderr)
        # Initialize API (don't output Alfred JSON format)
        api = LinkwardenAPI(output_alfred_format=False)

        print("Getting page title...", file=sys.stderr)
        # Get page title
        title = get_page_title(url)
        print(f"Page title: {title}", file=sys.stderr)

        # Determine collection to use (use first one if multiple)
        collection_name = collections[0] if collections else ""

        print("Saving link to Linkwarden...", file=sys.stderr)
        print(f"  URL: {url}", file=sys.stderr)
        print(f"  Title: {title}", file=sys.stderr)
        print(f"  Tags: {tags}", file=sys.stderr)
        print(f"  Collection: {collection_name if collection_name else '(default)'}", file=sys.stderr)

        # Save the link with enhanced data
        try:
            result = api.create_link(
                url=url,
                name=title,
                description="",
                tags=tags,
                collection_name=collection_name
            )

            # Build and show notification
            if tags or collection_name:
                details = []
                if collection_name:
                    # Check if there was an API bug
                    saved_collection = result.get('response', {}).get('collection', {})
                    saved_collection_name = saved_collection.get('name', '')
                    if saved_collection_name.lower() != collection_name.lower():
                        details.append(f"@{saved_collection_name} (manual move to @{collection_name} needed)")
                    else:
                        details.append(f"@{collection_name}")
                if tags:
                    details.append(f"#{', #'.join(tags)}")
                notification_msg = f"{title}\n{' • '.join(details)}"
            else:
                notification_msg = f"{title}\nSaved to default collection"

            # Output notification text for Alfred's built-in notification
            print(notification_msg)
            print(f"Successfully saved: {title}", file=sys.stderr)
            print(f"   URL: {url}", file=sys.stderr)
            if tags:
                print(f"   Tags: {', '.join(tags)}", file=sys.stderr)
            if collection_name:
                saved_collection_name = result.get('response', {}).get('collection', {}).get('name', 'Unknown')
                if saved_collection_name.lower() != collection_name.lower():
                    print(f"   Collection: {saved_collection_name} (should be {collection_name})", file=sys.stderr)
                else:
                    print(f"   Collection: {collection_name}", file=sys.stderr)

        except Exception as e:
            error_msg = f"Failed to save link: {str(e)}"
            print(f"{error_msg}", file=sys.stderr)

            # Handle specific error cases and provide appropriate notifications
            if "409" in str(e) and "Link already exists" in str(e):
                # Link already exists - show informative notification
                print(f"Link Already Exists\n{title}\nThis URL is already saved in Linkwarden")
                print("Link already exists in your Linkwarden collection", file=sys.stderr)
            elif "401" in str(e):
                print("Authentication Error\nInvalid API token\nCheck workflow configuration")
                print("Check your API token in workflow configuration", file=sys.stderr)
            elif "404" in str(e):
                print("Connection Error\nAPI endpoint not found\nCheck workflow configuration")
                print("Check your API URL in workflow configuration", file=sys.stderr)
            elif "400" in str(e):
                print("Invalid Request\nBad URL format\nPlease check the URL and try again")
                print("Check URL format and try again", file=sys.stderr)
            else:
                print(f"Save Failed\n{title}\n{error_msg}")
                print("Unexpected error occurred", file=sys.stderr)

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"{error_msg}", file=sys.stderr)

        # Output error notification for Alfred's built-in notification system
        print(f"Unexpected Error\nLinkwarden save failed\n{error_msg}")

        import traceback
        print("Full traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()