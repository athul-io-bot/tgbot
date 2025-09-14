import base64

def encode_series_name(series_name):
    encoded = base64.urlsafe_b64encode(series_name.encode()).decode()
    return encoded.rstrip("=")

def decode_series_name(encoded_name):
    padding = '=' * (-len(encoded_name) % 4)
    return base64.urlsafe_b64decode(encoded_name + padding).decode()
