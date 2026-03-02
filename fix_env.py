with open('.env', 'r') as f:
    content = f.read()
if 'GOOGLE_API_KEY' not in content:
    with open('.env', 'a') as f:
        f.write('\nGOOGLE_API_KEY="${GEMINI_API_KEY}"\n')
