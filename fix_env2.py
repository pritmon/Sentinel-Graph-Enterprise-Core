import re
with open('.env', 'r') as f:
    content = f.read()

content = re.sub(r'GOOGLE_API_KEY=.*?\n', '', content)
content += '\nGOOGLE_API_KEY="' + re.search(r'GEMINI_API_KEY="(.*?)"', content).group(1) + '"\n'

with open('.env', 'w') as f:
    f.write(content)
