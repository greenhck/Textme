import os
import json
from datetime import datetime
import pytz
import google.generativeai as genai
from google.generativeai import types # Added 'types' for completeness if needed later

# --- Configuration ---
# Fetch API key from GitHub Secrets (stored in API_KEY Python variable)
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    # This ValueError is correctly raised if the secret is not found in GitHub Actions
    raise ValueError("GEMINI_API_KEY secret not found!")

# *** FIX APPLIED HERE: Using API_KEY variable instead of the environment variable name ***
genai.configure(api_key=API_KEY)

# Use the most efficient model for batch analysis to save quota and time
MODEL_NAME = 'gemini-2.5-flash-lite' 
# --- End Configuration ---


def get_bulk_aura_change_prompt(celebrity_names):
    """
    Generates a single, powerful prompt to get data for all celebrities at once.
    """
    # Create a comma-separated string of names for the prompt
    names_string = ", ".join(celebrity_names)
    
    return (f"Analyze all significant positive and negative news, professional activities, "
            f"social media sentiment, and public statements for the following celebrities "
            f"over the last 24 hours: {names_string}. "
            f"Based on the overall real-world impact for EACH celebrity, generate a single numerical "
            f"value representing the change in their 'Aura Score'. For example: a major movie hit could be according to investment and movie profit, "
            f"a major public controversy could be according to who is right in their contoroversy, a minor brand deal +5, a small gaffe -3. "
            f"Provide the output as a single, valid JSON object where the keys are the celebrity names "
            f"(exactly as provided) and the values are their calculated numerical aura change. "
            f"The output MUST BE ONLY THE JSON OBJECT and nothing else. "
            f"Example format: {{\"Shah Rukh Khan\": 15.5, \"Virat Kohli\": -20.0, ...}}")

def update_aura_scores():
    """
    Fetches celebrity data, gets all aura changes in a single API call, and updates data.json.
    """
    try:
        with open('data.json', 'r+') as f:
            data = json.load(f)
            celebrities = data.get('celebrities', [])
            
            # 1. Get a list of all celebrity names
            celebrity_names = [celeb['name'] for celeb in celebrities]
            
            if not celebrity_names:
                print("No celebrities found in data.json. Exiting.")
                return

            # 2. Make ONE single API call for all celebrities
            print(f"Making a single API call using {MODEL_NAME} for all celebrities...")
            
            # Initialize the model instance using the efficient model
            client = genai.Client()
            model = client.models.get(model=MODEL_NAME)

            prompt = get_bulk_aura_change_prompt(celebrity_names)
            response = model.generate_content(prompt)
            
            # 3. Parse the JSON response from the API
            # The response text might be enclosed in markdown ```json ... ```, so we clean it.
            cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
            aura_changes = json.loads(cleaned_response_text)
            print("Successfully received and parsed bulk aura changes.")

            # 4. Loop through celebrities and update their data
            for celeb in celebrities:
                # Get the change from the parsed response. Default to 0.0 if a name is missing.
                aura_change = aura_changes.get(celeb['name'], 0.0)
                
                # Update scores
                celeb['previous_aura_score'] = celeb['aura_score']
                # Ensure aura_change is treated as float for calculation
                celeb['aura_score'] = round(celeb['aura_score'] + float(aura_change), 2)
                
                # Update 7-day trend data
                trend = celeb.get('trend_7_days', [celeb['aura_score']] * 7)
                trend.pop(0)  # Remove the oldest data point
                trend.append(celeb['aura_score']) # Add the new data point
                celeb['trend_7_days'] = trend

            # Update the timestamp
            ist = pytz.timezone('Asia/Kolkata')
            data['last_updated'] = datetime.now(ist).strftime('%d-%m-%Y %H:%M:%S')

            # Write back the updated data
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
            
        print("Aura Market data updated successfully using a single API call.")

    except json.JSONDecodeError as e:
        # If Gemini returns garbage text instead of JSON, print the response for debugging
        print(f"CRITICAL ERROR: Failed to parse JSON response from API. Response text was:\n{response.text[:500]}...\nError: {e}")
    except Exception as e:
        print(f"A critical error occurred: {e}")

if __name__ == '__main__':
    update_aura_scores()

