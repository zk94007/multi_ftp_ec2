#!/usr/bin/python3
#-*- coding: utf-8 -*-

import os
import sys
import time
import logging
import boto3
import pymysql
import magic
import requests

from botocore.exceptions import ClientError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, LoggingEventHandler, FileCreatedEvent
from dotenv import load_dotenv, find_dotenv
from datetime import datetime

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

class CreatedHandler(FileSystemEventHandler):
    def on_created(self, event):
        # If file is uploaded
        if (isinstance(event, FileCreatedEvent)):
            size = 0
            while True:
                time.sleep(3)
                newsize = os.stat(event.src_path).st_size
                print(size)
                print(newsize)
                if (size == newsize):
                    # Parse ftp user and file name
                    file_name, file_extension = os.path.splitext(event.src_path)
                    camera_name = event.src_path.replace(os.getenv("WATCH_DIRECTORY"), '').split('/')[0]
                    camera_id = camera_name.replace('USR_YTUZRXGOAC_', '')
                    s3_object = '{}_{}{}'.format(camera_id, int(datetime.now().timestamp() * 1000), file_extension)
                    mime = magic.Magic(mime=True)
                    content_type = mime.from_file(event.src_path)

                    try:
                        # Upload file to S3 bucket
                        s3.upload_file(
                            event.src_path,
                            os.getenv("AWS_S3_BUCKET_NAME"),
                            s3_object,
                            ExtraArgs={
                                'ACL': 'public-read',
                                'ContentType': content_type
                            }
                        )
                        logging.info('Successfully uploaded to AWS S3 Bucket')

                        # Run AI module to recognize
                        processedtime = datetime.now()
                        output = plate_recognizer_api('https://{}.s3.amazonaws.com/{}'.format(os.getenv("AWS_S3_BUCKET_NAME"), s3_object))
                        logging.info('Successfully launched recogintion module')

                        # Execute the SQL command
                        query='INSERT INTO LPRecStatus(\
                            PictureID, \
                            Plate, \
                            RecoginitionStatus, \
                            RecoginitionPercentage, \
                            CarPosition, \
                            ProcessedDate, \
                            ProcessedTime, \
                            CreationTime, \
                            CameraId, \
                            CameraCode) VALUES \
                            ("{}", "{}", {}, 0, "", "{}", "{}", "{}", "{}", "{}")'.format(s3_object, output[2], output[0]=="True",
                            processedtime,
                            processedtime,
                            datetime.now(),
                            camera_id,
                            camera_id
                            )
                        logging.info('SQL Query: {}'.format(query))
                        conn.execute(query)
                        db.commit()
                        logging.info('Successfully updated database record')
                    except:
                        logging.error(sys.exc_info()[0])
                        exit()
                    break
                size = newsize

if __name__ == "__main__":
    # load .env file
    load_dotenv(find_dotenv())

    # Configure logging
    logging.basicConfig(filename=os.getenv("LOG_FILENAME"),
                        level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

    # setup db connection
    try:
        db = pymysql.connect(
            os.getenv("DB_HOST"), # Database Host Name
            # "imagerecdb.c0mcsz5z1xgj.us-east-1.rds.amazonaws.com",
            os.getenv("DB_USERNAME"), # Database User Name
            # "iradmin",
            os.getenv("DB_PASSWORD"), # Datbase User Password
            # "7Q1TnETGj1ZH7fkOtv3t",
            os.getenv("DB_NAME") # Database Name
        )
        logging.info('Connected to Database')
    except pymysql.Error as e:
        logging.error(e)
        exit()

    # setup cursor for db
    conn = db.cursor()

    # setup s3 client
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET_KEY"))
        logging.info('AWS Client is created')
    except:
        logging.error('Can\'t initialize AWS Client')
        exit()

    # Setup watchdog Observer
    observer = Observer()

    # Define CreatedHandler and LoggingHandler
    created_handler = CreatedHandler()
    logging_handler = LoggingEventHandler()

    # Setup handler for the specific directory changes
    observer.schedule(created_handler, os.getenv("WATCH_DIRECTORY"), recursive=True)
    observer.schedule(logging_handler, os.getenv("WATCH_DIRECTORY"), recursive=True)

    # Start watching
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        db.close()
    observer.join()
