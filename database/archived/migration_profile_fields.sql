ALTER TABLE users ADD COLUMN display_name VARCHAR(100) NULL AFTER username;
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) NULL AFTER display_name;