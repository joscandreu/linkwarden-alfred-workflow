#!/usr/bin/env python3
"""
Linkwarden Alfred Workflow - Search Module

Provides comprehensive search functionality for Linkwarden links with advanced filtering.

Features:
- Universal search across links, tags, collections, and content
- Enhanced syntax: #tag @collection for intuitive filtering
- Legacy syntax support: tag:name collection:name
- Visual feedback for matched filters
- Multiple tag and collection filtering

Command: lw [query with #tags @collections]

Examples:
- lw python tutorial
- lw #coding @work python
- lw tag:work collection:reference (legacy)

Author: joscandreu
"""

import sys
import os
from linkwarden_api import LinkwardenAPI, output_alfred_items, create_alfred_item, truncate_text, parse_search_query


def format_link_item(link: dict, search_filters: dict = None) -> dict:
    """Format a link as an Alfred item"""
    title = link.get('name', 'Untitled')
    if not title or title.strip() == '':
        title = truncate_text(link.get('url', 'Unknown URL'), 60)

    # Build subtitle with collection and tags info
    subtitle_parts = []

    # Add URL (truncated)
    url = link.get('url', '')
    if url:
        subtitle_parts.append(truncate_text(url, 40))

    # Add collection info (highlight if it matches search)
    collection = link.get('collection', {})
    if collection and collection.get('name'):
        collection_name = collection['name']
        collection_icon = ""

        # Highlight if this collection was searched for
        if search_filters and search_filters.get('collections'):
            if collection_name.lower() in [c.lower() for c in search_filters['collections']]:
                collection_icon = ""

        subtitle_parts.append(f"{collection_name}")

    # Add tags (highlight matching ones)
    tags = link.get('tags', [])
    if tags:
        tag_names = [tag.get('name', '') for tag in tags if tag.get('name')]
        if tag_names:
            # Highlight matching tags
            highlighted_tags = []
            search_tag_names = []
            if search_filters and search_filters.get('tags'):
                search_tag_names = [t.lower() for t in search_filters['tags']]

            for tag_name in tag_names[:3]:  # Show max 3 tags
                if tag_name.lower() in search_tag_names:
                    highlighted_tags.append(f"#{tag_name}")  # Highlight matches
                else:
                    highlighted_tags.append(tag_name)

            tags_str = ', '.join(highlighted_tags)
            if len(tag_names) > 3:
                tags_str += f' (+{len(tag_names) - 3} more)'
            subtitle_parts.append(f"{tags_str}")

    subtitle = ' • '.join(subtitle_parts)

    return create_alfred_item(
        title=title,
        subtitle=subtitle,
        arg=url,
        icon="icon.png"
    )


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else ""

    try:
        api = LinkwardenAPI()

        # Parse the search query for special filters
        parsed = parse_search_query(query)
        search_query = parsed['query']
        tag_filters = parsed['tags']
        collection_filters = parsed['collections']

        # Build search parameters
        collection_ids = []
        tag_ids = []

        # Find collection IDs for all collection filters
        if collection_filters:
            collections = api.get_collections()
            for collection_name in collection_filters:
                for collection in collections:
                    if collection.get('name', '').lower() == collection_name.lower():
                        collection_ids.append(str(collection.get('id')))
                        break

        # Find tag IDs for all tag filters
        if tag_filters:
            tags = api.get_tags()
            for tag_name in tag_filters:
                for tag in tags:
                    if tag.get('name', '').lower() == tag_name.lower():
                        tag_ids.append(str(tag.get('id')))
                        break

        # Search links with enhanced filtering
        links = api.search_links(
            query=search_query,
            collection_ids=collection_ids,
            tag_ids=tag_ids,
            limit=20
        )

        if not links:
            # Show help message when no results
            help_items = []

            if query.strip() == "":
                help_items.append(create_alfred_item(
                    title="Search Linkwarden",
                    subtitle="Type to search your links by title, content, tags, or URL",
                    arg="",
                    valid=False
                ))
                help_items.append(create_alfred_item(
                    title="Enhanced Search Syntax",
                    subtitle="Use #tag @collection or mix: 'javascript #tutorial @work'",
                    arg="",
                    valid=False
                ))
                help_items.append(create_alfred_item(
                    title="Examples",
                    subtitle="#work #important @dev python | tag:work collection:reading",
                    arg="",
                    valid=False
                ))
            else:
                help_items.append(create_alfred_item(
                    title="No results found",
                    subtitle=f"No links found for '{query}'",
                    arg="",
                    valid=False
                ))

            output_alfred_items(help_items)
            return

        # Format links for Alfred
        alfred_items = [format_link_item(link, parsed) for link in links]

        # Add search tips if there are results but user might want to refine
        if len(alfred_items) == 20:  # Max results reached
            alfred_items.append(create_alfred_item(
                title="More results available...",
                subtitle="Refine your search to see more specific results",
                arg="",
                valid=False
            ))

        output_alfred_items(alfred_items)

    except Exception as e:
        # Handle any unexpected errors
        error_items = [create_alfred_item(
            title="Search Error",
            subtitle=str(e),
            arg="",
            valid=False
        )]
        output_alfred_items(error_items)


if __name__ == "__main__":
    main()