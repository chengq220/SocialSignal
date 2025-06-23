FROM python3.9
WORKDIR /backend
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80","--reload"]
