#!/usr/bin/env python3
"""
Browse Linkwarden collections - Alfred Script Filter
Command: lwc [collection filter]
"""

import sys
import os
import json
from urllib.parse import quote
from linkwarden_api import LinkwardenAPI, output_alfred_items, create_alfred_item, truncate_text


def format_collection_item(collection: dict) -> dict:
    """Format a collection as an Alfred item"""
    name = collection.get('name', 'Untitled Collection')
    description = collection.get('description', '')

    # Count links in collection (if available)
    # Note: The API might not return link counts directly
    # We'll use a placeholder for now
    link_count = collection.get('_count', {}).get('links', 0)

    subtitle_parts = []

    if link_count > 0:
        subtitle_parts.append(f"{link_count} link{'s' if link_count != 1 else ''}")

    if description:
        subtitle_parts.append(truncate_text(description, 60))

    if not subtitle_parts:
        subtitle_parts.append("Browse this collection")

    subtitle = ' • '.join(subtitle_parts)

    # Create argument that will trigger a search for links in this collection
    collection_id = str(collection.get('id', ''))

    return create_alfred_item(
        title=f"{name}",
        subtitle=subtitle,
        arg="",
        autocomplete=f"browse:{collection_id}",
        valid=False,
        icon="icon.png"
    )


def format_link_item_in_collection(link: dict, collection_name: str) -> dict:
    """Format a link within a collection as an Alfred item"""
    title = link.get('name', 'Untitled')
    if not title or title.strip() == '':
        title = truncate_text(link.get('url', 'Unknown URL'), 60)

    # Build subtitle with URL and tags
    subtitle_parts = []

    # Add URL (truncated)
    url = link.get('url', '')
    if url:
        subtitle_parts.append(truncate_text(url, 50))

    # Add tags
    tags = link.get('tags', [])
    if tags:
        tag_names = [tag.get('name', '') for tag in tags if tag.get('name')]
        if tag_names:
            tags_str = ', '.join(tag_names[:3])  # Show max 3 tags
            if len(tag_names) > 3:
                tags_str += f' (+{len(tag_names) - 3} more)'
            subtitle_parts.append(f"{tags_str}")

    subtitle = ' • '.join(subtitle_parts) if subtitle_parts else f"Link in {collection_name}"

    return create_alfred_item(
        title=title,
        subtitle=subtitle,
        arg=url,
        icon="icon.png"
    )


def is_collection_query(query: str) -> tuple:
    """Check if query is requesting links from a specific collection"""
    if query.startswith('collection:'):
        collection_id = query.replace('collection:', '').strip()
        return True, collection_id
    elif query.startswith('browse:'):
        collection_id = query.replace('browse:', '').strip()
        return True, collection_id
    return False, None


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    try:
        api = LinkwardenAPI()

        # Check if we're browsing a specific collection
        is_collection_browse, collection_id = is_collection_query(query)

        if is_collection_browse and collection_id:
            # Show links within the specific collection
            try:
                # Get collection details
                collections = api.get_collections()
                collection_name = "Unknown Collection"
                for col in collections:
                    if str(col.get('id')) == collection_id:
                        collection_name = col.get('name', 'Unknown Collection')
                        break

                # Get links in this collection
                links = api.get_links_by_collection(collection_id, limit=20)

                if not links:
                    no_links_item = create_alfred_item(
                        title="No links in this collection",
                        subtitle=f"Collection '{collection_name}' is empty",
                        arg="",
                        valid=False
                    )
                    output_alfred_items([no_links_item])
                    return

                # Add a back option
                alfred_items = [
                    create_alfred_item(
                        title="← Back to Collections",
                        subtitle="Return to collection browser (or clear the search)",
                        arg="",
                        autocomplete="",
                        valid=False,
                        icon="icon.png"
                    )
                ]

                # Format links for Alfred
                link_items = [format_link_item_in_collection(link, collection_name) for link in links]
                alfred_items.extend(link_items)

                output_alfred_items(alfred_items)

            except Exception as e:
                error_items = [create_alfred_item(
                    title="Error loading collection",
                    subtitle=str(e),
                    arg="",
                    valid=False
                )]
                output_alfred_items(error_items)

        else:
            # Show collections (with optional filtering)
            collections = api.get_collections()

            if not collections:
                no_collections_item = create_alfred_item(
                    title="No collections found",
                    subtitle="Create some collections in Linkwarden first",
                    arg="",
                    valid=False
                )
                output_alfred_items([no_collections_item])
                return

            # Filter collections if query is provided
            if query.strip():
                query_lower = query.lower()
                filtered_collections = []
                for collection in collections:
                    name = collection.get('name', '').lower()
                    description = collection.get('description', '').lower()
                    if query_lower in name or query_lower in description:
                        filtered_collections.append(collection)
                collections = filtered_collections

            if not collections:
                no_match_item = create_alfred_item(
                    title="No matching collections",
                    subtitle=f"No collections match '{query}'",
                    arg="",
                    valid=False
                )
                output_alfred_items([no_match_item])
                return

            # Format collections for Alfred
            alfred_items = [format_collection_item(collection) for collection in collections]

            # Add help text if no query
            if not query.strip():
                alfred_items.insert(0, create_alfred_item(
                    title="Browse Collections",
                    subtitle="Press Enter on a collection to view its links, or type to filter collections",
                    arg="",
                    valid=False
                ))

            output_alfred_items(alfred_items)

    except Exception as e:
        # Handle any unexpected errors
        error_items = [create_alfred_item(
            title="Collections Error",
            subtitle=str(e),
            arg="",
            valid=False
        )]
        output_alfred_items(error_items)


if __name__ == "__main__":
    main()