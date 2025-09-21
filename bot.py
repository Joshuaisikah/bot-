import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import re
import time
import random
import json
from bs4 import BeautifulSoup

# Configuration
POLL_ID = "15955819"
BASE_URL = "https://poll.fm"
POLL_URL = f"{BASE_URL}/{POLL_ID}"
VOTE_URL = f"{BASE_URL}/vote"
CASCADE_OPTION = "70603207"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0"
]

def get_headers(referer=None):
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Host": "poll.fm",
        "Referer": referer or POLL_URL,
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate", 
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": random.choice(USER_AGENTS)
    }

def solve_math_captcha(math_text):
    """Extract and solve math problem like '7 + 9 ='"""
    pattern = r'(\d+)\s*\+\s*(\d+)\s*='
    match = re.search(pattern, math_text)
    if match:
        num1, num2 = int(match.group(1)), int(match.group(2))
        return str(num1 + num2)
    raise ValueError(f"Could not parse math problem: {math_text}")

def extract_fresh_parameters(session, headers):
    """Extract current poll parameters from the main poll page"""
    print("Step 1: Getting fresh poll parameters...")
    
    poll_response = session.get(POLL_URL, headers=headers, timeout=15)
    poll_response.raise_for_status()
    
    soup = BeautifulSoup(poll_response.text, 'html.parser')
    
    # Find the vote button with data-vote attribute
    vote_button = soup.find('a', {'data-vote': True})
    if not vote_button:
        raise ValueError("Could not find vote button with data-vote")
    
    # Parse the JSON data from data-vote attribute
    vote_data_str = vote_button.get('data-vote', '{}')
    try:
        vote_data = json.loads(vote_data_str.replace('&quot;', '"'))
    except json.JSONDecodeError as e:
        raise ValueError(f"Could not parse vote data JSON: {e}")
    
    # Extract parameters
    fresh_params = {
        'va': '35',  # Vote action
        'pt': '0',   # Poll type
        'r': '0',    # Result
        'p': POLL_ID,
        'a': f'{CASCADE_OPTION},',  # Answer (Cascade)
        'o': '',     # Other
        't': str(vote_data.get('t', '29735')),  # Timestamp
        'token': vote_data.get('n', ''),  # Token from 'n' field
        'pz': str(vote_data.get('v', '679'))  # Poll zone from 'v' field
    }
    
    print(f"Extracted fresh parameters:")
    print(f"  t (timestamp): {fresh_params['t']}")
    print(f"  token: {fresh_params['token']}")
    print(f"  pz: {fresh_params['pz']}")
    
    return fresh_params

def vote_for_cascade():
    """Voting with fresh parameters extracted from poll page"""
    session = requests.Session()
    session.verify = False
    
    try:
        headers = get_headers()
        
        # Step 1: Get fresh parameters from poll page
        fresh_params = extract_fresh_parameters(session, headers)
        
        # Step 2: Get the math captcha form using fresh parameters
        print("Step 2: Getting math captcha with fresh parameters...")
        
        response = session.get(VOTE_URL, headers=headers, params=fresh_params, timeout=15)
        response.raise_for_status()
        
        if "math problem" not in response.text:
            print("❌ Did not get math captcha form")
            print("Response preview:")
            print(response.text[:500])
            return False
        
        print("✅ Got math captcha form with fresh parameters")
        
        # Step 3: Parse the form and solve immediately
        soup = BeautifulSoup(response.text, 'html.parser')
        form = soup.find('form', {'action': VOTE_URL})
        
        if not form:
            print("❌ Could not find form")
            return False
        
        # Extract form data (this should have the fresh parameters)
        submit_data = {}
        for input_tag in form.find_all('input'):
            name = input_tag.get('name')
            value = input_tag.get('value', '')
            if name and input_tag.get('type') not in ['submit']:
                submit_data[name] = value
        
        # Find and solve math problem
        math_p = form.find('p')
        if not math_p:
            print("❌ Could not find math problem")
            return False
        
        math_text = math_p.get_text().strip()
        answer = solve_math_captcha(math_text)
        submit_data['answer'] = answer
        
        print(f"Math problem: {math_text}")
        print(f"Answer: {answer}")
        print(f"Using fresh maths_key: {submit_data.get('maths_key', 'MISSING')}")
        
        # Step 4: Submit immediately
        print("Step 3: Submitting with fresh parameters...")
        headers['Referer'] = response.url
        
        # Disable auto-redirects to catch the 302
        final_response = session.get(VOTE_URL, headers=headers, params=submit_data, timeout=15, allow_redirects=False)
        final_response.raise_for_status()
        
        print(f"Final status: {final_response.status_code}")
        
        # Check for proper redirect
        if final_response.status_code == 302:
            location = final_response.headers.get('Location', '')
            print(f"Redirect location: {location}")
            
            if '/results' in location and 'msg=voted' in location:
                print("✅ SUCCESS: 302 redirect to results with msg=voted!")
                
                # Follow redirect to show results
                results_response = session.get(location, headers=headers, timeout=15)
                if results_response.status_code == 200:
                    soup = BeautifulSoup(results_response.text, 'html.parser')
                    print("\n=== CURRENT POLL RESULTS ===")
                    for feedback in soup.find_all('li', class_='pds-feedback-group'):
                        option_text = feedback.find('span', class_='pds-answer-text')
                        percentage = feedback.find('span', class_='pds-feedback-per')
                        votes = feedback.find('span', class_='pds-feedback-votes')
                        if option_text and percentage:
                            print(f"{option_text.get_text()}: {percentage.get_text().strip()} {votes.get_text().strip() if votes else ''}")
                    
                    total_votes = soup.find('div', class_='pds-total-votes')
                    if total_votes:
                        print(f"\n{total_votes.get_text()}")
                
                return True
            else:
                print(f"❌ Redirected to wrong location: {location}")
                return False
        else:
            print(f"❌ Unexpected status code: {final_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run continuous voting with safety measures"""
    total_successful_votes = 0
    consecutive_failures = 0
    max_consecutive_failures = 10
    
    print("🔄 Starting continuous voting mode...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            attempt_start_time = time.time()
            
            print(f"\n{'='*20} Vote #{total_successful_votes + 1} {'='*20}")
            
            if vote_for_cascade():
                total_successful_votes += 1
                consecutive_failures = 0
                print(f"✅ Total successful votes: {total_successful_votes}")
                
                # Success - wait shorter time
                wait_time = random.randint(1,5)  # 10-30 seconds between votes
                
            else:
                consecutive_failures += 1
                print(f"❌ Consecutive failures: {consecutive_failures}")
                
                # Check if we should stop due to too many failures
                if consecutive_failures >= max_consecutive_failures:
                    print(f"🛑 Stopping: {max_consecutive_failures} consecutive failures")
                    print("This usually means:")
                    print("  - Poll is closed")
                    print("  - IP/proxies are blocked") 
                    print("  - Server is down")
                    break
                
                # Failure - wait longer
                wait_time = random.randint(30, 60)  # 30-60 seconds after failure
            
            # Calculate and display timing info
            attempt_duration = time.time() - attempt_start_time
            print(f"⏱️  Attempt took {attempt_duration:.1f} seconds")
            print(f"💤 Waiting {wait_time} seconds before next attempt...")
            
            # Wait with countdown (so you can see progress)
            for remaining in range(wait_time, 0, -1):
                if remaining % 10 == 0 or remaining <= 5:
                    print(f"   {remaining} seconds remaining...")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped by user")
        print(f"📊 Final stats: {total_successful_votes} successful votes")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        print(f"📊 Final stats: {total_successful_votes} successful votes")

if __name__ == "__main__":
    main()
