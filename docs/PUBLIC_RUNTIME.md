# Publiczny Runtime

## Lokalny uklad portow

Na Raspberry Pi kazda aplikacja ma osobny lokalny port:

```text
PhotoMap    http://127.0.0.1:8000
IleStoi.pl  http://127.0.0.1:8001
```

Sprawdzenie:

```bash
systemctl status photomap.service wreckscanner.service cloudflared.service --no-pager
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8001/api/health
```

## Jeden tunel, wiele stron

Jeden `cloudflared` na tym samym Raspberry Pi moze obslugiwac kilka publicznych hostname'ow. Dla kazdej strony dodaj osobny wpis DNS/CNAME w Cloudflare i osobny wpis `ingress` w `/etc/cloudflared/config.yml`.

Przyklad konfiguracji:

```yaml
tunnel: 3b59bac9-6bb6-47bf-a532-6e44caa9855b
credentials-file: /home/test/.cloudflared/3b59bac9-6bb6-47bf-a532-6e44caa9855b.json

ingress:
  - hostname: photomap.pl
    service: http://127.0.0.1:8000
  - hostname: www.photomap.pl
    service: http://127.0.0.1:8000
  - hostname: wreckscanner.pl
    service: http://127.0.0.1:8001
  - hostname: ilestoi.pl
    service: http://127.0.0.1:8001
  - hostname: dlugostoi.pl
    service: http://127.0.0.1:8001
  - service: http_status:404
```

Po zmianie konfiguracji:

```bash
sudo systemctl restart cloudflared.service
systemctl status cloudflared.service --no-pager
```

Usuniecie strony oznacza usuniecie jej wpisow `ingress`, usuniecie jej rekordow DNS w Cloudflare i zatrzymanie/wylaczenie jej uslugi systemd.
