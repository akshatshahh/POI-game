FROM node:20-alpine AS builder

ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

CMD ["nginx", "-g", "daemon off;"]
