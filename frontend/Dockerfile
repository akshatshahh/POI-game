FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci
RUN npm install -g serve

COPY . .
RUN npm run build

CMD sh -c "serve -s dist -l ${PORT:-3000}"
