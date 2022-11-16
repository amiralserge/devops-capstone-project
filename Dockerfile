FROM python:3.9-slim

# Create working directory and install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 

# Copy the application
COPY service ./service/

# Add and use a non-root user
RUN useradd --uid 1000 theia && chown -R theia /app
USER theia

# Expose and run the service
EXPOSE 8080
CMD ["gunicorn", "--bind=0.0.0.0:8080", "--log-level=info", "service:app"]
