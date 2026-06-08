# -*- coding: utf-8 -*-
"""
Patch MajuBox: Importar JSON de canais como DVDs reais no banco de dados.

Use este patch APENAS no app.py original que ja funcionava.
Ele cria backup automatico e adiciona:
- botao no painel Musicas
- modal para colar JSON
- rota Flask /admin/api/youtube/import_channels_json
- salvamento real em genres/dvds/playlists usando get_db()
- suporte SQLite e Supabase/Postgres via camada existente do seu app.py
"""

from pathlib import Path
import shutil
import sys
import re

APP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("app.py")

if not APP.exists():
    print("ERRO: app.py nao encontrado.")
    print("Use assim: python patch_majubox_json_canais_db.py app.py")
    sys.exit(1)

text = APP.read_text(encoding="utf-8", errors="ignore")
backup = APP.with_suffix(".backup_json_canais_db.py")
shutil.copy2(APP, backup)
print(f"Backup criado: {backup}")

# ------------------------------------------------------------------
# 1) Botao na aba Musicas
# ------------------------------------------------------------------
if "modal-json-channels-db" not in text:
    old = '<button class="btn btn-ghost" onclick="openModal(\'modal-youtube-channel\')">📺 Importar canal YouTube</button>'
    new = old + "\n        " + '<button class="btn btn-ghost" onclick="openModal(\'modal-json-channels-db\')">📦 Importar JSON canais</button>'
    if old in text:
        text = text.replace(old, new, 1)
        print("OK: botao Importar JSON canais adicionado.")
    else:
        print("AVISO: nao achei o botao Importar canal YouTube para inserir o novo botao.")

# ------------------------------------------------------------------
# 2) Modal HTML
# ------------------------------------------------------------------
modal_html = '''
<div class="modal" id="modal-json-channels-db">
    <div class="modal-box" style="width:780px">
        <h2>📦 Importar JSON de canais como DVDs</h2>
        <p style="color:var(--muted);font-size:13px;margin-bottom:12px">
            Cole o JSON gerado pelo app buscador. Cada canal será salvo como um DVD real no banco, dentro do gênero escolhido.
        </p>
        <label>Gênero</label>
        <select id="json-db-genre"></select>
        <label>Modo das músicas</label>
        <select id="json-db-mode">
            <option value="jukebox">Jukebox</option>
            <option value="karaoke">Karaokê</option>
        </select>
        <label>Máximo de vídeos por canal</label>
        <input id="json-db-max-results" type="number" min="1" max="200" value="50">
        <label>JSON dos canais</label>
        <textarea id="json-db-text" rows="14" placeholder='Cole aqui o JSON exportado pelo app buscador de canais'></textarea>
        <div id="json-db-result" style="white-space:pre-wrap;color:var(--muted);font-size:13px;margin-top:10px"></div>
        <div class="row" style="margin-top:20px;justify-content:flex-end">
            <button class="btn btn-ghost" onclick="closeModal('modal-json-channels-db')">Cancelar</button>
            <button class="btn" onclick="importJSONChannelsDB()">Importar e salvar no banco</button>
        </div>
    </div>
</div>
'''

if 'id="modal-json-channels-db"' not in text:
    marker = '<div class="modal" id="modal-machine-reading">'
    if marker in text:
        text = text.replace(marker, modal_html + "\n" + marker, 1)
        print("OK: modal JSON DB adicionado.")
    else:
        # fallback antes do <script>
        marker2 = "<script>"
        if marker2 in text:
            text = text.replace(marker2, modal_html + "\n" + marker2, 1)
            print("OK: modal JSON DB adicionado antes do script.")
        else:
            print("AVISO: nao achei local para inserir modal.")

# ------------------------------------------------------------------
# 3) openModal carrega generos/DVDs tambem para o modal novo
# ------------------------------------------------------------------
if "modal-json-channels-db" in text and "id === 'modal-json-channels-db'" not in text:
    old = "if (id === 'modal-youtube-channel' || id === 'modal-bulk-playlist' || id === 'modal-playlist' || id === 'modal-dvd')"
    new = "if (id === 'modal-youtube-channel' || id === 'modal-json-channels-db' || id === 'modal-bulk-playlist' || id === 'modal-playlist' || id === 'modal-dvd')"
    if old in text:
        text = text.replace(old, new, 1)
        print("OK: openModal atualizado.")
    else:
        print("AVISO: nao achei condicao openModal exata.")

# ------------------------------------------------------------------
# 4) loadGenres preenche select json-db-genre
# ------------------------------------------------------------------
if "json-db-genre" in text and "jsonDbGenreSel" not in text:
    # tenta depois da linha yc-genre
    pattern = r"(document\.getElementById\('yc-genre'\)\.innerHTML\s*=\s*opts;)"
    repl = "\\1\n    const jsonDbGenreSel = document.getElementById('json-db-genre');\n    if (jsonDbGenreSel) jsonDbGenreSel.innerHTML = opts;"
    text2, n = re.subn(pattern, repl, text, count=1)
    if n:
        text = text2
        print("OK: json-db-genre recebe generos em loadGenres.")
    else:
        # fallback: inserir no fim de loadGenres antes de comentário DVDs
        marker = "// ─── DVDs"
        insert = "\nasync function fillJsonDbGenreSelect() {\n    const d = await api('/admin/api/genres');\n    const sel = document.getElementById('json-db-genre');\n    if (sel) sel.innerHTML = (d.genres || []).map(g => '<option value=\"' + g.id + '\">' + g.name + '</option>').join('');\n}\n"
        if marker in text:
            text = text.replace(marker, insert + "\n" + marker, 1)
            print("OK: fillJsonDbGenreSelect adicionado como fallback.")

# ------------------------------------------------------------------
# 5) JS para enviar JSON ao servidor
# ------------------------------------------------------------------
js_func = r'''
async function importJSONChannelsDB() {
    const box = document.getElementById('json-db-result');
    const genreId = document.getElementById('json-db-genre').value;
    const raw = document.getElementById('json-db-text').value.trim();
    const maxResults = document.getElementById('json-db-max-results').value || '50';
    const mode = document.getElementById('json-db-mode').value || 'jukebox';

    if (!genreId) {
        box.style.color = '#e74c3c';
        box.textContent = 'Escolha um gênero.';
        return;
    }
    if (!raw) {
        box.style.color = '#e74c3c';
        box.textContent = 'Cole o JSON dos canais.';
        return;
    }

    box.style.color = 'var(--yellow)';
    box.textContent = 'Importando e salvando no banco... Aguarde.';

    try {
        const r = await api('/admin/api/youtube/import_channels_json_db', 'POST', {
            genre_id: genreId,
            channels_json: raw,
            max_results: maxResults,
            mode: mode
        });

        if (r.ok) {
            box.style.color = '#2ecc71';
            let msg = 'Pronto!\n';
            msg += 'Canais no JSON: ' + (r.total || 0) + '\n';
            msg += 'DVDs salvos: ' + (r.dvds_saved || 0) + '\n';
            msg += 'Músicas salvas: ' + (r.playlists_saved || 0) + '\n';
            msg += 'Ignorados/repetidos: ' + (r.skipped || 0) + '\n';
            msg += 'Erros: ' + (r.failed || 0) + '\n\n';
            (r.results || []).slice(0, 80).forEach(function(x) {
                msg += '- ' + (x.dvd_name || x.name || x.channel || 'canal') + ': ' + (x.ok ? ('OK, ' + (x.inserted || 0) + ' músicas') : ('ERRO - ' + (x.error || 'falhou'))) + '\n';
            });
            box.textContent = msg;
            await loadDVDs();
            await loadPlaylists();
            await loadGenres();
            await loadStats();
        } else {
            box.style.color = '#e74c3c';
            box.textContent = r.error || 'Erro ao importar.';
        }
    } catch (e) {
        box.style.color = '#e74c3c';
        box.textContent = 'Erro no navegador: ' + e;
    }
}
'''

if "async function importJSONChannelsDB()" not in text:
    marker = "// ─── PAGAMENTOS"
    if marker in text:
        text = text.replace(marker, js_func + "\n" + marker, 1)
        print("OK: JS importJSONChannelsDB adicionado.")
    else:
        marker2 = "</script>"
        text = text.replace(marker2, js_func + "\n" + marker2, 1)
        print("OK: JS importJSONChannelsDB adicionado antes de </script>.")

# ------------------------------------------------------------------
# 6) Funções backend: salvar DVD e playlist no BANCO BASE do app.py
# ------------------------------------------------------------------
backend_code = r'''

def _json_channel_value(ch, *keys):
    for k in keys:
        v = ch.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def _normalize_channel_url_from_json(ch):
    channel_url = _json_channel_value(
        ch,
        "link_handle", "link_canal", "channel_url", "url", "link",
        "handle", "channel_id", "channelId", "id"
    )
    if not channel_url:
        return ""
    if channel_url.startswith("UC"):
        return "https://www.youtube.com/channel/" + channel_url
    if channel_url.startswith("@"):
        return "https://www.youtube.com/" + channel_url
    return channel_url


def _extract_channel_id_for_duplicate(channel_url):
    txt = str(channel_url or "").strip()
    if not txt:
        return ""
    m = re.search(r"/channel/(UC[0-9A-Za-z_-]{10,})", txt)
    if m:
        return m.group(1)
    if txt.startswith("UC"):
        return txt
    # handle ou URL normal
    return txt.rstrip("/").split("/")[-1].lower()


def _get_or_create_dvd_db(db, genre_id, dvd_name, cover_url="", channel_url=""):
    """Salva o canal como DVD REAL na tabela dvds do banco do app."""
    dvd_name = str(dvd_name or "Canal YouTube").strip()[:180]
    cover_url = str(cover_url or "").strip()
    key = _extract_channel_id_for_duplicate(channel_url) or dvd_name.lower()

    # Evita duplicar DVD pelo nome no mesmo genero.
    existing = db.execute(
        "SELECT * FROM dvds WHERE genre_id=? AND LOWER(name)=LOWER(?) LIMIT 1",
        (genre_id, dvd_name)
    ).fetchone()
    if existing:
        return existing["id"] if hasattr(existing, "keys") else existing[0], False

    max_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM dvds WHERE genre_id=?", (genre_id,)).fetchone()[0] or 0
    cur = db.execute(
        "INSERT INTO dvds(genre_id,name,cover_url,sort_order) VALUES(?,?,?,?)",
        (genre_id, dvd_name, cover_url, int(max_order) + 1)
    )
    dvd_id = getattr(cur, "lastrowid", None)
    if not dvd_id:
        row = db.execute("SELECT id FROM dvds WHERE genre_id=? AND LOWER(name)=LOWER(?) ORDER BY id DESC LIMIT 1", (genre_id, dvd_name)).fetchone()
        dvd_id = row["id"] if hasattr(row, "keys") else row[0]
    return dvd_id, True


def _save_playlist_video_db(db, genre_id, dvd_id, video, artist, mode):
    """Salva video REAL na tabela playlists, ligado ao genero e ao DVD."""
    youtube_id = str(video.get("youtube_id") or video.get("id") or video.get("videoId") or "").strip()
    title = str(video.get("title") or video.get("name") or "").strip()
    if not youtube_id or not title:
        return False, "sem youtube_id ou titulo"

    exists = db.execute(
        "SELECT id FROM playlists WHERE youtube_id=? AND dvd_id=? LIMIT 1",
        (youtube_id, dvd_id)
    ).fetchone()
    if exists:
        return False, "duplicado"

    max_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM playlists WHERE dvd_id=?", (dvd_id,)).fetchone()[0] or 0
    video_url = str(video.get("video_url") or video.get("url") or ("https://www.youtube.com/watch?v=" + youtube_id)).strip()
    cover_url = str(video.get("cover_url") or video.get("thumbnail") or video.get("thumb") or "").strip()
    db.execute(
        "INSERT INTO playlists(genre_id,dvd_id,title,artist,youtube_id,video_url,cover_url,mode,sort_order) VALUES(?,?,?,?,?,?,?,?,?)",
        (genre_id, dvd_id, title, artist or "", youtube_id, video_url, cover_url, mode or "jukebox", int(max_order) + 1)
    )
    return True, "ok"


def _fetch_youtube_videos_for_channel_db(channel_url, max_results=50, min_minutes=2, max_minutes=7):
    """Usa a funcao original do app se existir; senao tenta endpoint do YouTube.
    Retorna lista de dicts: title, youtube_id, cover_url, duration_seconds.
    """
    # Se seu app.py original ja tiver funcao pronta, usa ela.
    for fname in ["_fetch_youtube_channel_videos", "fetch_youtube_channel_videos", "_get_youtube_channel_videos"]:
        fn = globals().get(fname)
        if callable(fn):
            try:
                return fn(channel_url, max_results=max_results, min_minutes=min_minutes, max_minutes=max_minutes)
            except TypeError:
                try:
                    return fn(channel_url, max_results)
                except Exception:
                    pass
            except Exception:
                pass

    # Fallback minimo: se nao tiver funcao de buscar videos, nao inventa.
    return []


@app.route("/admin/api/youtube/import_channels_json_db", methods=["POST"])
def admin_import_channels_json_db():
    """Importa JSON do buscador e salva no banco base do MajuBox.

    Tabelas usadas:
    - genres: usa o genero escolhido
    - dvds: cada canal vira um DVD real
    - playlists: cada video importado entra ligado ao DVD
    """
    data = request.json or {}
    genre_id = data.get("genre_id")
    raw = (data.get("channels_json") or "").strip()
    mode = data.get("mode") or "jukebox"
    try:
        max_results = int(data.get("max_results") or 50)
    except Exception:
        max_results = 50
    max_results = max(1, min(200, max_results))

    if not genre_id:
        return jsonify({"ok": False, "error": "Escolha um genero."}), 400
    if not raw:
        return jsonify({"ok": False, "error": "Cole o JSON dos canais."}), 400

    try:
        parsed = json.loads(raw)
    except Exception as e:
        return jsonify({"ok": False, "error": "JSON invalido: " + str(e)}), 400

    if isinstance(parsed, dict):
        channels = parsed.get("channels") or parsed.get("canais") or parsed.get("results") or parsed.get("data") or []
    elif isinstance(parsed, list):
        channels = parsed
    else:
        channels = []

    if not channels:
        return jsonify({"ok": False, "error": "Nenhum canal encontrado no JSON."}), 400

    results = []
    dvds_saved = 0
    playlists_saved = 0
    skipped = 0
    failed = 0
    seen = set()

    with get_db() as db:
        g = db.execute("SELECT id, name FROM genres WHERE id=?", (genre_id,)).fetchone()
        if not g:
            return jsonify({"ok": False, "error": "Genero nao encontrado no banco."}), 404

        for ch in channels:
            if not isinstance(ch, dict):
                skipped += 1
                continue

            dvd_name = _json_channel_value(ch, "nome", "name", "title", "channelTitle", "handle", "channel_id", "channelId") or "Canal YouTube"
            channel_url = _normalize_channel_url_from_json(ch)
            cover_url = _json_channel_value(ch, "thumbnail", "cover_url", "avatar", "image", "foto")
            artist = dvd_name
            key = _extract_channel_id_for_duplicate(channel_url) or dvd_name.lower()
            if key in seen:
                skipped += 1
                continue
            seen.add(key)

            try:
                dvd_id, created = _get_or_create_dvd_db(db, genre_id, dvd_name, cover_url, channel_url)
                if created:
                    dvds_saved += 1

                videos = []
                # Se o JSON ja vier com videos, salva direto.
                if isinstance(ch.get("videos"), list):
                    videos = ch.get("videos")
                elif isinstance(ch.get("playlists"), list):
                    videos = ch.get("playlists")
                else:
                    videos = _fetch_youtube_videos_for_channel_db(channel_url, max_results=max_results, min_minutes=2, max_minutes=7)

                inserted = 0
                repeated = 0
                for video in videos or []:
                    if not isinstance(video, dict):
                        continue
                    try:
                        if _is_probable_short_video(video):
                            repeated += 1
                            continue
                    except Exception:
                        pass
                    ok, reason = _save_playlist_video_db(db, genre_id, dvd_id, video, artist, mode)
                    if ok:
                        inserted += 1
                        playlists_saved += 1
                    else:
                        repeated += 1

                results.append({"ok": True, "name": dvd_name, "dvd_name": dvd_name, "dvd_id": dvd_id, "created": created, "inserted": inserted, "skipped": repeated})
            except Exception as e:
                failed += 1
                results.append({"ok": False, "name": dvd_name, "channel": channel_url, "error": str(e)})

        db.commit()

    return jsonify({
        "ok": True,
        "total": len(channels),
        "processed": len(seen),
        "dvds_saved": dvds_saved,
        "playlists_saved": playlists_saved,
        "skipped": skipped,
        "failed": failed,
        "results": results
    })
'''

if '@app.route("/admin/api/youtube/import_channels_json_db"' not in text:
    marker = 'if __name__ == "__main__":'
    if marker in text:
        text = text.replace(marker, backend_code + "\n\n" + marker, 1)
        print("OK: backend DB import route adicionado antes do main.")
    else:
        text += "\n\n" + backend_code
        print("OK: backend DB import route adicionado no final.")

APP.write_text(text, encoding="utf-8")
print("\nPRONTO: patch aplicado no app.py.")
print("IMPORTANTE: ele salva no banco pelo get_db(), nas tabelas genres, dvds e playlists.")
print("Backup:", backup)
