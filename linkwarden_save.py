#!/usr/bin/env python3
"""
Save link to Linkwarden - Alfred Script Filter (Step 1: URL Input)
Command: lws [url]
"""

import sys
import os
import re
import json
from urllib.parse import urlparse
from linkwarden_api import LinkwardenAPI, output_alfred_items, create_alfred_item


def normalize_url(url: str) -> str:
    """Normalize URL by adding https:// if no scheme is provided"""
    url = url.strip()
    if not url:
        return url

    # If it already has a scheme, return as-is
    if url.startswith(('http://', 'https://', 'ftp://')):
        return url

    # If it looks like a URL (has dots), add https://
    if '.' in url and ' ' not in url:
        return f"https://{url}"

    return url


def is_valid_url(url: str) -> bool:
    """Check if the provided string is a valid URL (with auto-normalization)"""
    try:
        normalized = normalize_url(url)
        result = urlparse(normalized)
        return all([result.scheme, result.netloc])
    except:
        return False


def extract_domain(url: str) -> str:
    """Extract domain from URL for display"""
    try:
        normalized = normalize_url(url)
        parsed = urlparse(normalized)
        return parsed.netloc
    except:
        return url


def parse_save_query(query: str) -> dict:
    """Parse save query for URL, tags (#), and collections (@)"""
    import re

    # Extract tags using # syntax
    tag_matches = re.findall(r'#(\w+)', query)

    # Extract collections using @ syntax
    collection_matches = re.findall(r'@(\w+)', query)

    # Remove # and @ patterns from query to get the URL
    clean_query = re.sub(r'#\w+', '', query)
    clean_query = re.sub(r'@\w+', '', clean_query)
    clean_query = clean_query.strip()

    # The remaining text should be the URL
    url = normalize_url(clean_query)

    return {
        'url': url,
        'tags': list(set(tag_matches)),  # Remove duplicates
        'collections': list(set(collection_matches))  # Remove duplicates
    }


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    try:
        # Step 1: Handle URL input with enhanced syntax
        if not query.strip():
            # Show help with enhanced syntax examples
            help_items = [
                create_alfred_item(
                    title="Save Link to Linkwarden",
                    subtitle="Enter URL with optional tags and collections",
                    arg="",
                    valid=False
                ),
                create_alfred_item(
                    title="Enhanced Syntax Examples",
                    subtitle="example.com #work #important @dev",
                    arg="",
                    valid=False
                ),
                create_alfred_item(
                    title="Auto HTTPS",
                    subtitle="github.com becomes https://github.com automatically",
                    arg="",
                    valid=False
                )
            ]
            output_alfred_items(help_items)
            return

        # Parse the enhanced query
        parsed = parse_save_query(query)
        url = parsed['url']
        tags = parsed['tags']
        collections = parsed['collections']

        # Check if we have a valid URL
        if is_valid_url(url):
            domain = extract_domain(url)

            # Build subtitle showing what will be saved
            subtitle_parts = [f"URL: {url}"]

            if tags:
                subtitle_parts.append(f"Tags: {', '.join(f'#{tag}' for tag in tags)}")

            if collections:
                subtitle_parts.append(f"Collections: {', '.join(f'@{col}' for col in collections)}")

            subtitle_parts.append("Press Enter to save")
            subtitle = " • ".join(subtitle_parts)

            # Create save data string to pass to action
            save_data = {
                'url': url,
                'tags': tags,
                'collections': collections
            }
            import json
            save_arg = f"save_enhanced:{json.dumps(save_data)}"

            alfred_items = [
                create_alfred_item(
                    title=f"Save: {domain}",
                    subtitle=subtitle,
                    arg=save_arg,
                    icon="icon.png"
                )
            ]
            output_alfred_items(alfred_items)

        else:
            # Input doesn't look like a URL
            alfred_items = []

            # Try to be helpful - maybe they're typing a URL
            if '.' in query:
                suggested_url = normalize_url(query)
                alfred_items.append(create_alfred_item(
                    title="Auto-fix URL?",
                    subtitle=f"Did you mean: {suggested_url}",
                    arg="",
                    valid=False
                ))

            # Show enhanced syntax examples
            alfred_items.extend([
                create_alfred_item(
                    title="Enhanced Save Syntax",
                    subtitle="example.com #work @dev (auto-adds https://)",
                    arg="",
                    valid=False
                ),
                create_alfred_item(
                    title="Multiple Tags & Collections",
                    subtitle="github.com #coding #tutorial @work @reference",
                    arg="",
                    valid=False
                ),
                create_alfred_item(
                    title="Just URL works too",
                    subtitle="https://example.com or example.com",
                    arg="",
                    valid=False
                )
            ])

            output_alfred_items(alfred_items)

    except Exception as e:
        # Handle any unexpected errors
        error_items = [create_alfred_item(
            title="Save Link Error",
            subtitle=str(e),
            arg="",
            valid=False
        )]
        output_alfred_items(error_items)


if __name__ == "__main__":
    main()