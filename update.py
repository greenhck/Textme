import os
import json
from datetime import datetime
import pytz
import google.generativeai as genai
import re 

# --- Configuration ---
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    print("CRITICAL ERROR: GEMINI_API_KEY environment variable not found! Script cannot run.")
    exit(1)

genai.configure(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash-lite' 

def get_bulk_aura_change_prompt(celebrity_names):
    """Generates the prompt for the Gemini API."""
    names_string = ", ".join(celebrity_names)
    return (f"Analyze all significant positive and negative news, professional activities, "
            f"social media sentiment, and public statements for the following celebrities "
            f"over the last 24 hours: {names_string}. "
            f"Based on the overall real-world impact for EACH celebrity, generate a single numerical "
            f"value representing the change in their 'Aura Score'. For example: a major movie hit could be +25, "
            f"a major public controversy could be -20. "
            f"Provide the output as a single, valid JSON object where the keys are the celebrity names "
            f"(exactly as provided) and the values are their calculated numerical aura change. "
            f"The output MUST BE ONLY THE JSON OBJECT and nothing else.")

def update_aura_scores():
    """Fetches data, processes scores, and writes to data.json."""
    data = {}
    response = None 
    ist = pytz.timezone('Asia/Kolkata')
    
    # 1. Read existing data
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
        print("DEBUG: Successfully loaded data.json.")
    except Exception as e:
        print(f"ERROR: Failed to read data.json: {e}")
        # If read fails, we can't proceed with celebrity logic
        data['celebrities'] = []

    celebrities = data.get('celebrities', [])
    celebrity_names = [celeb['name'] for celeb in celebrities]

    if not celebrity_names:
        print("DEBUG: No celebrities found in data.json.")
        # Even if list is empty, we update the timestamp before exiting
        data['last_updated'] = datetime.now(ist).strftime('%d-%m-%Y %H:%M:%S IST')
        write_data(data)
        return

    # 2. Make API Call and Process
    try:
        print(f"DEBUG: Making API call for {len(celebrity_names)} celebrities...")
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = get_bulk_aura_change_prompt(celebrity_names)
        
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        print(f"DEBUG: Raw API Response Received (First 100 chars): {response_text[:100]}...")

        # Robust JSON Parsing
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if not json_match:
            # CRITICAL LOG: If API doesn't return JSON, we MUST see this in the log
            raise json.JSONDecodeError("API response did not contain a valid JSON object.", response_text, 0)
            
        cleaned_response_text = json_match.group(0).strip()
        aura_changes = json.loads(cleaned_response_text)
        print("DEBUG: Successfully parsed bulk aura changes.")

        # Case-insensitive map
        aura_changes_map = {k.lower(): v for k, v in aura_changes.items()}
        
        # 3. Update scores
        for celeb in celebrities:
            aura_change = aura_changes_map.get(celeb['name'].lower(), 0.0) 
            
            change_value = float(aura_change)
            
            celeb['previous_aura_score'] = celeb['aura_score']
            celeb['aura_score'] = round(celeb['aura_score'] + change_value, 2)
            
            # Update 7-day trend
            trend = celeb.get('trend_7_days', [celeb['aura_score']] * 7)
            trend = trend[-6:] 
            trend.append(celeb['aura_score']) 
            celeb['trend_7_days'] = trend
        
        print("DEBUG: Scores updated in memory.")

    except json.JSONDecodeError as e:
        print(f"CRITICAL ERROR: Failed to parse JSON response from API. Response was: {getattr(response, 'text', 'No response text')}. Error: {e}")
        # If API update fails, we still proceed to write the file with an updated timestamp.
    except Exception as e:
        print(f"CRITICAL ERROR: API or processing failed: {e}")
        # If API update fails, we still proceed to write the file with an updated timestamp.
    
    # 4. CRITICAL FIX: Always update the timestamp and write the data
    data['last_updated'] = datetime.now(ist).strftime('%d-%m-%Y %H:%M:%S IST')
    write_data(data)

def write_data(data):
    """Helper function to write data to file."""
    try:
        with open('data.json', 'w') as f:
            json.dump(data, f, indent=4)
        print("DEBUG: Final data.json write successful.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to write data.json: {e}")


if __name__ == '__main__':
    update_aura_scores()

