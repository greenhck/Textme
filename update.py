import os
import json
from datetime import datetime
import pytz
from google import genai
# केवल APIError को इंपोर्ट करें जो अधिकांश समस्याओं को कवर करता है।
from google.genai.errors import APIError

# --- Configuration ---
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    print("WARNING: GEMINI_API_KEY secret not found! Exiting.")
    exit(1)

# Client Initialization
try:
    # Key is automatically picked up from the Environment Variable
    client = genai.Client()
    print("✅ Gemini API Client initialized.")
except Exception as e:
    print(f"❌ Initialization Error: Could not initialize Gemini client. Details: {e}")
    exit(1)
    
MODEL_NAME = 'gemini-2.5-flash-lite'

def get_bulk_aura_change_prompt(celebrity_names):
    """Generates the bulk Aura Score change prompt."""
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
    
    # response_text को try ब्लॉक के बाहर खाली स्ट्रिंग से इनिशियलाइज़ करें
    # ताकि JSONDecodeError के मामले में यह कोई बकवास पार्स करने की कोशिश न करे।
    response_text = ""
    
    try:
        # 1. Read the existing data (No Change)
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
        
        # --- FINAL BRUTE-FORCE API CALL BLOCK START ---
        
        try:
            # API Call Syntax
            response = client.models.generate_content(
                model=MODEL_NAME, 
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
        
        # CATCH ALL EXCEPTIONS (APIError catches Google service issues)
        except APIError as e:
            print(f"\n🚨 CRITICAL GOOGLE API ERROR DETECTED (Handled API Error)!")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Details: {e}")
            exit(1)
        
        # CATCH ALL UNHANDLED EXCEPTIONS (This is the block we NEED to hit)
        except Exception as e:
            # If we land here, the key is invalid or the connection is blocked.
            print(f"\n❌ CRITICAL UNHANDLED CONNECTION/AUTHENTICATION ERROR DETECTED!")
            print(f"The API call failed at a low level, suggesting an issue with the **API Key** or **Network Access**.")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Details: {e}")
            exit(1)
            
        # --- FINAL BRUTE-FORCE API CALL BLOCK END ---

        # 3. Check for empty or blocked response
        if not response.text or not response.candidates[0].content.parts[0].text:
             response_text = "ERROR: Empty response received from Gemini API. Check for Safety/Policy block."
             raise ValueError(response_text)

        response_text = response.text.strip()
        aura_changes = json.loads(response_text) 
        
        print("Successfully received and parsed bulk aura changes.")

        # 4. Loop through celebrities and update their data (No Change)
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

        # 5. Update the timestamp to IST (No Change)
        ist = pytz.timezone('Asia/Kolkata')
        data['last_updated'] = datetime.now(ist).strftime('%d-%m-%Y %H:%M:%S IST')

        # 6. Write back the updated data (No Change)
        with open('data.json', 'w') as f:
            json.dump(data, f, indent=4)
            
        print("Aura Market data updated successfully.")

    except (json.JSONDecodeError, ValueError) as e:
        # If response_text is empty or contains an API key error message, it will land here.
        # This is the old error path we are trying to avoid.
        print(f"CRITICAL ERROR: Failed to process API response (JSON/Data Error). Raw response:\n---START RAW RESPONSE---\n{response_text}\n---END RAW RESPONSE---\nError: {e}")
        exit(1)
    except Exception as e:
        # Catches file read/write errors or logic errors
        print(f"A critical error occurred (File/Logic Error): {e}")
        exit(1)

if __name__ == '__main__':
    update_aura_scores()
