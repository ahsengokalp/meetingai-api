# meetingai-api

MeetingAI'nin web dashboard ve mobile API katmani.

## Icerik

- Flask app factory
- Web dashboard route'lari
- Mobile auth ve meeting API route'lari
- Session tabanli web auth ve bearer token tabanli mobile auth

## Dahili bagimliliklar

- `meetingai-shared`
- `meetingai-note-worker`
- `meetingai-transcription-worker`

## Dis bagimliliklar

- `Flask`
- `ldap3`

## Entrypoint

- CLI: `meetingai-api`
- Module: `python -m meetingai_api --host 0.0.0.0 --port 5051`

## Calistirma

Bu servis kendi repo kokunden calistirilmalidir ve kendi `.env` dosyasini kullanir.

1. Sanal ortami hazirla:
   `python -m venv .venv`
2. Ortak paketi kur:
   `.\.venv\Scripts\python -m pip install -e ..\meetingai_shared`
3. API paketini kur:
   `.\.venv\Scripts\python -m pip install -e .`
4. `.env.example` dosyasini `.env` olarak kopyalayip degerleri doldur.
5. Servisi baslat:
   `.\.venv\Scripts\Activate.ps1`
   `python main.py --port 5051`

API, mobil uygulama ve web dashboard icin ana giris noktasi olarak calisir. Worker adresleri `.env` icindeki `TRANSCRIPTION_WORKER_BASE_URL` ve `NOTE_WORKER_BASE_URL` alanlarindan okunur.

## Not

Bu klasor artik kendi `templates/` ve `static/` varliklarini tasiyor. Ayrı repoya cikarirken `meetingai_api` paket adi korunursa import yolu degismeden tasinabilir.
