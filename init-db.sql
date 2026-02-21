-- Create separate databases for each service
CREATE DATABASE litellm;
CREATE DATABASE openwebui;

-- Enable pgvector in both
\c litellm;
CREATE EXTENSION IF NOT EXISTS vector;

\c openwebui;
CREATE EXTENSION IF NOT EXISTS vector;