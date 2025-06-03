# Docker
## Install docker & docker compose
```
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

## Docker compose setup
### With SSL
- Create a .env file
```
HOST=your-domain.com
LETSENCRYPT_EMAIL=contact@your-domain.com
```

### Start
```
docker compose up -d
```
