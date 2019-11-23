# pip install requests
import requests

cloud_url = "https://irlpbucket.s3.amazonaws.com/FRJL46.JPG"

# Fetching the image from s3 bucket   
def plate_recognizer_api(cloud_url):
    regions = ['cl']
    image_response  = requests.get(cloud_url)
    temp_image_path = r"temp\test_image.jpg"
    open(temp_image_path, "wb").write(image_response.content) 
    
    with open(temp_image_path,"rb") as image_to_test:
        response = requests.post(
            'https://api.platerecognizer.com/v1/plate-reader/',
            data=dict(regions=regions),  # Optional
            files=dict(upload=image_to_test),
            headers={'Authorization': 'Token 138da36d78d15b690a944730c09fc8d846f48c6a'})
    if 'detail' in response.json():
        if 'cannot identify image' in response.json()['detail']:
            print("recognition status: ", "False")
        return False, None, None, None
        
    else:
        return "True", response.json()['results'][0]['box'], response.json()['results'][0]['plate'],  response.json()['processing_time']
    
    
output = plate_recognizer_api(cloud_url)

print("recognition status: ", output[0])
print("Box co-ordinates: ", output[1])
print("License plate num: ", output[2])
print("Response time: ", output[3])