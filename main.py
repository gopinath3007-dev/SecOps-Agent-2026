import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def run_secops_agent():
    print("--- SecOps Agent: 2.5 Flash Production Mode ---")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    # Using the confirmed 2026 model name
    model_name = "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1/models/{model_name}:generateContent?key={api_key}"
    
    # 1. Search for your YARA-L files
    root_dir = os.path.dirname(os.path.abspath(__file__))
    found_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            # We want your specific logic files, not requirements or env files
            if file.endswith(".txt") and "requirements" not in file and "env" not in file:
                found_files.append(os.path.join(root, file))

    if not found_files:
        print("No YARA-L files found in the directory.")
        return
    
    print(f"SUCCESS! Found: {[os.path.basename(f) for f in found_files]}")

    # 2. Prepare the data from your files
    full_content = ""
    for path in found_files:
        with open(path, 'r', encoding='utf-8') as f:
            full_content += f"\n--- FILE: {os.path.basename(path)} ---\n" + f.read()

    # 3. Request Analysis
    payload = {
        "contents": [{
            "parts": [{
                "text": f"You are a SecOps expert. Analyze these YARA-L rules and explain exactly what security threats they are designed to detect:\n\n{full_content}"
            }]
        }]
    }

    print(f"\nAnalyzing security logic with {model_name}...")
    
    try:
        response = requests.post(
            url, 
            headers={'Content-Type': 'application/json'}, 
            data=json.dumps(payload)
        )
        
        result = response.json()

        if response.status_code == 200:
            analysis = result['candidates'][0]['content']['parts'][0]['text']
            print("\n" + "="*50)
            print("YARA-L SECURITY ANALYSIS")
            print("="*50)
            print(analysis)
        else:
            print(f"\nError ({response.status_code}): {result.get('error', {}).get('message')}")
            
    except Exception as e:
        print(f"\nSystem Error: {e}")

if __name__ == "__main__":
    run_secops_agent()
    input("\nPress Enter to exit...")