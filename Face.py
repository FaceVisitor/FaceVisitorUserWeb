# Face.py

import base64
import datetime
import os
import time

import boto3
import cv2
import face_recognition
import numpy as np
import pandas as pd
import requests

import aws_rekog
import camera
from Recommend import Recommend

boto3.setup_default_session(profile_name='face')
headers = {'content-type': 'application/json'}
customerFaceCount = {}
# customerCountDataFrame = pd.DataFrame(index=['count', 'like', 'start_time', 'end_time'])
# print(customerCountDataFrame)
fail_reason = ['EXCEEDS_MAX_FACES', 'EXTREME_POSE', 'LOW_BRIGHTNESS', 'LOW_SHARPNESS', 'LOW_CONFIDENCE',
               'SMALL_BOUNDING_BOX', 'LOW_FACE_QUALITY']
session = boto3.Session(profile_name="face")
client = session.client('rekognition')
similarity = 0.4
recommend = Recommend()


class Face():
    def __init__(self):
        # Using OpenCV to capture from device 0. If you have trouble capturing
        # from a webcam, comment the line below out and use a video file
        # instead.
        self.camera = camera.VideoCamera(0)
        self.currentFace = None
        self.known_face_encodings = []
        self.known_face_names = []
        self.countDf = pd.DataFrame(data={"user_name": [], "count": [], "timestamp": []})

        # # Load sample pictures and learn how to recognize it.

        # Initialize some variables
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.process_this_frame = True
        self.face_detected = False
        self.init_customer_face()
        # 좋아요 계산
        self.cal_like()

    def __del__(self):
        del self.camera

    def init_customer_face(self):
        dirname = 'customers'
        files = os.listdir(dirname)
        for filename in files:
            name, ext = os.path.splitext(filename)
            name = name.split('_')[0]
            if ext == '.jpg' or ext == '.jpeg' or ext == '.png':
                self.known_face_names.append(name)
                pathname = os.path.join(dirname, filename)
                img = face_recognition.load_image_file(pathname)
                if len(face_recognition.face_encodings(img)) > 0:
                    face_encoding = face_recognition.face_encodings(img)[0]
                    self.known_face_encodings.append(face_encoding)

    def release(self):
        cv2.destroyAllWindows()

    def get_frame(self, is_test=False):
        # Grab a single frame of video
        num = 0
        frame = self.camera.get_frame()

        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]

        # Only process every other frame of video to save time
        if self.process_this_frame:

            # Find all the faces and face encodings in the current frame of video
            self.face_locations = face_recognition.face_locations(rgb_small_frame)
            self.face_encodings = face_recognition.face_encodings(rgb_small_frame, self.face_locations)
            self.face_names = []
            for face_encoding in self.face_encodings:
                # See if the face is a match for the known face(s)
                distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                if len(distances) > 0:
                    min_value = min(distances)
                    # tolerance: How much distance between faces to consider it a match. Lower is more strict.
                    # 0.6 is typical best performance.
                    name = "NOT CUSTOMER"
                    if min_value < similarity:
                        index = np.argmin(distances)
                        name = self.known_face_names[index]
                        # customerFaceCount[name]['count']
                        if is_test:
                            self.face_names.append("like count : {}".format(str(customerFaceCount[name]['count'])))
                        else:
                            None
                            # self.face_names.append(name)

        self.process_this_frame = not self.process_this_frame

        # Display the results
        if len(self.face_names) > 0:
            for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
                # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                # Draw a box around the face
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                # Draw a label with a name below the face
                cv2.rectangle(frame, (left, bottom), (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 2.0, (255, 255, 255), 2)
        else:
            for (top, right, bottom, left) in self.face_locations:
                # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                # Draw a box around the face
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                # # Draw a label with a name below the face
                # cv2.rectangle(frame, (left, bottom), (right, bottom), (0, 0, 255), cv2.FILLED)
                # font = cv2.FONT_HERSHEY_DUPLEX
                # cv2.putText(frame, name, (left + 6, bottom - 6), font, 2.0, (255, 255, 255), 2)

        return frame

    def get_jpg_bytes(self):
        frame = self.get_frame()
        # We are using Motion JPEG, but OpenCV defaults to capture raw images,
        # so we must encode it into JPEG in order to correctly display the
        # video stream.
        ret, jpg = cv2.imencode('.jpg', frame)
        return jpg.tobytes()

    def get_jpg_bytes_test(self):
        frame = self.get_frame(is_test=True)
        # We are using Motion JPEG, but OpenCV defaults to capture raw images,
        # so we must encode it into JPEG in order to correctly display the
        # video stream.
        ret, jpg = cv2.imencode('.jpg', frame)
        return jpg.tobytes()

    def picture_shot_for_join(self, username):
        self.camera.picture_shot(username)

    def get_64_frame(self):
        frame = self.camera.get_frame()
        return base64.b64encode(frame)

    def add_faces_to_collection(self, email, collection_id):
        count = 0
        process = []
        faceIds = []
        result = {}
        tempFrame = self.camera.get_frame()
        response = aws_rekog.add_face_to_collection(collection_id, self.get_jpg_bytes())
        if len(response['UnindexedFaces']) > 0:
            for unindexedFace in response['UnindexedFaces']:
                if len(unindexedFace['Reasons']) > 0:
                    print(unindexedFace['Reasons'], None)
        elif len(response['FaceRecords']) > 0:
            for faceRecord in response['FaceRecords']:
                faceId = faceRecord['Face']['FaceId']
                print("faceId : " + faceId)
                faceIds.append(faceId)
                faceQuality = faceRecord['FaceDetail']['Quality']
                print('  Face ID: ' + faceRecord['Face']['FaceId'])
                print(faceRecord['FaceDetail']['Quality'])
                process.append([tempFrame, faceQuality['Sharpness'], faceId])
        # 가장 정확한 얼굴로 사진 캡쳐
        # max(process, key=lambda x: x[1])

        (pictureFrame, sharpness, faeId) = max(process, key=lambda x: x[1])
        print("가장 정확한 얼굴 모양 데이터 : {}".format(max(process, key=lambda x: x[1])))
        ret, jpg = cv2.imencode('.jpg', pictureFrame)
        faceMeta = self.detect_face(jpg.tobytes())
        result['faceIds'] = faceIds
        result['faceMeta'] = faceMeta
        result['faceImageUrl'] = []
        for idx, (pictureFrame, sharpness, faceId) in enumerate(process):
            result['faceImageUrl'].append(
                self.camera.picture_shot(str(email) + "_" + str(idx) + ".jpg", pictureFrame, s3=True))

        self.init_customer_face()
        return result

    def find_face_by_byte(self, collection_id):
        faceIds = []
        response = client.search_faces_by_image(CollectionId=collection_id,
                                                # Image={'Bytes': self.get_jpg_bytes()},
                                                Image={'Bytes': self.get_jpg_bytes()},
                                                FaceMatchThreshold=70,
                                                MaxFaces=1)

        faceMatches = response['FaceMatches']
        if not faceMatches:
            print("not match face")
            return None

        for match in faceMatches:
            print('FaceId:' + match['Face']['FaceId'])
            print('Similarity: ' + "{:.2f}".format(match['Similarity']) + "%")
            faceIds.append(match['Face']['FaceId'])
            # return match['Face']['FaceId']
        return faceIds

    def detect_face(self, byte):
        response = client.detect_faces(Image={'Bytes': byte}, Attributes=['ALL'])
        for faceDetail in response['FaceDetails']:
            lowAge = faceDetail['AgeRange']['Low']
            highAge = faceDetail['AgeRange']['High']
            gender = faceDetail['Gender']['Value']
            return {'lowAge': lowAge, 'highAge': highAge, 'gender': gender}

    def now(self):
        return datetime.datetime.now().strftime("%y/%m/%d, %H:%M:%S")

    def facePreference(self):
        frame = self.camera.get_frame()
        if frame is not None:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = small_frame[:, :, ::-1]
            self.face_locations = face_recognition.face_locations(rgb_small_frame)
            self.face_encodings = face_recognition.face_encodings(rgb_small_frame, self.face_locations)
            self.face_names = []
            for face_encoding in self.face_encodings:
                distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                if len(distances) > 0:
                    min_value = min(distances)
                    if min_value < similarity:
                        index = np.argmin(distances)
                        name = self.known_face_names[index]

                        if len(self.countDf.loc[self.countDf['user_name'] == name]["user_name"].values) > 0:

                            count = self.countDf.loc[self.countDf['user_name'] == name]["count"].values[0] + 1
                            self.countDf.at[self.countDf['user_name'] == name, 'count'] = count
                            self.countDf.at[self.countDf['user_name'] == name, 'timestamp'] = self.now()

                            print("email : {}, 현재 초 : {} , 카운트 : {} ".format(name, str(time.localtime().tm_sec),
                                                                             str(count)))

                        else:
                            print("init new user")
                            newCount = pd.DataFrame(
                                data={"user_name": [name], "count": [1], "timestamp": [datetime.datetime.now()]})
                            self.countDf = self.countDf.append(newCount)
                            self.countDf = self.countDf.reset_index(drop=True)
                            # customerFaceCount[name] = {'count': 0, 'like': 0, 'timestamp': self.now()}

        self.cal_like()

    def cal_like(self):
        preferenceFace = self.countDf.loc[self.countDf['count'] >= 180]
        for email in preferenceFace["user_name"].values:
            response = requests.post('http://api.facevisitor.co.kr/api/v1/user/id',
                                     json={"email": email},
                                     headers=headers)
            if response.status_code == 200:
                user_id = response.json()
                print("user_id : {}".format(user_id))
                response = requests.get('http://api.facevisitor.co.kr/api/v1/goods/goods-by-category', headers=headers)
                if response.status_code == 200:
                    goods_id = response.json()
                    recommend.add_interaction(user_id, goods_id, "face")
                    print("user id : {}가 goods_id : {}에 관심 있습니다(점수10) ".format(user_id, goods_id))
                    self.countDf.at[self.countDf['user_name'] == email, 'count'] = 0
                else:
                    print("error")
                    self.countDf.at[self.countDf['user_name'] == email, 'count'] = 0

            else:
                self.countDf.at[self.countDf['user_name'] == email, 'count'] = 0

    def login(self):
        faceIds = self.find_face_by_byte('collection_test')


if __name__ == '__main__':
    face_recog = Face()

    while True:
        frame = face_recog.get_frame()
        # show the frame
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break

    # do a bit of cleanup
    cv2.destroyAllWindows()
