-- MotorMind DB Schema
-- Jalankan di phpMyAdmin / MySQL CLI Laragon
-- mysql -u root motormind_db < schema.sql

CREATE DATABASE IF NOT EXISTS motormind_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE motormind_db;

-- ─────────────────────────────────────────────
-- USERS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  employee_id VARCHAR(30)  UNIQUE,
  name        VARCHAR(120) NOT NULL,
  email       VARCHAR(120) UNIQUE,
  password    VARCHAR(64)  NOT NULL COMMENT 'MD5 hash',
  role        ENUM('pegawai','owner') NOT NULL DEFAULT 'pegawai',
  avatar      VARCHAR(200) DEFAULT '',
  is_active   TINYINT(1)   DEFAULT 1,
  created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────
-- ANALYSES
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analyses (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  text          TEXT NOT NULL,
  sentiment     ENUM('positif','negatif','netral') NOT NULL,
  confidence    FLOAT DEFAULT 0,
  lexicon_score FLOAT DEFAULT 0,
  word_count    INT   DEFAULT 0,
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_created (created_at),
  INDEX idx_sentiment (sentiment)
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────
-- LEXICON
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lexicon (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  word     VARCHAR(100) UNIQUE NOT NULL,
  score    FLOAT NOT NULL DEFAULT 0 COMMENT 'positif > 0, negatif < 0',
  category ENUM('positif','negatif') NOT NULL
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────
-- SEED DATA
-- ─────────────────────────────────────────────
-- Password: admin123  → MD5 = 0192023a7bbd73250516f069df18b500
-- Password: owner123  → MD5 = gunakan: SELECT MD5('owner123')

INSERT IGNORE INTO users (employee_id, name, email, password, role) VALUES
('EMP001', 'Budi Santoso',  'budi@motormind.id',  MD5('admin123'), 'pegawai'),
('EMP002', 'Siti Rahayu',   'siti@motormind.id',  MD5('admin123'), 'pegawai'),
('OWN001', 'Direktur Utama','owner@motormind.id', MD5('owner123'), 'owner');

-- Sample lexicon
INSERT IGNORE INTO lexicon (word, score, category) VALUES
('kacau',  -1, 'negatif'),
('lelet',  -1, 'negatif'),
('parah',  -1, 'negatif'),
('kotor',  -1, 'negatif'),
('lama',   -1, 'negatif'),
('nyaman',  1, 'positif'),
}

-- Sample analyses
INSERT IGNORE INTO analyses (user_id, text, sentiment, confidence, lexicon_score, word_count, created_at) VALUES
(1,'Performa mesin sangat bagus dan responsif di semua kondisi jalan.','positif',0.94,3.6,10,'2025-10-24 14:22:01'),
(1,'Ditemukan getaran kecil pada katup pendingin sekunder saat idle.','negatif',0.78,-1.5,12,'2025-10-24 13:45:55'),
(1,'Efisiensi bahan bakar tetap dalam batas optimal selama pengujian.','positif',0.92,1.7,11,'2025-10-24 11:18:30'),
(2,'Profil akustik tidak biasa terdeteksi pada ignisi stage 2.','negatif',0.88,-1.8,10,'2025-10-23 22:15:04'),
(2,'Transisi transmisi mulus tercatat di semua rasio gigi yang disintesis.','positif',0.95,2.1,11,'2025-10-23 18:05:41');
