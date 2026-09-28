# Project Alpha - Chatbot

## Description

This project provides a front-end for interacting with the Alpha series chatbot. It is configured via environment variables and uses the Gemini API for its responses.

## Setup

1.  Create a `.env` file from the `.env.example` and add your `GEMINI_API_KEY`.
2.  Install dependencies: `pip install -r requirements.txt`

## Running the application

`flask --app app/main.py run`

## Testing

`python -m unittest discover tests`
