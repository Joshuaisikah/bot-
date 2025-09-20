import requests
import re
import time

# Configuration
VOTE_URL = "https://poll.fm/vote"
INITIAL_PARAMS = {
    "va": "35",
    "pt": "0",
    "r": "0",
    "p": "15955819",
    "a": "70603207,",  # Cascade vote
    "o": "",
    "t": "22473",
    "token": "60b31bf29b69cdfddf0fc71da89909d9",
    "pz": "279"
}
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Alt-Used": "poll.fm",
    "Connection": "keep-alive",
    "Cookie": "PD_REQ_AUTH=30f0a664ff1fdb9545c34a4c4a7a10ee",
    "Host": "poll.fm",
    "Priority": "u=4",
    "Referer": "https://poll.fm/15955819",
    "Sec-Fetch-Dest": "iframe",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0"
}

def solve_math_captcha(math_text):
    pattern = r'(\d+)\s*\+\s*(\d+)\s*='
    match = re.search(pattern, math_text)
    if match:
        num1, num2 = int(match.group(1)), int(match.group(2))
        return str(num1 + num2)
    raise ValueError(f"Could not parse math problem: {math_text}")

def vote_for_cascade():
    session = requests.Session()
    while True:
        try:
            # Step 1: Fetch the form to extract dynamic CAPTCHA
            print("Fetching form...")
            response = session.get(VOTE_URL, headers=HEADERS, params=INITIAL_PARAMS, timeout=10, allow_redirects=True)
            response.raise_for_status()
            
            response_text = response.text
            if response.encoding != 'utf-8' or "��" in response_text:
                response_text = response.content.decode('utf-8', errors='ignore')
            
            # Extract math problem and maths_key
            math_pattern = r'<p>(\d+\s*\+\s*\d+\s*=)\s*(?:<[^>]+>)*<input[^>]*name="answer"[^>]*>\s*(?:<[^>]+>)*<input[^>]*name="maths_key"[^>]*value="([^"]+)"'
            match = re.search(math_pattern, response_text, re.DOTALL)
            if not match:
                raise ValueError("Could not extract math problem or maths_key")
            
            math_problem, maths_key = match.group(1), match.group(2)
            answer = solve_math_captcha(math_problem)
            print(f"Extracted: {math_problem}, Answer: {answer}, maths_key: {maths_key}")
            
            # Step 2: Submit the vote with the solved CAPTCHA
            SUBMIT_PARAMS = INITIAL_PARAMS.copy()
            SUBMIT_PARAMS.update({
                "answer": answer,
                "maths_key": maths_key,
                "_pd_nonce": "1f44e32926"
            })
            
            print("Submitting vote...")
            submit_response = session.get(VOTE_URL, headers=HEADERS, params=SUBMIT_PARAMS, timeout=10, allow_redirects=True)
            submit_response.raise_for_status()
            
            submit_text = submit_response.text
            if submit_response.encoding != 'utf-8' or "��" in submit_text:
                submit_text = submit_response.content.decode('utf-8', errors='ignore')
            
            print(f"Submitted, URL: {submit_response.url}")
            print(f"Response: {submit_text[:200]}...")  # Preview response
            
            # Check for success
            if "Your vote was counted" in submit_text or submit_response.url != VOTE_URL:
                print("Vote confirmed!")
            else:
                print("No confirmation; check response.")
            
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
        except ValueError as e:
            print(f"Error: {e}")
        
        # Wait 30 seconds before next attempt
        print("Waiting 30 seconds...")
        time.sleep(1)

if __name__ == "__main__":
    vote_for_cascade()
