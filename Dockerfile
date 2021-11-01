# Specify our base image
FROM alpine:3.14
LABEL maintainer="Jaimyn Mayer (github@jaimyn.com.au)"
LABEL description="Base Dockerfile for the MemberMatters software."

VOLUME /usr/src/data/
VOLUME /usr/src/logs/

COPY nginx.conf /etc/nginx/nginx.conf
COPY . /usr/src/app/

WORKDIR /usr/src/app/
RUN apk update
RUN apk add make gcc g++ musl-dev libffi-dev openssl-dev zlib-dev jpeg-dev bash libpng-dev openrc cargo nginx vips-dev python2 python3 python3-dev py3-pip mariadb-dev nodejs npm
RUN mkdir -p /usr/src/app/frontend && mkdir /usr/src/logs && mkdir /usr/src/data

WORKDIR /usr/src/app/frontend/
RUN npm ci

WORKDIR /usr/src/app/memberportal/
RUN pip3 install --no-cache-dir pillow
RUN pip3 install --no-cache-dir -r requirements.txt
RUN python3 manage.py collectstatic --noinput

WORKDIR /usr/src/app/frontend/
RUN npm run build
RUN rm -rf .npmrc node_modules/
RUN apk del --no-cache --purge make gcc g++ musl-dev libffi-dev openssl-dev zlib-dev jpeg-dev bash libpng-dev cargo vips-dev python2 python3-dev npm
RUN rm -rf /var/cache/apk/*

EXPOSE 8000

CMD ["sh", "/usr/src/app/docker/container_start.sh"]
