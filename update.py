import os
import json
from datetime import datetime
import pytz
import google.generativeai as genai

# --- Configuration ---
# Fetch API key from GitHub Secrets
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    print("WARNING: GEMINI_API_KEY secret not found! Exiting.")
    exit()

# Configure Gemini
genai.configure(api_key=API_KEY)
MODEL_NAME = 'gemini-2.5-flash-lite'

def get_bulk_aura_change_prompt(celebrity_names):
    """
    Generates a single, powerful prompt to get data for all celebrities at once.
    """
    names_string = ", ".join(celebrity_names)
    
    # Prompt is designed to guide the model towards a single score change
    return (f"Analyze all significant positive and negative news, professional activities, "
            f"social media sentiment, and public statements for the following celebrities "
            f"over the last 24 hours: {names_string}. "
            f"Based on the overall real-world impact for EACH celebrity, generate a single numerical "
            f"value representing the change in their 'Aura Score'. For example: a major movie hit could be according to investment and movie profit, "
            f"a major public controversy could be according to who is right in their contoroversy, a minor brand deal +5, a small gaffe -3. "
            f"Provide the output as a single, valid JSON object where the keys are the celebrity names "
            f"(exactly as provided) and the values are their calculated numerical aura change. "
            f"The output MUST BE ONLY THE JSON OBJECT and nothing else.")

def update_aura_scores():
    """
    Fetches celebrity data, gets all aura changes in a single API call, and updates data.json.
    """
    data = {}
    response_text = "No response text available (Error occurred before API call)" # Initialize for robust logging
    
    try:
        # 1. Read the existing data from the file
        with open('data.json', 'r') as f:
            data = json.load(f)
            
        celebrities = data.get('celebrities', [])
        
        celebrity_names = [celeb['name'] for celeb in celebrities]
        
        if not celebrity_names:
            print("No celebrities found in data.json. Exiting.")
            return

        # 2. Make ONE single API call, enforcing JSON output
        print(f"Making a single API call for {len(celebrity_names)} celebrities...")
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = get_bulk_aura_change_prompt(celebrity_names)
        
        # KEY FIX: Use response_mime_type to guarantee a valid JSON response text
        response = model.generate_content(
            prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # 3. Parse the JSON response (Now guaranteed to be JSON)
        response_text = response.text.strip()
        
        # The response text IS the JSON object when response_mime_type is used
        aura_changes = json.loads(response_text)
        print("Successfully received and parsed bulk aura changes.")

        # 4. Loop through celebrities and update their data
        for celeb in celebrities:
            # Get the change from the parsed response. Default to 0.0 if a name is missing.
            aura_change = aura_changes.get(celeb['name'], 0.0)
            
            # Ensure the change is treated as a float
            try:
                change_value = float(aura_change)
            except ValueError:
                print(f"Warning: Non-numeric change received for {celeb['name']}: {aura_change}. Setting change to 0.0.")
                change_value = 0.0
            
            # Update scores
            celeb['previous_aura_score'] = celeb['aura_score']
            celeb['aura_score'] = round(celeb['aura_score'] + change_value, 2)
            
            # Update 7-day trend data
            trend = celeb.get('trend_7_days', [celeb['aura_score']] * 7)
            # Ensure the trend list has at most 7 elements
            trend = trend[-6:] 
            trend.append(celeb['aura_score'])
            celeb['trend_7_days'] = trend

        # 5. Update the timestamp to IST
        ist = pytz.timezone('Asia/Kolkata')
        data['last_updated'] = datetime.now(ist).strftime('%d-%m-%Y %H:%M:%S IST')

        # 6. Write back the updated data
        with open('data.json', 'w') as f:
            json.dump(data, f, indent=4)
            
        print("Aura Market data updated successfully.")

    except json.JSONDecodeError as e:
        # Detailed logging for JSON error
        print(f"CRITICAL ERROR: Failed to parse JSON response from API. The raw response was:\n---START RAW RESPONSE---\n{response_text}\n---END RAW RESPONSE---\nError: {e}")
    except Exception as e:
        # General error handling
        print(f"A critical error occurred: {e}")

if __name__ == '__main__':
    update_aura_scores()
