FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 3000

# Запускаємо CRA dev-сервер — підтримує proxy до backend та hot-reload
CMD ["npm", "start"]
