FROM node:26.10-bookworm-slim 

WORKDIR /app

COPY ./frontend/package.json .

RUN npm install

COPY ./frontend .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
