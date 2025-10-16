FROM node:16 as builder
WORKDIR /opt/app
COPY ["./package.json","./yarn.lock","./"]
RUN yarn install --frozen-lockfile --network-timeout 1000000
COPY ./ ./
RUN yarn run build
FROM nginx as worker
COPY --from=builder /opt/app/dist/spa  /usr/share/nginx/html
COPY --from=builder /opt/app/deployments/proxy.conf /etc/nginx/conf.d/default.conf
