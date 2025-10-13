import os
import json
import google.generativeai as genai

# Configure the Gemini API with your key
# It's recommended to set this as an environment variable for security
genai.configure(api_key="YOUR_GEMINI_API_KEY") # Replace with your actual key

def get_aura_update_prompt(celebrity_name):
    """Generates the prompt for the Gemini API."""
    return f"Analyze the recent news, social media mentions, and professional activities for {celebrity_name}. Based on this, provide a numerical sentiment score between -10 and 10, where -10 is extremely negative, 0 is neutral, and 10 is extremely positive. The output should be just the number."

def update_aura_scores():
    """Fetches celebrity data, gets updates from Gemini, and updates the data.json file."""
    try:
        with open('data.json', 'r+') as f:
            celebrities = json.load(f)

            for celebrity in celebrities:
                prompt = get_aura_update_prompt(celebrity['name'])
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                
                try:
                    sentiment_score = float(response.text)
                    
                    # Update previous aura score and calculate the new one
                    celebrity['previous_aura_score'] = celebrity['aura_score']
                    
                    # More complex logic can be added here
                    new_aura_score = celebrity['aura_score'] + (sentiment_score * 0.1) # The multiplier can be adjusted
                    celebrity['aura_score'] = round(new_aura_score, 2)

                except ValueError:
                    print(f"Could not parse sentiment score for {celebrity['name']}. Received: {response.text}")

            f.seek(0)
            json.dump(celebrities, f, indent=4)
            f.truncate()

        print("Aura scores updated successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    update_aura_scores()
