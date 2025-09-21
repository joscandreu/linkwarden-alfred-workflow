#!/usr/bin/env python3
"""
Linkwarden Alfred Workflow - Core API Module

This module provides a unified interface to the Linkwarden API for the Alfred workflow.
It handles authentication, request/response processing, and implements workarounds for
known API limitations.

Key Features:
- Automatic tag and collection management
- Enhanced search with multiple filters
- Two-step save process to bypass API collection assignment bug
- Comprehensive error handling and user feedback

Author: joscandreu
License: MIT
Repository: https://github.com/joscandreu/linkwarden-alfred-workflow
"""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
import sys
from typing import Dict, List, Optional, Any
from cache_manager import get_cache


class LinkwardenAPI:
    """
    Main API client for interacting with Linkwarden instances.

    This class handles all communication with the Linkwarden API, including:
    - Authentication using Bearer tokens
    - Search operations with advanced filtering
    - Link creation with automatic tag/collection management
    - Collection and tag CRUD operations
    - Error handling and user feedback

    Args:
        output_alfred_format (bool): Whether to output errors in Alfred JSON format.
                                   Set to False for command-line scripts.
    """

    def __init__(self, output_alfred_format=True):
        """
        Initialize the API client with credentials from environment variables.

        Environment Variables Required:
        - LW_API_URL: Base URL of Linkwarden instance (e.g., https://linkwarden.example.com)
        - LW_API_TOKEN: API token from Linkwarden Settings → Access Tokens

        Optional Cache Configuration:
        - LW_CACHE_COLLECTIONS_TTL: TTL for collections cache in seconds (default: 600 = 10 minutes)
        - LW_CACHE_TAGS_TTL: TTL for tags cache in seconds (default: 600 = 10 minutes)
        - LW_CACHE_SEARCH_TTL: TTL for search results cache in seconds (default: 120 = 2 minutes)
        """
        self.api_url = os.environ.get('LW_API_URL', '').rstrip('/')
        self.api_token = os.environ.get('LW_API_TOKEN', '')
        self.output_alfred_format = output_alfred_format
        self.cache = get_cache()

        # Configure cache TTLs with environment variables or defaults
        self.cache_ttl_collections = self._get_ttl_from_env('LW_CACHE_COLLECTIONS_TTL', 600)  # 10 minutes
        self.cache_ttl_tags = self._get_ttl_from_env('LW_CACHE_TAGS_TTL', 600)  # 10 minutes
        self.cache_ttl_search = self._get_ttl_from_env('LW_CACHE_SEARCH_TTL', 120)  # 2 minutes

        # Validate required configuration
        if not self.api_url or not self.api_token:
            missing = []
            if not self.api_url:
                missing.append("LW_API_URL")
            if not self.api_token:
                missing.append("LW_API_TOKEN")

            error_msg = f"Missing: {', '.join(missing)}"
            if len(missing) == 2:
                error_msg = "Configuration needed: Open Alfred Preferences → Workflows → Linkwarden → Configure Variables"

            if self.output_alfred_format:
                self._output_error(error_msg)
            else:
                print(f"Configuration Error: {error_msg}", file=sys.stderr)
            sys.exit(1)

    def _get_ttl_from_env(self, env_var: str, default: int) -> int:
        """
        Get TTL value from environment variable with validation.

        Args:
            env_var (str): Environment variable name
            default (int): Default TTL value in seconds

        Returns:
            int: TTL value in seconds
        """
        try:
            value = os.environ.get(env_var)
            if value is None:
                return default

            ttl = int(value)

            # Validate TTL range (minimum 30 seconds, maximum 24 hours)
            if ttl < 30:
                print(f"{env_var}={ttl} is too low, using minimum of 30 seconds", file=sys.stderr)
                return 30
            elif ttl > 86400:  # 24 hours
                print(f"{env_var}={ttl} is too high, using maximum of 24 hours", file=sys.stderr)
                return 86400

            print(f"Cache TTL configured: {env_var}={ttl}s ({ttl//60}m)", file=sys.stderr)
            return ttl

        except ValueError:
            print(f"Invalid {env_var}='{value}', using default {default}s", file=sys.stderr)
            return default

    def get_cache_config(self) -> Dict[str, Any]:
        """
        Get current cache configuration.

        Returns:
            Dict with cache TTL settings and other configuration
        """
        return {
            'collections_ttl': self.cache_ttl_collections,
            'tags_ttl': self.cache_ttl_tags,
            'search_ttl': self.cache_ttl_search,
            'collections_ttl_minutes': self.cache_ttl_collections // 60,
            'tags_ttl_minutes': self.cache_ttl_tags // 60,
            'search_ttl_minutes': self.cache_ttl_search // 60,
            'api_url': self.api_url
        }

    def _make_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """
        Make authenticated HTTP request to Linkwarden API.

        Args:
            endpoint (str): API endpoint path (e.g., '/links', '/collections')
            method (str): HTTP method ('GET', 'POST', 'PUT', 'PATCH')
            data (Optional[Dict]): Request body data for POST/PUT/PATCH requests

        Returns:
            Dict: JSON response from the API

        Raises:
            SystemExit: On authentication or connection errors
        """
        url = f"{self.api_url}/api/v1{endpoint}"

        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Linkwarden-Alfred-Workflow/1.0 (joscandreu)'
        }

        try:
            if method == 'GET':
                req = urllib.request.Request(url, headers=headers)
            else:  # POST, PUT, PATCH
                json_data = json.dumps(data).encode('utf-8') if data else b''
                print(f"API Request: {method} {url}", file=sys.stderr)
                print(f"Request data: {json.dumps(data, indent=2)}", file=sys.stderr)
                req = urllib.request.Request(url, data=json_data, headers=headers)
                req.get_method = lambda: method

            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                print(f"API Response: {json.dumps(response_data, indent=2)}", file=sys.stderr)
                return response_data

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}: {e.reason}"
            try:
                # Try to get more detailed error information
                error_body = e.read().decode('utf-8')
                if error_body:
                    error_msg += f" - {error_body}"
            except:
                pass

            if e.code == 401:
                error_msg = "Invalid API token. Please check LW_API_TOKEN in workflow variables."
            elif e.code == 404:
                error_msg = "API endpoint not found. Please check LW_API_URL in workflow variables."
            elif e.code == 409:
                error_msg = f"Conflict: {error_msg}. Link may already exist."
            elif e.code == 400:
                error_msg = f"Bad request: {error_msg}. Check the data being sent to the API."

            if self.output_alfred_format:
                self._output_error(error_msg)
                sys.exit(1)
            else:
                print(f"API Error: {error_msg}", file=sys.stderr)
                # Raise exception instead of sys.exit() for save action to handle
                raise Exception(f"HTTP {e.code}: {e.reason} - {error_body if 'error_body' in locals() else error_msg}")
        except urllib.error.URLError as e:
            error_msg = f"Connection error: {e.reason}"
            if self.output_alfred_format:
                self._output_error(error_msg)
                sys.exit(1)
            else:
                print(f"{error_msg}", file=sys.stderr)
                raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            if self.output_alfred_format:
                self._output_error(error_msg)
                sys.exit(1)
            else:
                print(f"{error_msg}", file=sys.stderr)
                raise Exception(error_msg)

    def search_links(self, query: str = "", collection_ids: List[str] = None,
                    tag_ids: List[str] = None, collection_id: Optional[str] = None,
                    tag_id: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Search links with various filters including multiple tags and collections"""
        if collection_ids is None:
            collection_ids = []
        if tag_ids is None:
            tag_ids = []

        # Add backward compatibility
        if collection_id:
            collection_ids.append(collection_id)
        if tag_id:
            tag_ids.append(tag_id)

        # Remove duplicates
        collection_ids = list(set(collection_ids))
        tag_ids = list(set(tag_ids))

        # For multiple filters, we'll need to make separate requests and combine results
        # since the API may not support multiple collection/tag IDs directly
        all_links = []

        if collection_ids or tag_ids:
            # If we have specific filters, search with each combination
            search_combinations = []

            if collection_ids and tag_ids:
                # Combine each collection with each tag
                for col_id in collection_ids:
                    for tag_id in tag_ids:
                        search_combinations.append({'collection': col_id, 'tag': tag_id})
            elif collection_ids:
                # Just collections
                for col_id in collection_ids:
                    search_combinations.append({'collection': col_id, 'tag': None})
            elif tag_ids:
                # Just tags
                for tag_id in tag_ids:
                    search_combinations.append({'collection': None, 'tag': tag_id})

            seen_links = set()
            for combo in search_combinations:
                params = {}

                if query:
                    params['searchQueryString'] = query
                    params['searchByName'] = 'true'
                    params['searchByUrl'] = 'true'
                    params['searchByDescription'] = 'true'
                    params['searchByTextContent'] = 'true'
                    params['searchByTags'] = 'true'

                if combo['collection']:
                    params['collectionId'] = combo['collection']
                if combo['tag']:
                    params['tagId'] = combo['tag']

                params['sort'] = 'createdAt'
                params['cursor'] = '0'

                query_string = urllib.parse.urlencode(params)
                endpoint = f"/links?{query_string}"

                try:
                    response = self._make_request(endpoint)
                    links = response.get('response', [])

                    # Add unique links
                    for link in links:
                        link_id = link.get('id')
                        if link_id and link_id not in seen_links:
                            seen_links.add(link_id)
                            all_links.append(link)
                except Exception:
                    continue  # Skip failed requests

        else:
            # No specific filters, do a general search
            params = {}

            if query:
                params['searchQueryString'] = query
                params['searchByName'] = 'true'
                params['searchByUrl'] = 'true'
                params['searchByDescription'] = 'true'
                params['searchByTextContent'] = 'true'
                params['searchByTags'] = 'true'

            params['sort'] = 'createdAt'
            params['cursor'] = '0'

            query_string = urllib.parse.urlencode(params)
            endpoint = f"/links?{query_string}"

            response = self._make_request(endpoint)
            all_links = response.get('response', [])

        return all_links[:limit]

    def get_collections(self) -> List[Dict]:
        """Get all collections with caching support"""
        cache_key = f"collections_{self.api_url}_{hash(self.api_token) % 10000}"

        # Try to get from cache first
        cached_collections, cache_hit = self.cache.get(cache_key)
        if cache_hit:
            print(f"Collections cache HIT ({len(cached_collections)} collections)", file=sys.stderr)
            return cached_collections

        print(f"Collections cache MISS - fetching from API", file=sys.stderr)

        # Not in cache, fetch from API
        response = self._make_request('/collections')
        collections = response.get('response', [])

        # Cache the result using configured TTL
        if collections:
            self.cache.set(cache_key, collections, ttl_seconds=self.cache_ttl_collections)
            ttl_minutes = self.cache_ttl_collections // 60
            print(f"Cached {len(collections)} collections for {ttl_minutes}m ({self.cache_ttl_collections}s)", file=sys.stderr)

        return collections

    def get_links_by_collection(self, collection_id: str, limit: int = 20) -> List[Dict]:
        """Get links within a specific collection"""
        return self.search_links(collection_id=collection_id, limit=limit)

    def get_tags(self) -> List[Dict]:
        """Get all available tags with caching support"""
        cache_key = f"tags_{self.api_url}_{hash(self.api_token) % 10000}"

        # Try to get from cache first
        cached_tags, cache_hit = self.cache.get(cache_key)
        if cache_hit:
            print(f"Tags cache HIT ({len(cached_tags)} tags)", file=sys.stderr)
            return cached_tags

        print(f"Tags cache MISS - fetching from API", file=sys.stderr)

        # Not in cache, fetch from API
        response = self._make_request('/tags')
        tags = response.get('response', [])

        # Cache the result using configured TTL
        if tags:
            self.cache.set(cache_key, tags, ttl_seconds=self.cache_ttl_tags)
            ttl_minutes = self.cache_ttl_tags // 60
            print(f"Cached {len(tags)} tags for {ttl_minutes}m ({self.cache_ttl_tags}s)", file=sys.stderr)

        return tags

    def create_collection(self, name: str, description: str = "") -> Dict:
        """Create a new collection and invalidate cache"""
        data = {
            "name": name,
            "description": description
        }
        result = self._make_request('/collections', 'POST', data)

        # Invalidate collections cache since we added a new collection
        cache_key = f"collections_{self.api_url}_{hash(self.api_token) % 10000}"
        self.cache.delete(cache_key)
        print(f"Invalidated collections cache after creating new collection", file=sys.stderr)

        return result

    def create_link(self, url: str, name: str = "", description: str = "",
                   tags: List[str] = None, collection_name: str = "") -> Dict:
        """
        Create a new link in Linkwarden with tags and collection assignment.

        This method implements a two-step process to work around a known Linkwarden API bug
        where specifying collectionId in POST requests is ignored, causing links to be
        saved to the "Unorganized" collection instead.

        Workaround Process:
        1. Create link without collection (POST /api/v1/links)
        2. Update link to assign correct collection (PUT /api/v1/links/{id})

        Args:
            url (str): URL to save
            name (str): Link title (auto-extracted from page if empty)
            description (str): Link description
            tags (List[str]): List of tag names (will be created if they don't exist)
            collection_name (str): Collection name (will be created if it doesn't exist)

        Returns:
            Dict: API response with created/updated link data

        Note:
            Tags are converted to objects with IDs for existing tags, or name-only objects
            for new tags (which Linkwarden will automatically create).
        """
        if tags is None:
            tags = []

        # Convert tag names to tag objects that Linkwarden expects
        tag_objects = []
        if tags:
            print(f"Processing tags: {tags}", file=sys.stderr)
            try:
                # Get existing tags to find IDs, or create new ones
                existing_tags = self.get_tags()
                existing_tag_map = {tag.get('name', '').lower(): tag for tag in existing_tags}

                existing_count = 0
                new_count = 0

                for tag_name in tags:
                    tag_name_lower = tag_name.lower()
                    if tag_name_lower in existing_tag_map:
                        # Use existing tag
                        tag_objects.append(existing_tag_map[tag_name_lower])
                        existing_count += 1
                    else:
                        # Create new tag object (Linkwarden will auto-create it)
                        tag_objects.append({"name": tag_name})
                        new_count += 1

                if existing_count > 0:
                    print(f"Using {existing_count} existing tag(s)", file=sys.stderr)
                if new_count > 0:
                    print(f"Creating {new_count} new tag(s)", file=sys.stderr)

            except Exception as e:
                print(f"Error processing tags, using new tag objects: {e}", file=sys.stderr)
                # If we can't get existing tags, just create new tag objects
                tag_objects = [{"name": tag_name} for tag_name in tags]

        # Basic data structure based on Linkwarden API
        data = {
            "url": url,
            "name": name,
            "description": description,
            "tags": tag_objects
        }

        # Handle collection assignment
        if collection_name:
            print(f"Processing collection: '{collection_name}'", file=sys.stderr)
            # Try to find the collection ID first
            try:
                print(f"Fetching existing collections...", file=sys.stderr)
                collections = self.get_collections()
                print(f"Found {len(collections)} existing collections", file=sys.stderr)

                collection_id = None
                for collection in collections:
                    existing_name = collection.get('name', '')
                    print(f"   - Checking: '{existing_name}' vs '{collection_name}'", file=sys.stderr)
                    if existing_name.lower() == collection_name.lower():
                        collection_id = collection.get('id')
                        print(f"Found matching collection: '{existing_name}' (ID: {collection_id})", file=sys.stderr)
                        break

                if collection_id:
                    # Use existing collection by ID
                    data["collectionId"] = collection_id
                    print(f"Using existing collection: {collection_name} (ID: {collection_id})", file=sys.stderr)
                else:
                    # Collection doesn't exist - create new one
                    print(f"Collection '{collection_name}' not found, creating new one...", file=sys.stderr)
                    try:
                        new_collection = self.create_collection(collection_name)
                        print(f"Create collection response: {json.dumps(new_collection, indent=2)}", file=sys.stderr)

                        if new_collection and 'response' in new_collection:
                            response = new_collection['response']
                            if isinstance(response, dict) and 'id' in response:
                                collection_id = response['id']
                                data["collectionId"] = collection_id
                                print(f"Created new collection: {collection_name} (ID: {collection_id})", file=sys.stderr)
                            else:
                                print(f"Unexpected response format from collection creation", file=sys.stderr)
                                print(f"   Response: {response}", file=sys.stderr)
                        else:
                            print(f"Could not create collection '{collection_name}', using default", file=sys.stderr)
                            print(f"   Response: {new_collection}", file=sys.stderr)
                    except Exception as e:
                        print(f"Failed to create collection '{collection_name}': {e}", file=sys.stderr)
                        print("   Link will be saved to default collection", file=sys.stderr)
            except Exception as e:
                print(f"Error handling collection '{collection_name}': {e}", file=sys.stderr)
                print("   Link will be saved to default collection", file=sys.stderr)
        else:
            print(f"No collection specified, using default", file=sys.stderr)

        print(f"Final API request data:", file=sys.stderr)
        print(json.dumps(data, indent=2), file=sys.stderr)

        # WORKAROUND: Two-step approach to bypass Linkwarden API collection assignment bug
        #
        # Issue: When creating links with collectionId in POST /api/v1/links, the API ignores
        # the collectionId parameter and always saves to "Unorganized" collection.
        #
        # Solution: Create link without collection first, then update with PUT to assign collection.
        # This ensures proper collection assignment while maintaining tag functionality.
        if collection_name and data.get('collectionId'):
            intended_collection_id = data.get('collectionId')
            print(f"Using two-step approach to bypass API bug", file=sys.stderr)

            # Step 1: Create link without collection (avoids the API bug)
            data_without_collection = data.copy()
            data_without_collection.pop('collectionId', None)
            print(f"Step 1: Creating link without collection", file=sys.stderr)

            result = self._make_request('/links', 'POST', data_without_collection)

            if result and 'response' in result:
                link_id = result['response'].get('id')
                print(f"Link created (ID: {link_id})", file=sys.stderr)

                # Step 2: Use PUT with all required fields to assign collection
                #
                # The PUT endpoint requires specific fields including ownerId and collection object.
                # We extract these from the created link and build a complete update request.
                print(f"Step 2: Using PUT to assign collection {intended_collection_id}", file=sys.stderr)

                # Get the current link data and include all required fields for PUT
                saved_link = result['response']
                saved_collection = saved_link.get('collection', {})

                update_data = {
                    "id": link_id,
                    "url": saved_link.get('url'),
                    "name": saved_link.get('name'),
                    "description": saved_link.get('description', ''),
                    "tags": saved_link.get('tags', []),
                    "collectionId": intended_collection_id,
                    "collection": {
                        "id": intended_collection_id,
                        "name": collection_name,
                        "ownerId": saved_collection.get('ownerId', 1)  # Use existing ownerId
                    },
                    "ownerId": saved_collection.get('ownerId', 1)  # Add ownerId to root level
                }

                try:
                    updated_result = self._make_request(f'/links/{link_id}', 'PUT', update_data)

                    # Verify it worked
                    if updated_result and 'response' in updated_result:
                        final_collection_id = updated_result['response'].get('collection', {}).get('id')
                        if final_collection_id == intended_collection_id:
                            print(f"Collection assignment successful", file=sys.stderr)
                            return updated_result
                        else:
                            print(f"Collection update didn't stick, still in collection {final_collection_id}", file=sys.stderr)
                            return result  # Return original result
                    else:
                        print(f"Update response unexpected, returning original result", file=sys.stderr)
                        return result

                except Exception as e:
                    print(f"Collection update failed: {e}", file=sys.stderr)
                    print(f"Link saved but in wrong collection", file=sys.stderr)
                    return result  # Return original result
            else:
                print(f"Link creation failed", file=sys.stderr)
                return result
        else:
            # No collection specified, use standard approach
            print(f"Creating link without collection", file=sys.stderr)
            result = self._make_request('/links', 'POST', data)

        return result

    def _output_error(self, message: str):
        """Output error in Alfred format"""
        error_output = {
            "items": [{
                "title": "Error",
                "subtitle": message,
                "icon": {"path": "icon.png"}
            }]
        }
        print(json.dumps(error_output))


def output_alfred_items(items: List[Dict]):
    """Output items in Alfred JSON format"""
    alfred_items = {"items": items}
    print(json.dumps(alfred_items, ensure_ascii=False))


def create_alfred_item(title: str, subtitle: str, arg: str, icon: str = "icon.png",
                      autocomplete: str = None, valid: bool = True) -> Dict:
    """Create a single Alfred item"""
    item = {
        "title": title,
        "subtitle": subtitle,
        "arg": arg,
        "icon": {"path": icon},
        "valid": valid
    }

    if autocomplete:
        item["autocomplete"] = autocomplete

    return item


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def parse_search_query(query: str) -> Dict[str, Any]:
    """Parse search query for special filters like #tag, @collection, and tag:/collection:"""
    import re

    # Extract tags using # syntax
    tag_matches = re.findall(r'#(\w+)', query)

    # Extract collections using @ syntax
    collection_matches = re.findall(r'@(\w+)', query)

    # Remove # and @ patterns from query for text search
    clean_query = re.sub(r'#\w+', '', query)
    clean_query = re.sub(r'@\w+', '', clean_query)

    # Also handle legacy tag: and collection: syntax
    parts = clean_query.split()
    search_terms = []
    legacy_filters = {}

    for part in parts:
        if ':' in part and not part.startswith('http'):
            key, value = part.split(':', 1)
            if key.lower() in ['tag', 'collection', 'col']:
                if key.lower() == 'tag':
                    tag_matches.append(value)
                elif key.lower() in ['collection', 'col']:
                    collection_matches.append(value)
        else:
            search_terms.append(part)

    # Clean up the text query
    text_query = ' '.join(search_terms).strip()
    text_query = re.sub(r'\s+', ' ', text_query)  # Remove extra spaces

    return {
        'query': text_query,
        'tags': list(set(tag_matches)),  # Remove duplicates
        'collections': list(set(collection_matches)),  # Remove duplicates
        'tag': tag_matches[0] if tag_matches else '',  # For backwards compatibility
        'collection': collection_matches[0] if collection_matches else ''  # For backwards compatibility
    }