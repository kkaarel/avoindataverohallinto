# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.10-slim

WORKDIR /streamlit

# Copy the contents of the local ./streamlit folder into the /streamlit directory in the image
COPY ./streamlit .

RUN ls -aR


RUN pip install --upgrade pip \
    && pip install --force-reinstall -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]