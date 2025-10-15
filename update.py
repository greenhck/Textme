import os
import json
from datetime import datetime
import pytz
from google import genai
# FIX: Only import the core APIError class, which catches almost all service errors.
from google.genai.errors import APIError

# --- Configuration ---
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    print("WARNING: GEMINI_API_KEY secret not found! Exiting.")
    exit(1)

# Client Initialization
try:
    # Client Initialization Key is automatically picked up from the Environment Variable
    client = genai.Client()
    print("✅ Gemini API Client initialized.")
except Exception as e:
    # Catches issues with the API key format or initial connection setup.
    print(f"❌ Initialization Error: Could not initialize Gemini client. Details: {e}")
    exit(1)
    
MODEL_NAME = 'gemini-2.5-flash-lite'

def get_bulk_aura_change_prompt(celebrity_names):
    """Generates the bulk Aura Score change prompt for the given celebrity names."""
    names_string = ", ".join(celebrity_names)
    return (f"Analyze all significant positive and negative news, professional activities, "
            f"social media sentiment, and public statements for the following celebrities "
            f"over the last 24 hours: {names_string}. "
            f"Based on the overall real-world impact for EACH celebrity, generate a single numerical "
            f"value representing the change in their 'Aura Score'. "
            f"Provide the output as a single, valid JSON object where the keys are the celebrity names "
            f"(exactly as provided) and the values are their calculated numerical aura change. "
            f"The output MUST BE ONLY THE JSON OBJECT and nothing else.")

def update_aura_scores():
    data = {}
    response_text = "ERROR: Raw response text not captured before API call."
    
    try:
        # 1. Read the existing data 
        with open('data.json', 'r') as f:
            data = json.load(f)
            
        celebrities = data.get('celebrities', [])
        celebrity_names = [celeb['name'] for celeb in celebrities]
        
        if not celebrity_names:
            print("No celebrities found in data.json. Exiting.")
            return

        # 2. Setup for API call
        print(f"Making a single API call for {len(celebrity_names)} celebrities...")
        prompt = get_bulk_aura_change_prompt(celebrity_names)
        
        # --- ROBUST API CALL BLOCK START ---
        
        try:
            # API Call Syntax
            response = client.models.generate_content(
                model=MODEL_NAME, 
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
        
        # 1. Catch all specific Google API exceptions (Authentication, Quota, Internal, etc.)
        except APIError as e:
            print(f"\n🚨 CRITICAL GOOGLE API ERROR DETECTED (Handled API Error)!")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Details: {e}")
            # This is where we'd see the AuthenticationError or QuotaError details
            exit(1)
        
        # 2. Catch generic exceptions (Low-level network failure, connection loss)
        except Exception as e:
            print(f"\n❌ CRITICAL UNHANDLED CONNECTION/SYSTEM ERROR DETECTED!")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Details: {e}")
            exit(1)
            
        # --- ROBUST API CALL BLOCK END ---

        # 3. Check for empty or blocked response
        if not response.text or not response.candidates[0].content.parts[0].text:
             response_text = "ERROR: Empty response received from Gemini API. Check for Safety/Policy block."
             raise ValueError(response_text)

        response_text = response.text.strip()
        aura_changes = json.loads(response_text) 
        
        print("Successfully received and parsed bulk aura changes.")

        # 4. Loop through celebrities and update their data
        for celeb in celebrities:
            aura_change = aura_changes.get(celeb['name'], 0.0)
            
            try:
                change_value = float(aura_change)
            except ValueError:
                print(f"Warning: Non-numeric change received for {celeb['name']}: {aura_change}. Setting change to 0.0.")
                change_value = 0.0
            
            celeb['previous_aura_score'] = celeb['aura_score']
            celeb['aura_score'] = round(celeb['aura_score'] + change_value, 2)
            
            trend = celeb.get('trend_7_days', [celeb['aura_score']] * 7)
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

    except (json.JSONDecodeError, ValueError) as e:
        # This catches errors if the API response is not valid JSON
        print(f"CRITICAL ERROR: Failed to process API response (JSON/Data Error). Raw response:\n---START RAW RESPONSE---\n{response_text}\n---END RAW RESPONSE---\nError: {e}")
        exit(1)
    except Exception as e:
        # Catches file read/write errors or logic errors
        print(f"A critical error occurred (File/Logic Error): {e}")
        exit(1)

if __name__ == '__main__':
    update_aura_scores()
