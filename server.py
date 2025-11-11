from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
import json
import requests
import re
import time
import os
from urllib.parse import urlparse, quote
from requests.adapters import HTTPAdapter, Retry

class DualStackServer(HTTPServer):
    address_family = socket.AF_INET6
    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()

def extract_domains_and_names(messages):
    domain_regex = r'\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b'
    domains = set()
    names = set()

    for msg in messages:
        if msg["role"] == "user":
            content = msg.get("content", "")

            # Extract domains
            found_domains = re.findall(domain_regex, content)
            domains.update(found_domains)

            # Extract name from From header with various formats
            if content.lower().startswith("from:"):
                # Match patterns like:
                # From: John Doe <john@example.com>
                # From: <noreply@example.com>
                # From: Company Name <support@example.com>
                match = re.search(r'From:\s*(?:([^<]+?)\s*<|<([^>]+)>)', content, re.IGNORECASE)
                if match:
                    name = match.group(1) or match.group(2)
                    if name:
                        # Clean up the name (remove extra spaces, quotes, etc)
                        name = name.strip().strip('"\'')
                        names.add(name)

    # Convert domains set to list and take only first 3
    domains_list = list(domains)[:3]
    return domains_list, list(names)

def fetch_leta_search(query):
    url = f"https://leta.mullvad.net/search/__data.json?q={query}&engine=brave"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            break  # Success, exit retry loop
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt == max_retries - 1:  # Last attempt
                return [{"title": "Error", "link": "", "snippet": "Search service timeout after {} attempts".format(max_retries)}]
            print("Search attempt {} failed: {}. Retrying...".format(attempt + 1, e))
            time.sleep(1 * (attempt + 1))  # Exponential backoff
        except Exception as e:
            return [{"title": "Error", "link": "", "snippet": str(e)}]

    try:
        search_data = None
        if 'nodes' in data:
            for node in data['nodes']:
                if node and isinstance(node, dict) and 'type' in node and node['type'] == 'data':
                    if 'data' in node and isinstance(node['data'], list):
                        # Look for a list that has elements with 'success', 'items', etc.
                        if any(isinstance(item, dict) and 'success' in item for item in node['data']):
                            search_data = node['data']
                            break
        
        if not search_data:
            return "Could not locate search results in the JSON data"
        
        # Find the indices for results
        result_indices = None
        for i, item in enumerate(search_data):
            if isinstance(item, list) and len(item) > 0 and all(isinstance(x, int) for x in item):
                # This is likely the list of indices
                result_indices = item
                break
        
        if not result_indices:
            return "Could not locate result indices in the search data"
        
        # Initialize a list to store results
        results = []
        
        # Extract only the first two results
        for i in range(min(2, len(result_indices))):
            index = result_indices[i]
            
            # Find the result data structure at this index
            if index < len(search_data) and isinstance(search_data[index], dict):
                result_data = search_data[index]
                
                # Extract link, snippet, title if they exist
                if 'link' in result_data and result_data['link'] < len(search_data):
                    link = search_data[result_data['link']]
                else:
                    link = "Link not found"
                    
                if 'snippet' in result_data and result_data['snippet'] < len(search_data):
                    snippet = search_data[result_data['snippet']]
                else:
                    snippet = "Snippet not found"
                    
                if 'title' in result_data and result_data['title'] < len(search_data):
                    title = search_data[result_data['title']]
                else:
                    title = "Title not found"
                
                result = {
                    'link': link,
                    'title': title,
                    'snippet': snippet
                }
                
                results.append(result)
        
        return results

    except Exception as e:
        return [{"title": "Error", "link": "", "snippet": str(e)}]


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        ollama_api = os.environ.get('OLLAMA_API', 'http://127.0.0.1:11434')
        url = f"{ollama_api}/v1/chat/completions"

        s = requests.Session()

        retries = Retry(total=10,
                backoff_factor=2,
                status_forcelist=[ 500, 502, 503, 504 ],
                raise_on_status=False)

        s.mount('http://', HTTPAdapter(max_retries=retries))

        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body)

            if "messages" not in data or not data["messages"]:
                raise ValueError("Missing messages in request.")

            domains, names = extract_domains_and_names(data["messages"])
            search_queries = domains + names
            search_results = []

            for query in search_queries:
                results = fetch_leta_search(query)
                for res in results:
                    search_results.append(f"{res['title']}\n{res['link']}\n{res['snippet']}")

            if search_results:
                system_message = {
                    "role": "system",
                    "content": "Web context:\n" + "\n\n".join(search_results)
                }
                data["messages"].insert(1, system_message)  # insert after initial system prompt

            headers = dict(self.headers)

            # Retry logic for the main request
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = s.post(
                        f"{ollama_api}/v1/chat/completions",
                        json=data,
                        headers=headers,
                        timeout=45
                    )
                    break  # Success, exit retry loop
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    if attempt == max_retries - 1:  # Last attempt
                        raise e
                    print("Attempt {} failed with timeout/connection error: {}. Retrying...".format(attempt + 1, e))
                    # Optional: add a brief delay between retries
                    import time
                    time.sleep(1 * (attempt + 1))  # Exponential backoff

            content = response.content
            self.send_response(response.status_code)
            self.send_header('Content-Length', len(content))
            for header, value in response.headers.items():
                if header.lower() not in ['transfer-encoding', 'content-length']:
                    self.send_header(header, value)
            self.end_headers()
            self.wfile.write(content)

        except Exception as e:
            print(f"Exception occurred: {e}")  # Print the error message
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = json.dumps({'error': str(e)})
            self.wfile.write(error_response.encode())


def run_server(port=8080):
    server_address = ('::', port)
    httpd = DualStackServer(server_address, RequestHandler)
    print(f'Server running on:: [IPv6] http://[::]:{port} and [IPv4] http://0.0.0.0:{port}')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
