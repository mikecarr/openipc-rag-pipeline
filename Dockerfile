FROM python:3.11-slim

# 1. Set the working directory
WORKDIR /usr/src/app

# 2. Add the working directory to the PYTHONPATH.
#    This is the key to making imports work consistently.
ENV PYTHONPATH="/usr/src/app"

# 3. Copy only the requirements first to leverage Docker caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy your application code into the working directory
#    This creates /usr/src/app/app, /usr/src/app/data, etc.
COPY . .

# 5. Set the command to run the app using the absolute module path
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]