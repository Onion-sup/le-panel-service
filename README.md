# le-panel-service

Build
docker build -t led-panel-service .

Run
docker run -p 5000:5000 
        -e PORT=5000 \
        -e GITLAB_HOST=... \
        -e GITLAB_TOKEN=... \
        -e O365_TENANT_ID=... \
        -e O365_CLIENT_ID=... \
        -e O365_CLIENT_SECRET=... \
        led-panel-service