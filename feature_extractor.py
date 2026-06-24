import re
import tldextract

def extract_features(url):
    features = {}
    features['url_length'] = len(url)
    features['has_https'] = 1 if url.startswith('https') else 0
    features['dot_count'] = url.count('.')
    features['has_ip'] = 1 if re.match(
        r'\d+\.\d+\.\d+\.\d+', url) else 0
    features['special_chars'] = len(
        re.findall(r'[@_!#$%^&*<>?/|}{~:]', url))
    ext = tldextract.extract(url)
    features['subdomain_count'] = len(
        ext.subdomain.split('.')) if ext.subdomain else 0
    return features

# Test
url = "http://192.168.1.1/login/bank-secure.php"
print(extract_features(url))