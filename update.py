import os
import json
from datetime import datetime
import pytz
import google.generativeai as genai

# Fetch API key from GitHub Secrets
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("GEMINI_API_KEY secret not found!")

genai.configure(api_key=API_KEY)

def get_aura_change_prompt(celebrity_name):
    """
    Generates a precise prompt to get a numerical market-like change.
    """
    return (f"Analyze all significant positive and negative news, professional activities, "
            f"social media sentiment, and public statements related to '{celebrity_name}' "
            f"over the last 24 hours. Based on the overall real-world impact, generate a "
            f"single numerical value representing the change in their 'Aura Score'. "
            f"For example: a major hit movie could be +50. A minor brand deal +5. "
            f"A major public controversy could be -70. A small gaffe -3. "
            f"The output must be ONLY the final integer or float number. No text.")

def update_aura_scores():
    """
    Fetches celebrity data, gets aura change from Gemini, and updates the data.json file.
    """
    try:
        with open('data.json', 'r+') as f:
            data = json.load(f)
            celebrities = data.get('celebrities', [])

            model = genai.GenerativeModel('gemini-pro')

            for celeb in celebrities:
                try:
                    prompt = get_aura_change_prompt(celeb['name'])
                    response = model.generate_content(prompt)
                    
                    # Parse the numerical change from the API response
                    aura_change = float(response.text.strip())
                    
                    # Update scores
                    celeb['previous_aura_score'] = celeb['aura_score']
                    celeb['aura_score'] = round(celeb['aura_score'] + aura_change, 2)
                    
                    # Update 7-day trend data
                    trend = celeb.get('trend_7_days', [celeb['aura_score']] * 7)
                    trend.pop(0)  # Remove the oldest data point
                    trend.append(celeb['aura_score']) # Add the new data point
                    celeb['trend_7_days'] = trend

                except (ValueError, IndexError) as e:
                    print(f"Could not parse score for {celeb['name']}. Response: '{response.text}'. Error: {e}")
                    # If API fails, we keep the score unchanged for stability
                    celeb['previous_aura_score'] = celeb['aura_score']
                    trend = celeb.get('trend_7_days', [celeb['aura_score']] * 7)
                    trend.pop(0)
                    trend.append(celeb['aura_score'])
                    celeb['trend_7_days'] = trend


            # Update the timestamp
            ist = pytz.timezone('Asia/Kolkata')
            data['last_updated'] = datetime.now(ist).strftime('%d-%m-%Y %H:%M:%S')

            # Write back the updated data
            f.seek(0)
            json.dump(data, f, indent=4)
            f.truncate()
            
        print("Aura Market data updated successfully.")

    except Exception as e:
        print(f"A critical error occurred: {e}")

if __name__ == '__main__':
    update_aura_scores()
