FROM node:20

WORKDIR /app

# Copy from chatbot-ui, not the root of frontend
COPY chatbot-ui/package*.json ./

RUN npm install

COPY chatbot-ui .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
