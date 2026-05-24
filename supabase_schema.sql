-- MajuBox / Juke - Banco Supabase Postgres
-- Rode este SQL no Supabase: SQL Editor > New query > Run.
-- O servidor também cria as tabelas automaticamente quando DATABASE_URL está configurado.

CREATE TABLE IF NOT EXISTS machines (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    location    TEXT,
    token       TEXT UNIQUE NOT NULL,
    hwid        TEXT UNIQUE,
    active      INTEGER DEFAULT 1,
    license_ok  INTEGER DEFAULT 1,
    license_exp TEXT,
    admin_pass  TEXT DEFAULT '1234',
    pix_key     TEXT,
    pix_name    TEXT,
    pix_city    TEXT,
    mp_token    TEXT,
    last_seen   TIMESTAMP,
    last_ip     TEXT,
    last_user_agent TEXT,
    last_error  TEXT,
    app_version TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS genres (
    id          BIGSERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    cover_url   TEXT,
    sort_order  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dvds (
    id          BIGSERIAL PRIMARY KEY,
    genre_id    BIGINT REFERENCES genres(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    cover_url   TEXT,
    sort_order  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS playlists (
    id           BIGSERIAL PRIMARY KEY,
    genre_id     BIGINT REFERENCES genres(id) ON DELETE CASCADE,
    dvd_id       BIGINT REFERENCES dvds(id) ON DELETE SET NULL,
    title        TEXT NOT NULL,
    artist       TEXT,
    youtube_id   TEXT NOT NULL,
    video_url    TEXT,
    cover_url    TEXT,
    mode         TEXT DEFAULT 'jukebox',
    sort_order   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payments (
    id           TEXT PRIMARY KEY,
    machine_id   TEXT REFERENCES machines(id),
    amount       REAL DEFAULT 0,
    credits      INTEGER DEFAULT 0,
    status       TEXT DEFAULT 'pending',
    pix_qr       TEXT,
    pix_code     TEXT,
    mp_id        TEXT,
    payment_type TEXT DEFAULT 'license',
    credited     INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT NOW(),
    paid_at      TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plays (
    id           BIGSERIAL PRIMARY KEY,
    machine_id   TEXT,
    playlist_id  BIGINT,
    played_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS license_revenue (
    id           BIGSERIAL PRIMARY KEY,
    machine_id   TEXT REFERENCES machines(id),
    month        TEXT NOT NULL,
    total        REAL DEFAULT 0,
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS machine_revenue_log (
    id           BIGSERIAL PRIMARY KEY,
    machine_id   TEXT REFERENCES machines(id),
    amount       REAL DEFAULT 0,
    recorded_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS karaoke_scores (
    id           BIGSERIAL PRIMARY KEY,
    machine_id   TEXT,
    machine_hwid TEXT,
    machine_token TEXT,
    player_name  TEXT NOT NULL,
    score        INTEGER NOT NULL,
    song_title   TEXT,
    artist       TEXT,
    youtube_id   TEXT,
    genre_name   TEXT DEFAULT 'Karaokê',
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_machines_token ON machines(token);
CREATE INDEX IF NOT EXISTS idx_machines_hwid ON machines(hwid);
CREATE INDEX IF NOT EXISTS idx_playlists_genre_dvd ON playlists(genre_id, dvd_id);
CREATE INDEX IF NOT EXISTS idx_payments_machine_status ON payments(machine_id, status);
CREATE INDEX IF NOT EXISTS idx_karaoke_scores_score ON karaoke_scores(score DESC);

INSERT INTO genres(name, cover_url, sort_order)
SELECT * FROM (VALUES
('Sertanejo','/genre_covers/sertanejo.png',0),
('Pagode','/genre_covers/pagode.png',1),
('Forró','/genre_covers/forro.png',2),
('Axé','/genre_covers/axe.png',3),
('Funk','/genre_covers/funk.png',4),
('Rock','/genre_covers/rock.png',5),
('Karaokê','/genre_covers/karaoke.png',6),
('MPB','/genre_covers/mpb.png',7),
('Samba','/genre_covers/samba.png',8),
('Pop','/genre_covers/pop.png',9),
('Eletrônica','/genre_covers/eletronica.png',10),
('Gospel','/genre_covers/gospel.png',11)
) AS v(name, cover_url, sort_order)
WHERE NOT EXISTS (SELECT 1 FROM genres);
