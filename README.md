# Bird-tag

## Project Website

https://main.d1z9zbyt1ozwli.amplifyapp.com/dashboard



## Introduction

This project is rebuilt from **FIT5225 Cloud Computing Assessment**. It aims to build a bird species identification web platform using a fully serverless solution.



This project aims to deliver a fully **event-driven serverless AWS architecture**, integrating **S3, Lambda, ECR, API Gateway, DynamoDB, and Cognito**.

- Containerized and deployed AI-based visual and audio processing models using **Lambda container images**.
- Achieved secure, automated media tagging and scalable cloud processing with minimal operational overhead.
- Used **WebSocket** to push real-time updates to the front end once AI inference is completed, instead of sending frequent polling requests.

## Features

![image-20260315110844266](C:\Users\Henry\AppData\Roaming\Typora\typora-user-images\image-20260315110844266.png)

### Upload files

![image-20260315111522634](C:\Users\Henry\AppData\Roaming\Typora\typora-user-images\image-20260315111522634.png)



### Supported Upload Types

Users are allowed to upload:

- **Images:** PNG, JPG
- **Videos:** short videos within **10 seconds** (MP4, MOV)
- **Audio:** MP3, WAV

Once a file is successfully uploaded, the AI model automatically starts the **inference process**, and the detected **bird species** will be displayed on the file cards.

Clicking on a file card will navigate to the **File Details page**.



### File Detail

#### Video & Audio

Clicking on the file card navigates to the **File Details page**.

Use the **Annotated / Original switch** to toggle between displaying the **original** or the **AI-annotated** video or image.

The **Species Detection Timeline** shows the appearance time of each detected species. Clicking on a bar will jump to the **start time** of that species.



**Video**:

![image-20260315112439480](C:\Users\Henry\AppData\Roaming\Typora\typora-user-images\image-20260315112439480.png)



**Audio**:

![image-20260315114325340](C:\Users\Henry\AppData\Roaming\Typora\typora-user-images\image-20260315114325340.png)

**Image**:

![image-20260315114614998](C:\Users\Henry\AppData\Roaming\Typora\typora-user-images\image-20260315114614998.png)



# Architecture



![birdtag_architecture](C:\Users\Henry\Desktop\private_project\bird-tag\birdtag_architecture.png)







# Limit:

#### Performance Limitation

Despite reducing the AI model’s **sampling FPS and resolution**, video processing still takes a relatively long time.

#### Trade-off of Serverless Architecture

Serverless architecture provides an **on-demand solution**, reducing costs while services are idle. However, AI models deployed in a serverless environment may experience **cold start latency** if the model has not been invoked frequently.



