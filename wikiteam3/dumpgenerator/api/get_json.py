import requests


def get_JSON(request: requests.Response):
    """Strip Unicode BOM"""
    if request.text.startswith("\ufeff"):
        request.encoding = "utf-8-sig"
    # request.encoding = request.apparent_encoding
    try:
        return request.json()
    except Exception:
        # Maybe an older API version which did not return correct JSON
        print("Error: Could not parse JSON")
        return {}
