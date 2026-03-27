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

## Not

Bu klasor artik kendi `templates/` ve `static/` varliklarini tasiyor. Ayrı repoya cikarirken `meetingai_api` paket adi korunursa import yolu degismeden tasinabilir.
