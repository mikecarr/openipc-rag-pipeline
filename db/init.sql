CREATE TABLE IF NOT EXISTS messages (
    id BIGINT PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    sender_id BIGINT NOT NULL,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    text TEXT,
    media JSONB
);
